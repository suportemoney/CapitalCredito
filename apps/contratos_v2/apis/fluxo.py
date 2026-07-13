# -*- coding: utf-8 -*-
"""APIs JSON do fluxo v2: solicitação de propostas, digitação, formalização, vídeo.

Acesso "vendedor" na esteira usa SCT16 (Consulta SIAPE) e, onde aplicável,
SCT201 (CRM Supervisão SIAPE). O código SCT191 não é mais verificado aqui; pode ser removido
dos perfis no cadastro de permissões se não for usado em outro lugar.
"""
import json
import logging
import re
from datetime import timedelta
from decimal import Decimal
from functools import wraps
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Prefetch, ProtectedError, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.contratos_v2.permissoes_codigos import COD_CX_NOVO_CONTRATO, COD_SS_ESTEIRA
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.utils import user_has_access

from apps.contratos_v2.fluxo_constants import (
    EstadoSolicitacaoDigitacao,
    EstadoSolicitacaoProposta,
    EtapaOperacional,
    FaseContratoExecucao,
    SubStatusOperacional,
    TagFinanceiraContrato,
    contrato_permite_envio_comprovante_pagamento_vendedor,
    validar_arquivo_comprovante_vendedor,
)
from apps.contratos_v2.fluxo_transicoes import (
    PAPEL_FINANCEIRO,
    PAPEL_OPERACIONAL,
    PAPEL_SUPERVISOR,
    PAPEL_VENDEDOR,
    _soma_comprovantes_tc_ativos,
    _valor_tc_contrato,
    contrato_exige_video_conscientizacao_para_pagamento,
    _lojas_m2m_dicts_por_usuario,
    lojas_elegiveis_m2m_destinatarios_register_money_ce,
    valor_tc_efetivo_para_fluxo,
    acoes_evoluir_contrato_permitidas,
    contrato_permite_evolucao_livre,
    transicoes_catalogo_livre_contrato,
    criar_registermoney_ranking_supervisor,
    aplicar_etapa_sub,
    par_etapa_sub_valido,
    persistir_tc_modal_em_contrato_e_rm,
    zerar_tc_modal_em_contrato,
    transicao_por_acao,
    transicoes_disponiveis_contrato_execucao,
    transicoes_disponiveis_simulacao,
)
from apps.contratos_v2.video_audit import (
    MENSAGEM_ERRO_VIDEO_TAMANHO,
    arquivar_video_atual_contrato,
    video_upload_excede_limite,
)
from apps.contratos_v2.cms_financeiro_base import base_af_para_cms, classificador_banco_efetivo
from apps.contratos_v2.models import (
    Banco,
    ClienteArquivo,
    ClienteBancario,
    ClienteContato,
    ClienteContatoDinamico,
    ClienteDadosPessoais,
    ClienteEndereco,
    ClienteEnderecoDinamico,
    ClienteRepresentante,
    Convenio,
    ContratoPortado,
    ContratoDadosOperacionais,
    ContratoExecucao,
    EnvioComprovantePagamentoVendedor,
    HistoricoEventoDigitacao,
    HistoricoEventoSimulacao,
    HistoricoTransicaoContrato,
    Produto,
    PropostaDados,
    SolicitacaoDigitacao,
    SolicitacaoPropostaCliente,
    TabelaCms,
    TagStatusOperacional,
)
from apps.vendas.siape.models import (
    CarteiraClientes,
    ClassificacaoValor,
    Cliente,
    RegisterMoney,
    TabulacaoVendedor,
)
from apps.vendas.financeiro_vendas.models import Classificador
from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
    resolver_classificacao_valor_de_rm_payload,
    resolver_classificacao_valor_por_classificador_id,
    resolver_classificador_financeiro_de_rm_payload,
)
from apps.vendas.siape.services.carteira_operacional import adicionar_proposta_operacional_na_carteira
from apps.contratos_v2.services.proposta_duplicata import (
    MSG_PROPOSTA_JA_DIGITADA,
    proposta_ja_existe_para_cliente,
)

logger = logging.getLogger(__name__)

# Migração 0050 (numero_contrato_banco_pre / link_formalizacao_pre): se o migrate ainda não rodou
# no ambiente, SELECT * quebraria. Usamos defer + leitura defensiva onde a ficha e permissões leem a solicitação.
_SOL_DIG_DEFER_PRE = ('numero_contrato_banco_pre', 'link_formalizacao_pre')

# Mesmo conjunto, prefixado para uso quando o ContratoExecucao traz a solicitação via select_related.
DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO = tuple(
    f'solicitacao_digitacao__{c}' for c in _SOL_DIG_DEFER_PRE
)


def _solicitacao_digitacao_queryset_schema_seguro():
    return SolicitacaoDigitacao.objects.defer(*_SOL_DIG_DEFER_PRE)


def _solicitacao_digitacao_campos_pre_contrato_seguros(sol):
    """Lê campos pré-contrato da solicitação; retorna ('', '') se as colunas não existirem no BD."""
    num_pre, link_pre = '', ''
    try:
        n = sol.numero_contrato_banco_pre
        num_pre = (n or '').strip() if isinstance(n, str) else (str(n).strip() if n is not None else '')
    except DatabaseError:
        num_pre = ''
    try:
        l = sol.link_formalizacao_pre
        link_pre = (l or '').strip() if isinstance(l, str) else (str(l).strip() if l is not None else '')
    except DatabaseError:
        link_pre = ''
    return num_pre, link_pre


# Permissões de tela equivalentes ao antigo SCT191 (vendedor na esteira de contratos).
COD_SIAPE_CONSULTA_CLIENTE = 'SCT16'  # SIAPE | Consulta cliente
COD_SIAPE_CRM_SUPERVISAO = 'SCT201'  # SIAPE | CRM Supervisão (formalização no lugar do vendedor)
# Sentinela interno: permissão não é um único código SCT (ver _usuario_autorizado_acao_vendedor).
_COD_VENDEDOR_ESTEIRA = '__VENDEDOR_ESTEIRA__'


def _acesso_crm_operacional_ou_supervisao_siape(user):
    """CRM operacional (SS35) ou supervisão SIAPE (SCT201) — mesma tela de ficha/timeline."""
    return user_has_access(user, COD_SS_ESTEIRA) or user_has_access(user, COD_SIAPE_CRM_SUPERVISAO)


def controle_acess_multiplos(*codigos):
    """Decorator: usuário precisa de pelo menos um dos códigos (ex.: CRM operacional ou financeiro)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_authenticated and any(
                user_has_access(request.user, c) for c in codigos
            ):
                return view_func(request, *args, **kwargs)
            return redirect('/sem-acesso/')

        return _wrapped

    return decorator


def _acesso_vendedor_loja_ou_consulta(usuario):
    """True se o usuário tem acesso à consulta SIAPE (vendedor) ou novo contrato (CX48)."""
    return user_has_access(usuario, COD_SIAPE_CONSULTA_CLIENTE) or user_has_access(usuario, COD_CX_NOVO_CONTRATO)


def _vendedor_cx48_carteira_contrato(usuario, ce):
    """CX48 com contrato vinculado à carteira do vendedor."""
    if not ce or not user_has_access(usuario, COD_CX_NOVO_CONTRATO):
        return False
    from apps.contratos_v2.apis.carteira_contrato_permissoes import contrato_vinculado_carteiras_responsavel
    return contrato_vinculado_carteiras_responsavel(usuario, ce)


def _usuario_autorizado_acao_vendedor(usuario, acao):
    """
    Autorização HTTP para ações com prefixo vendedor_* (substitui SCT191).
    - vendedor_video_enviado: apenas loja/consulta (transição no domínio só aceita papel vendedor).
    - Demais: loja/consulta ou CRM Supervisão SIAPE (paridade com vendedor_formalizado no fluxo_transicoes).
    """
    a = (acao or '').strip()
    base = _acesso_vendedor_loja_ou_consulta(usuario)
    if a == 'vendedor_video_enviado':
        return base
    return base or user_has_access(usuario, COD_SIAPE_CRM_SUPERVISAO)


def _usuario_pode_executar_acao_transicao(usuario, acao, ce=None):
    """Valida permissão para POST de transição conforme o mapeamento de código/papel por ação."""
    a = (acao or '').strip()
    codigo, papel = _codigo_acesso_para_acao(acao)
    if not codigo or not papel:
        return False
    if codigo == _COD_VENDEDOR_ESTEIRA:
        if _usuario_autorizado_acao_vendedor(usuario, acao):
            return True
        if _vendedor_cx48_carteira_contrato(usuario, ce):
            return True
        # CRM operacional (SS35): checado/formalizado na carteira própria sem SCT16 na permissão.
        if ce is not None and a in ('vendedor_checado_formalizacao', 'vendedor_formalizado_desde_link'):
            if user_has_access(usuario, COD_SS_ESTEIRA):
                from apps.contratos_v2.apis.carteira_contrato_permissoes import contrato_vinculado_carteiras_responsavel

                return contrato_vinculado_carteiras_responsavel(usuario, ce)
        return False
    # Paridade com api_post_evoluir (SS35): checado/formalizado na esteira CRM operacional.
    if codigo == 'SCT201' and papel == PAPEL_SUPERVISOR and a in (
        'supervisor_checado',
        'supervisor_formalizado',
    ):
        return user_has_access(usuario, codigo) or user_has_access(usuario, COD_SS_ESTEIRA)
    return user_has_access(usuario, codigo)


def _norm_cpf(cpf):
    if not cpf:
        return None
    d = ''.join(filter(str.isdigit, str(cpf)))
    if len(d) < 11:
        d = d.zfill(11)
    return d[:11] if len(d) >= 11 else d


def _tipo_telefone_siape_para_modal(tipo_siape):
    """Mapeia tipo do TelefoneCliente para o select do modal (CELULAR, TELEFONE_FIXO)."""
    if (tipo_siape or '').upper() == 'FIXO':
        return 'TELEFONE_FIXO'
    return 'CELULAR'


def _contatos_dinamicos_desde_siape(cpf_norm):
    """Monta lista {tipo, valor} a partir do celular cadastrado no Cliente SIAPE."""
    if len(cpf_norm) != 11:
        return []
    try:
        cli = Cliente.objects.get(cpf=cpf_norm)
    except Cliente.DoesNotExist:
        return []
    out = []
    cel = (cli.celular or '').strip()
    if cel:
        out.append({'tipo': 'CELULAR', 'valor': cel})
    return out


def _json_body(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return {}
    return {}


def _kwargs_snapshot_tabela_cms(tab):
    """Campos de snapshot copiados de TabelaCms ao criar ContratoDadosOperacionais."""
    if not tab:
        return {}
    tit = getattr(tab, 'titulo', None) or ''
    return {
        'tabela_cms_titulo_snapshot': tit[:200],
        'taxa_recebido_snapshot': tab.taxa_recebido,
        'taxa_repasse_snapshot': tab.taxa_repasse,
        'taxa_plastico_snapshot': tab.taxa_plastico,
    }


def _dec_flex(v):
    """Decimal a partir de string JSON (aceita pt-BR: 2.920,00)."""
    if v is None or v == '':
        return None
    if isinstance(v, Decimal):
        return v
    s = str(v).strip()
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(',', '.')
    try:
        return Decimal(s)
    except Exception:
        return None


def _extras_operacional_pago_cliente(data):
    """Monta extras de Pago Cliente (valor_saldo PORT e/ou payload REFIN)."""
    extras = {}
    vs = data.get('valor_saldo')
    if vs is not None and str(vs).strip() != '':
        extras['valor_saldo'] = vs
    rp = data.get('refin_port')
    if rp:
        extras['refin_port'] = rp
    return extras or None


def _evoluir_contrato_acao_permitida(ce, acao, data):
    """
    Valida se a ação do POST evoluir/ é aceita para o contrato.
    Port + Refin em Pago Cliente pode vir de qualquer etapa (salto livre ou operacional_pago_cliente).
    """
    if acao in acoes_evoluir_contrato_permitidas(ce):
        return True
    try:
        from apps.contratos_v2.services.port_refin import ce_exige_fluxo_port_refin_pago_cliente

        if not ce_exige_fluxo_port_refin_pago_cliente(ce):
            return False
        if acao == 'operacional_pago_cliente':
            return True
        sub = (data.get('sub') or data.get('sub_status') or '').strip()
        if acao == 'operacional_definir_status' and sub == SubStatusOperacional.PG_PAGO_CLIENTE:
            return True
    except Exception:
        return False
    return False


def _taxa_snapshot_ou_tabela(d, attr_snap, attr_tab):
    v = getattr(d, attr_snap, None)
    if v is not None:
        return v
    if d.tabela_cms_id:
        return getattr(d.tabela_cms, attr_tab, None)
    return None


def _montar_pago_tc_modal_defaults(ce):
    """Valores sugeridos para o modal Pago TC (supervisor + TC > 0)."""
    try:
        d = ce.dados_operacionais
    except Exception:
        return None
    if not d:
        return None
    qs_classificadores = Classificador.objects.filter(status=True).order_by('titulo')
    if not qs_classificadores.exists():
        # Evita dropdown vazio quando não há classificadores ativos no financeiro.
        qs_classificadores = Classificador.objects.all().order_by('titulo')
    classificacoes = [
        {
            'id': c.id,
            'titulo': c.titulo,
            'percentual': str(c.percentual),
            'percentual_num': str(c.percentual),
        }
        for c in qs_classificadores
    ]
    classif_100 = (
        Classificador.objects.filter(status=True, percentual=Decimal('100.00')).order_by('titulo').first()
        or Classificador.objects.filter(percentual=Decimal('100.00')).order_by('titulo').first()
    )
    from apps.contratos_v2.services.repasse_carteira import resolver_contexto_repasse_contrato

    ctx_rep = resolver_contexto_repasse_contrato(ce)
    tem_repasse = ctx_rep.get('tem_repasse', False)
    nome_responsavel = ctx_rep.get('nome_responsavel', '')
    nome_repasse = ctx_rep.get('nome_repasse', '')
    destinatarios = list(ctx_rep.get('destinatarios') or [])
    if not destinatarios:
        try:
            sol = ce.solicitacao_digitacao
            if sol and sol.criado_por_id:
                cr = sol.criado_por
                nome_v = (cr.get_full_name() or cr.username) if cr else '—'
                destinatarios = [{'user_id': cr.id if cr else None, 'nome': nome_v, 'papel': 'vendedor'}]
        except Exception:
            pass
    af = d.valor_af or Decimal('0')
    tr = _taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido')
    tp = _taxa_snapshot_ou_tabela(d, 'taxa_repasse_snapshot', 'taxa_repasse')
    tpl = _taxa_snapshot_ou_tabela(d, 'taxa_plastico_snapshot', 'taxa_plastico')

    def pct(taxa):
        if taxa is None or not af:
            return ''
        try:
            return str((af * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01')))
        except Exception:
            return ''

    titulo = (d.tabela_cms_titulo_snapshot or '').strip()
    if not titulo and d.tabela_cms_id:
        titulo = (d.tabela_cms.titulo or '')[:200]

    af_default = d.valor_af
    if af_default is None:
        try:
            af_default = ce.proposta_dados.valor_af if ce.proposta_dados_id else None
        except Exception:
            af_default = None

    v_tc_modal = valor_tc_efetivo_para_fluxo(ce)
    lojas_elegiveis = lojas_elegiveis_m2m_destinatarios_register_money_ce(ce)
    venda_associada_loja_default = False
    loja_id_default = None
    return {
        'contrato_id': ce.id,
        'valor_est_tc': str(v_tc_modal),
        'af': str(af_default) if af_default is not None else '',
        'tabela_cms_titulo': titulo,
        'taxa_recebido': str(tr) if tr is not None else '',
        'taxa_repasse': str(tp) if tp is not None else '',
        'taxa_plastico': str(tpl) if tpl is not None else '',
        'valor_cms_recebido': pct(tr),
        'valor_cms_repassado': pct(tp),
        'valor_cms_plastico': pct(tpl),
        'flag_cms_pago': False,
        'classificacoes': classificacoes,
        'classificadores': classificacoes,
        'classificacao_default_id': classif_100.id if classif_100 else None,
        'tem_repasse': tem_repasse,
        'eh_repasse': tem_repasse,
        'nome_responsavel': nome_responsavel,
        'nome_repasse': nome_repasse,
        'destinatarios': destinatarios,
        'lojas_elegiveis': [{'id': row['id'], 'nome': row['nome']} for row in lojas_elegiveis],
        'venda_associada_loja_default': venda_associada_loja_default,
        'loja_id_default': loja_id_default,
        'exige_escolha_loja': True,
        'flag_video_enviado': bool(ce.flag_video_enviado),
        'exige_video_conscientizacao': bool(contrato_exige_video_conscientizacao_para_pagamento(ce)),
        'ranking_formula_hint': 'Ranking SIAPE = fatia de TC (total ou metade se repasse). O % do classificador define a bonificação do consultor, não o ranking.',
    }


def _montar_pago_cms_modal_defaults(ce):
    """Snapshot de tabela e percentuais para o modal Pago CMS (financeiro, aguardando CMS)."""
    try:
        d = ce.dados_operacionais
    except Exception:
        return None
    if not d:
        return None
    titulo = (d.tabela_cms_titulo_snapshot or '').strip()
    if not titulo and d.tabela_cms_id:
        titulo = (d.tabela_cms.titulo or '')[:200]
    tr = _taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido')
    tp = _taxa_snapshot_ou_tabela(d, 'taxa_repasse_snapshot', 'taxa_repasse')
    tpl = _taxa_snapshot_ou_tabela(d, 'taxa_plastico_snapshot', 'taxa_plastico')
    return {
        'tabela_cms_titulo': titulo,
        'taxa_recebido': str(tr) if tr is not None else '',
        'taxa_repasse': str(tp) if tp is not None else '',
        'taxa_plastico': str(tpl) if tpl is not None else '',
    }


def _montar_registermoney_extra_supervisor_pago_tc(data, ce):
    """
    Monta o dict registermoney para transicao_por_acao quando TC > 0.
    Retorna (dict|None, erro|None): (None, None) se não aplicável; (None, msg) se inválido.
    """
    sem_tc = _valor_tc_contrato(ce) <= 0
    try:
        d = ce.dados_operacionais
    except Exception:
        return None, 'Dados operacionais não encontrados.'
    valor_est = _dec_flex(data.get('valor_est_tc') or data.get('valor_est'))
    # Intenção de zerar TC no modal (antes havia valor no contrato).
    zerando_tc = (valor_est is None or valor_est <= 0) and not sem_tc
    # Não zerar TC informado no modal só porque o snapshot do contrato ainda não foi gravado.
    if valor_est is None or valor_est <= 0:
        if sem_tc or zerando_tc:
            valor_est = Decimal('0')
        else:
            return None, 'Informe valor_est_tc (TC) maior que zero.'
    af = _dec_flex(data.get('af'))
    if af is None:
        af = d.valor_af

    af_base = d.valor_af or Decimal('0')
    tr = _taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido')
    tp = _taxa_snapshot_ou_tabela(d, 'taxa_repasse_snapshot', 'taxa_repasse')
    tpl = _taxa_snapshot_ou_tabela(d, 'taxa_plastico_snapshot', 'taxa_plastico')

    def cms_ou_calc(key, taxa):
        raw = data.get(key)
        if raw not in (None, ''):
            return _dec_flex(raw)
        if taxa is not None and af_base:
            try:
                return (af_base * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01'))
            except Exception:
                return None
        return None

    has_cls_input = (
        data.get('classificador_id') not in (None, '')
        or data.get('classificacao_valor_id') not in (None, '')
    )
    cv = resolver_classificacao_valor_de_rm_payload(data) if has_cls_input else None
    if not cv and not sem_tc:
        if has_cls_input:
            return None, 'Classificador inválido ou inativo.'
        cl_100 = (
            Classificador.objects.filter(status=True, percentual=Decimal('100.00')).order_by('titulo').first()
            or Classificador.objects.filter(percentual=Decimal('100.00')).order_by('titulo').first()
        )
        cv = resolver_classificacao_valor_por_classificador_id(cl_100.pk if cl_100 else None)
        if not cv:
            return None, 'Selecione o classificador de valor.'

    cl_fin = None
    if data.get('classificador_id') not in (None, ''):
        try:
            cl_fin = Classificador.objects.get(pk=int(data.get('classificador_id')), status=True)
        except (Classificador.DoesNotExist, ValueError, TypeError):
            try:
                cl_fin = Classificador.objects.get(pk=int(data.get('classificador_id')))
            except (Classificador.DoesNotExist, ValueError, TypeError):
                if not sem_tc:
                    return None, 'Classificador inválido ou inativo.'
    elif cv is not None:
        cl_fin = resolver_classificador_financeiro_de_rm_payload({'classificacao_valor_id': cv.id})

    extra = {
        'valor_est': valor_est,
        'af': af,
        'valor_cms_recebido': cms_ou_calc('valor_cms_recebido', tr),
        'valor_cms_repassado': cms_ou_calc('valor_cms_repassado', tp),
        'valor_cms_plastico': cms_ou_calc('valor_cms_plastico', tpl),
        'flag_cms_pago': bool(data.get('flag_cms_pago')),
        'classificacao_valor_id': cv.id if cv else None,
        'classificador_id': cl_fin.id if cl_fin else None,
    }
    # Pago TC (CRM): associação explícita de loja via M2M do funcionário destinatário
    if 'venda_associada_loja' in data:
        extra['venda_associada_loja'] = data.get('venda_associada_loja')
    if 'loja_id' in data:
        extra['loja_id'] = data.get('loja_id')
    if data.get('forcar_m3') in (True, 1, '1', 'true', 'True'):
        extra['forcar_m3'] = True
    return extra, None


def _aplicar_taxas_snapshot_financeiro_pago_cms(ce, user, data):
    """
    Persiste percentuais no snapshot antes de transicionar para Pago CMS.
    Retorna mensagem de erro (str) ou None se ok.
    """
    for key in ('taxa_recebido_snapshot', 'taxa_repasse_snapshot', 'taxa_plastico_snapshot'):
        if key not in data or data.get(key) in (None, ''):
            return 'Informe os três percentuais (recebido, repasse e plástico).'
    d = ContratoDadosOperacionais.objects.filter(contrato_execucao=ce).select_related('tabela_cms').first()
    if not d:
        return 'Sem dados operacionais no contrato.'
    for fld in ('taxa_recebido_snapshot', 'taxa_repasse_snapshot', 'taxa_plastico_snapshot'):
        val = data.get(fld)
        setattr(d, fld, _dec_flex(val))
    d.data_att_cms = timezone.now()
    d.user_att_cms = user
    d.save()
    ce_fresh = ContratoExecucao.objects.select_related(
        'dados_operacionais', 'dados_operacionais__tabela_cms'
    ).get(pk=ce.pk)
    _recalcular_cms_register_money_contrato(ce_fresh)
    return None


def _recalcular_cms_register_money_contrato(ce):
    """Atualiza valores CMS e classificador banco nos RegisterMoney quando snapshot/taxas/base mudam."""
    try:
        d = ce.dados_operacionais
    except Exception:
        return
    if not d:
        return
    af_base = base_af_para_cms(d)
    tr = _taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido')
    tp = _taxa_snapshot_ou_tabela(d, 'taxa_repasse_snapshot', 'taxa_repasse')
    tpl = _taxa_snapshot_ou_tabela(d, 'taxa_plastico_snapshot', 'taxa_plastico')

    def cms_from_af(taxa):
        if taxa is None or not af_base:
            return None
        try:
            return (af_base * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01'))
        except Exception:
            return None

    vr = cms_from_af(tr)
    vrep = cms_from_af(tp)
    vp = cms_from_af(tpl)
    cls_ef = classificador_banco_efetivo(d)
    for rm in RegisterMoney.objects.filter(contrato_execucao=ce):
        fields = []
        if rm.af is not None and rm.af > 0:
            rm.valor_cms_recebido = vr
            rm.valor_cms_repassado = vrep
            rm.valor_cms_plastico = vp
            fields.extend(
                ['valor_cms_recebido', 'valor_cms_repassado', 'valor_cms_plastico']
            )
        if cls_ef:
            rm.classificador_auto = cls_ef
            fields.append('classificador_auto')
        if fields:
            rm.save(update_fields=fields)


def _map_sub_status_simulacao(estado):
    """Mapeia o estado interno para os chips da aba Simulação."""
    if estado in (EstadoSolicitacaoProposta.ENVIADA, EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL, 'PENDENTE'):
        return 'aguardando'
    if estado == EstadoSolicitacaoProposta.RESULTADO_PROPOSTAS:
        return 'retornado'
    if estado == EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL:
        return 'inelegivel'
    return 'aguardando'


def _registrar_tabulacao(carteira, user, tipo, observacao='', sub_status_propostas=None):
    TabulacaoVendedor.objects.create(
        carteira_clientes=carteira,
        user=user,
        tipo=tipo,
        observacao=observacao or None,
    )
    carteira.status_comercial = tipo
    fields = ['status_comercial']
    if sub_status_propostas is not None:
        carteira.sub_status_propostas_comercial = sub_status_propostas
        fields.append('sub_status_propostas_comercial')
    carteira.save(update_fields=fields)
    _sincronizar_agregado_operacional(carteira)


def _sincronizar_agregado_operacional(carteira):
    try:
        from apps.vendas.siape.services.operacional_agregado import sincronizar_agregado_operacional
        sincronizar_agregado_operacional(carteira, salvar=True)
    except Exception:
        return


def _contrato_fila_dict(c):
    return {
        'contrato_id': c.id,
        'codigo': c.codigo,
        'fase': c.fase,
        'etapa_operacional': c.etapa_operacional,
        'sub_status_operacional': c.sub_status_operacional,
        'portabilidade': c.portabilidade,
        'cpf': c.cliente_dados_pessoais.cpf,
        'nome': c.cliente_dados_pessoais.nome_completo,
        'proposta_codigo': c.proposta_dados.codigo,
        'link_formalizacao': c.link_formalizacao or '',
    }


def _codigo_acesso_para_acao(acao):
    if acao in (
        'operacional_cancelar_cliente',
        'operacional_cancelar_corretor',
        'operacional_cancelar_banco',
        'operacional_cancelar_reembolso',
    ):
        return COD_SS_ESTEIRA, PAPEL_OPERACIONAL
    if acao in ('pendencia_entrar', 'pendencia_corrigido') or (acao or '').startswith('operacional_'):
        return COD_SS_ESTEIRA, PAPEL_OPERACIONAL
    if (acao or '').startswith('supervisor_'):
        return 'SCT201', PAPEL_SUPERVISOR
    if (acao or '').startswith('vendedor_'):
        return _COD_VENDEDOR_ESTEIRA, PAPEL_VENDEDOR
    if (acao or '').startswith('financeiro_'):
        return 'SCT147', PAPEL_FINANCEIRO
    return None, None


def _filtrar_transicoes_por_permissao(usuario, transicoes, ce=None):
    """Exibe no Evoluir apenas ações que o usuário pode executar no POST."""
    if not transicoes:
        return []
    out = []
    for t in transicoes:
        acao = t.get('acao')
        codigo, _ = _codigo_acesso_para_acao(acao)
        if not codigo:
            continue
        if codigo == _COD_VENDEDOR_ESTEIRA:
            if _usuario_autorizado_acao_vendedor(usuario, acao):
                out.append(t)
        elif codigo == 'SCT201':
            # Paridade com _usuario_pode_executar_acao_transicao: CRM operacional (SS35)
            # vê «Checado» e «Formalizado» na formalização sem possuir SCT201.
            a = (acao or '').strip()
            if user_has_access(usuario, codigo):
                out.append(t)
            elif (
                ce is not None
                and a in ('supervisor_formalizado', 'supervisor_checado')
                and user_has_access(usuario, COD_SS_ESTEIRA)
            ):
                out.append(t)
        elif user_has_access(usuario, codigo):
            out.append(t)
    return out


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_fila_operacional(request):
    """Filas para CRM operacional: solicitações digitação, contratos por etapa (nexos)."""
    fila = request.GET.get('fila', 'digitacao')
    out = []

    if fila == 'digitacao':
        qs = (
            _solicitacao_digitacao_queryset_schema_seguro()
            .filter(
                estado__in=[
                    EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
                    EstadoSolicitacaoDigitacao.EM_DIGITACAO,
                    EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO,
                ],
            )
            .select_related('proposta_dados', 'carteira_clientes', 'carteira_clientes__cliente')
            .order_by('-data_criacao')[:200]
        )
        for s in qs:
            out.append({
                'solicitacao_digitacao_id': s.id,
                'estado': s.estado,
                'cpf': s.proposta_dados.cliente_dados_pessoais.cpf,
                'nome': s.carteira_clientes.cliente.nome if s.carteira_clientes.cliente else '',
                'proposta_codigo': s.proposta_dados.codigo,
            })
        return JsonResponse({'ok': True, 'fila': fila, 'itens': out})

    mapa_etapa = {
        'em_analise': EtapaOperacional.ANALISE,
        'cip': EtapaOperacional.CIP,
        'refin': EtapaOperacional.REFIN,
        'anuencia': EtapaOperacional.ANUENCIA,
        'pagamento': EtapaOperacional.PAGAMENTO,
        'pendencias': EtapaOperacional.PENDENCIAS,
        'contratos_digitacao': EtapaOperacional.DIGITACAO,
    }
    if fila in mapa_etapa:
        et = mapa_etapa[fila]
        qs = ContratoExecucao.objects.filter(etapa_operacional=et, status=True).select_related(
            'proposta_dados', 'cliente_dados_pessoais'
        ).order_by('-data_ultima_atualizacao')[:200]
        for c in qs:
            out.append(_contrato_fila_dict(c))
        return JsonResponse({'ok': True, 'fila': fila, 'itens': out})

    return JsonResponse({'ok': False, 'erro': 'fila inválida.'}, status=400)


# Regex aceita letras, dígitos e os separadores comuns em números de contrato bancários.
_RX_CONTRATO_CODIGO = re.compile(r'^[A-Z0-9\-\.\/]{1,30}$')


def _validar_contrato_codigo(data):
    """
    Valida e normaliza o Nº Contrato informado pelo operacional ao gerar o
    contrato (campo ``codigo`` de ``ContratoExecucao``).

    Retorna ``(codigo_normalizado, erro)`` onde ``erro`` é ``None`` em caso
    de sucesso ou uma mensagem pronta para retorno JSON caso contrário.
    """
    cc = (data.get('contrato_codigo') or '').strip().upper()
    if not cc:
        return None, 'Nº Contrato obrigatório para gerar contrato.'
    if not _RX_CONTRATO_CODIGO.match(cc):
        return None, 'Nº Contrato inválido. Use apenas letras, números e -./ (até 30 caracteres).'
    if ContratoExecucao.objects.filter(codigo=cc).exists():
        return None, 'Nº Contrato já utilizado em outro contrato.'
    return cc, None


def _solicitacao_digitacao_permite_gerar_contrato(estado):
    """Pré-contrato: só gera contrato a partir de solicitação em fila operacional ativa."""
    return estado in (
        EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
        EstadoSolicitacaoDigitacao.EM_DIGITACAO,
    )


def _solicitacao_digitacao_requer_geracao_contrato(estado, em_pend_correcao=False):
    """CRM: solicitação sem ContratoExecucao que deveria ter contrato (modal obrigatório)."""
    if em_pend_correcao or estado == EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO:
        return False
    if estado == EstadoSolicitacaoDigitacao.CANCELADA:
        return False
    if estado == EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL:
        return False
    return True


def _persistir_numero_contrato_banco_pre(sol, cc):
    """Grava nº informado pelo operacional na solicitação (pré-geração)."""
    try:
        if getattr(sol, 'numero_contrato_banco_pre', None) != cc:
            sol.numero_contrato_banco_pre = cc
            sol.save(update_fields=['numero_contrato_banco_pre'])
    except DatabaseError:
        pass

def _transicoes_disponiveis_solicitacao_digitacao(sol):
    """Transições do modal Evoluir (pré-contrato): gerar, pendência vendedor, cancelar ou reabrir.

    Usa códigos de etapa ``PRE_SOL_*`` (não são etapas Nexos) para o CRM exibir cada ação
    como opção própria no select «Tabulação» sem depender do segundo nível Etapa+Status.
    """
    e = sol.estado
    if e in (EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL, EstadoSolicitacaoDigitacao.EM_DIGITACAO):
        return [
            {
                'acao': 'gerar_contrato',
                'etapa': 'PRE_SOL_GERAR',
                'etapa_label': 'Gerar contrato',
                'sub': 'DIG_AGUARDANDO',
                'sub_label': 'Com tabela CMS e nº contrato',
                'requer_extra': 'tabela_cms',
                'ordem': 0,
            },
            {
                'acao': 'operacional_solicitacao_marcar_pendencia',
                'etapa': 'PRE_SOL_PENDENCIA',
                'etapa_label': 'Pendenciar (correção vendedor)',
                'sub': EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO,
                'sub_label': 'Devolver proposta ao vendedor',
                'requer_extra': 'observacao',
                'ordem': 1,
            },
            {
                'acao': 'operacional_solicitacao_cancelar',
                'etapa': 'PRE_SOL_CANCELAR',
                'etapa_label': 'Cancelar proposta / solicitação',
                'sub': EstadoSolicitacaoDigitacao.CANCELADA,
                'sub_label': 'Encerra sem gerar contrato',
                'requer_extra': 'observacao',
                'ordem': 2,
            },
        ]
    if e == EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO:
        return [
            {
                'acao': 'operacional_solicitacao_reabrir',
                'etapa': 'PRE_SOL_REABRIR',
                'etapa_label': 'Reabrir para digitação',
                'sub': EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
                'sub_label': 'Voltar à fila operacional',
                'requer_extra': None,
                'ordem': 0,
            },
        ]
    return []


@login_required
@require_POST
@controle_acess(COD_SS_ESTEIRA)
def api_post_gerar_contrato_digitacao(request):
    """
    Operacional gera ContratoExecucao + ContratoDadosOperacionais a partir de uma solicitação de digitação.
    JSON: solicitacao_digitacao_id, tabela_cms_id (opcional se PropostaDados já tem tabela_cms), contrato_codigo

    Comportamento da Tabela CMS:
    - Se `tabela_cms_id` vier no payload, ele prevalece (permite ao operacional trocar a tabela).
    - Se não vier, usa-se o `proposta_dados.tabela_cms` escolhido pelo vendedor no wizard.
    - Se nenhum dos dois existir, retorna 400.
    """
    data = _json_body(request)
    sid = data.get('solicitacao_digitacao_id')
    tid = data.get('tabela_cms_id')
    if not sid:
        return JsonResponse({'ok': False, 'erro': 'solicitacao_digitacao_id é obrigatório.'}, status=400)
    cc, erro_cc = _validar_contrato_codigo(data)
    if erro_cc:
        return JsonResponse({'ok': False, 'erro': erro_cc}, status=400)
    try:
        sol = (
            _solicitacao_digitacao_queryset_schema_seguro()
            .select_related(
                'proposta_dados',
                'proposta_dados__tabela_cms',
                'carteira_clientes',
                'carteira_clientes__user_repasse',
                'carteira_clientes__user_responsavel',
            )
            .get(pk=int(sid))
        )
    except (ValueError, SolicitacaoDigitacao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
    if not _solicitacao_digitacao_permite_gerar_contrato(sol.estado):
        return JsonResponse(
            {
                'ok': False,
                'erro': (
                    'Esta solicitação não permite gerar contrato (cancelada, pendente de correção '
                    'ou já gerada). Recarregue a esteira.'
                ),
            },
            status=400,
        )

    # Fallback: se o operacional não forneceu tabela_cms_id, usa a escolhida pelo vendedor no PropostaDados.
    if not tid and sol.proposta_dados and sol.proposta_dados.tabela_cms_id:
        tid = sol.proposta_dados.tabela_cms_id
    if not tid:
        return JsonResponse({'ok': False, 'erro': 'tabela_cms_id é obrigatório (PropostaDados também não possui tabela CMS associada).'}, status=400)

    try:
        tab = TabelaCms.objects.select_related('banco', 'convenio', 'produto').get(pk=int(tid))
    except (ValueError, TabelaCms.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Tabela CMS não encontrada.'}, status=404)
    pd = sol.proposta_dados
    if sol.estado == EstadoSolicitacaoDigitacao.CONTRATO_GERADO:
        ce = ContratoExecucao.objects.filter(solicitacao_digitacao=sol).first()
        if ce:
            return JsonResponse({'ok': True, 'contrato_id': ce.id, 'codigo': ce.codigo, 'ja_existia': True})
    _persistir_numero_contrato_banco_pre(sol, cc)
    from apps.contratos_v2.services.repasse_carteira import kwargs_snapshot_repasse_contrato

    cart_snap = sol.carteira_clientes if sol.carteira_clientes_id else None
    snap_kw = kwargs_snapshot_repasse_contrato(cart_snap)
    with transaction.atomic():
        ce = ContratoExecucao.objects.create(
            codigo=cc,
            proposta_dados=pd,
            cliente_dados_pessoais=pd.cliente_dados_pessoais,
            solicitacao_digitacao=sol,
            fase=FaseContratoExecucao.DIGITACAO_AGUARDANDO,
            etapa_operacional=EtapaOperacional.DIGITACAO,
            sub_status_operacional=SubStatusOperacional.DIG_AGUARDANDO,
            **snap_kw,
        )
        ContratoDadosOperacionais.objects.create(
            contrato_execucao=ce,
            banco=tab.banco,
            convenio=tab.convenio,
            produto=tab.produto,
            tabela_cms=tab,
            valor_parcela=pd.valor_parcela,
            prazo=pd.prazo,
            valor_af=pd.valor_af,
            valor_tc=pd.valor_tc,
            valor_liberado=pd.valor_liberado,
            **_kwargs_snapshot_tabela_cms(tab),
        )
        sol.estado = EstadoSolicitacaoDigitacao.CONTRATO_GERADO
        sol.save(update_fields=['estado'])
    return JsonResponse({'ok': True, 'contrato_id': ce.id, 'codigo': ce.codigo})


@login_required
@require_POST
@controle_acess(COD_SS_ESTEIRA)
def api_post_definir_link_formalizacao(request, contrato_id):
    """Operacional informa link de formalização e notifica vendedor."""
    data = _json_body(request)
    link = (data.get('link_formalizacao') or '').strip()
    if not link:
        return JsonResponse({'ok': False, 'erro': 'link_formalizacao obrigatório.'}, status=400)
    try:
        ce = ContratoExecucao.objects.get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    ce.link_formalizacao = link
    ce.destaque_vendedor = True
    ce.save(update_fields=['link_formalizacao', 'destaque_vendedor', 'data_ultima_atualizacao'])
    ok, erro = aplicar_etapa_sub(
        ce,
        EtapaOperacional.DIGITACAO,
        SubStatusOperacional.DIG_LINK_DISPONIBILIZADO,
        request.user,
        observacao='Link de formalização',
    )
    if not ok:
        return JsonResponse({'ok': False, 'erro': erro}, status=400)
    return JsonResponse({'ok': True, 'codigo': ce.codigo})


def _build_arquivos_cliente_payload(request, dp_id, limit=200):
    """Lista ClienteArquivo (status=True) do cliente em formato pronto para a UI."""
    arquivos = []
    if not dp_id:
        return arquivos
    for a in (
        ClienteArquivo.objects.filter(cliente_dados_pessoais_id=dp_id, status=True)
        .order_by('-data_criacao')[:limit]
    ):
        try:
            aurl = request.build_absolute_uri(a.arquivo.url)
        except Exception:
            aurl = a.arquivo.url
        arquivos.append(
            {
                'id': a.id,
                'titulo': a.titulo,
                'tipo': a.tipo or '',
                'url': aurl,
                'data_criacao': a.data_criacao.strftime('%d/%m/%Y %H:%M') if a.data_criacao else '',
            }
        )
    return arquivos


def _build_pdf_proposta_payload(request, sol):
    """Retorna dict com PDF da proposta enviado pelo vendedor, ou None."""
    if not sol:
        return None
    arq = getattr(sol, 'arquivo_pdf_proposta', None)
    if not arq or not getattr(arq, 'name', ''):
        return None
    try:
        url = request.build_absolute_uri(arq.url)
    except Exception:
        url = arq.url
    return {
        'name': (arq.name or '').split('/')[-1] or 'proposta.pdf',
        'url': url,
        'enviado_por': (
            (sol.criado_por.get_full_name() or sol.criado_por.username)
            if getattr(sol, 'criado_por_id', None) else ''
        ),
        'data_criacao': sol.data_criacao.strftime('%d/%m/%Y %H:%M') if getattr(sol, 'data_criacao', None) else '',
    }


def serialize_envios_comprovante_pagamento_vendedor(request, contrato_execucao):
    """Lista envios do vendedor (mesmo shape de api_get_comprovantes_tc.envios_vendedor)."""
    itens = []
    for e in (
        EnvioComprovantePagamentoVendedor.objects.filter(contrato_execucao=contrato_execucao)
        .select_related('enviado_por')
        .order_by('-criado_em')
    ):
        arquivo_url = None
        if e.arquivo:
            try:
                arquivo_url = request.build_absolute_uri(e.arquivo.url)
            except Exception:
                arquivo_url = e.arquivo.url
        itens.append(
            {
                'id': e.id,
                'titulo': e.titulo,
                'arquivo_url': arquivo_url,
                'enviado_por': e.enviado_por.get_username() if e.enviado_por_id else '',
                'enviado_por_nome': (
                    (e.enviado_por.get_full_name() or e.enviado_por.username or '')
                    if e.enviado_por_id
                    else ''
                ),
                'criado_em': e.criado_em.isoformat() if e.criado_em else None,
            }
        )
    return itens


@login_required
@require_GET
def api_get_contrato_midia_arquivos(request, contrato_id):
    """Lista vídeo do contrato, PDF da proposta (vendedor) e arquivos do cliente (CRM)."""
    from apps.contratos_v2.apis.carteira_contrato_permissoes import pode_visualizar_contrato_ficha_ou_midia

    try:
        ce = (
            ContratoExecucao.objects.select_related(
                'cliente_dados_pessoais',
                'solicitacao_digitacao__criado_por',
                'solicitacao_digitacao',
                'proposta_dados__solicitacao_origem',
            )
            .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
            .get(pk=int(contrato_id), status=True)
        )
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    if not pode_visualizar_contrato_ficha_ou_midia(request.user, ce):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)

    video_payload = None
    if ce.video_cliente and ce.video_cliente.name:
        try:
            url = request.build_absolute_uri(ce.video_cliente.url)
        except Exception:
            url = ce.video_cliente.url
        video_payload = {
            'name': (ce.video_cliente.name or '').split('/')[-1] or 'video',
            'url': url,
            'size': ce.video_tamanho,
            'flag_video_enviado': bool(ce.flag_video_enviado),
        }

    sol_dig = ce.solicitacao_digitacao if ce.solicitacao_digitacao_id else None
    pdf_proposta = _build_pdf_proposta_payload(request, sol_dig)

    dp_id = ce.cliente_dados_pessoais_id
    arquivos = _build_arquivos_cliente_payload(request, dp_id)

    somente_leitura = ce.etapa_operacional == EtapaOperacional.CANCELADO
    envios_comprovante_vendedor = serialize_envios_comprovante_pagamento_vendedor(request, ce)
    return JsonResponse(
        {
            'ok': True,
            'tipo': 'contrato',
            'contrato_id': ce.id,
            'contrato_codigo': ce.codigo or '',
            'nome_cliente': ce.cliente_dados_pessoais.nome_completo if dp_id else '',
            'video': video_payload,
            'pdf_proposta': pdf_proposta,
            'arquivos': arquivos,
            'envios_comprovante_vendedor': envios_comprovante_vendedor,
            'somente_leitura': somente_leitura,
        }
    )


@login_required
@require_GET
def api_get_solicitacao_dig_midia_arquivos(request, solicitacao_id):
    """Lista PDF da proposta (vendedor) e arquivos do cliente p/ uma SolicitacaoDigitacao (CRM).

    Permissão alinhada à abertura do modal "Corrigir pendências": qualquer
    usuário logado pode listar (a barreira de acesso já é feita no endpoint da ficha).
    """
    try:
        sol = (
            _solicitacao_digitacao_queryset_schema_seguro()
            .select_related('proposta_dados__cliente_dados_pessoais', 'criado_por')
            .get(pk=int(solicitacao_id))
        )
    except (ValueError, SolicitacaoDigitacao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)

    dp = sol.proposta_dados.cliente_dados_pessoais if sol.proposta_dados_id else None
    dp_id = dp.id if dp else None
    pdf_proposta = _build_pdf_proposta_payload(request, sol)
    arquivos = _build_arquivos_cliente_payload(request, dp_id)

    return JsonResponse(
        {
            'ok': True,
            'tipo': 'solicitacao_dig',
            'solicitacao_id': sol.id,
            'nome_cliente': dp.nome_completo if dp else '',
            'video': None,
            'pdf_proposta': pdf_proposta,
            'arquivos': arquivos,
            # Upload de arquivo no pré-contrato passa a ser permitido para alinhar
            # com a regra "se conseguiu abrir a pendência, pode anexar".
            'somente_leitura': False,
        }
    )


@login_required
@require_POST
def api_post_solicitacao_dig_cliente_arquivo(request, solicitacao_id):
    """Anexa arquivo ao ClienteDadosPessoais da solicitação (pré-contrato).

    Espelha `api_post_contrato_cliente_arquivo`, porém recebe `solicitacao_id`
    em vez de `contrato_id` (para o modal de correção de pendências antes do
    `ContratoExecucao` ser gerado).
    """
    try:
        sol = (
            _solicitacao_digitacao_queryset_schema_seguro()
            .select_related('proposta_dados__cliente_dados_pessoais')
            .get(pk=int(solicitacao_id))
        )
    except (ValueError, SolicitacaoDigitacao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
    pd = sol.proposta_dados if sol.proposta_dados_id else None
    if not pd:
        return JsonResponse({'ok': False, 'erro': 'Proposta não vinculada à solicitação.'}, status=400)
    if not pd.cliente_dados_pessoais_id:
        return JsonResponse({'ok': False, 'erro': 'Cliente não vinculado à proposta.'}, status=400)
    f = request.FILES.get('arquivo') or request.FILES.get('file')
    if not f:
        return JsonResponse({'ok': False, 'erro': 'Arquivo obrigatório.'}, status=400)
    titulo = (request.POST.get('titulo') or '').strip() or (f.name[:200] if f.name else 'arquivo')
    tipo = f.name.split('.')[-1][:20] if f.name and '.' in f.name else ''
    ClienteArquivo.objects.create(
        cliente_dados_pessoais_id=pd.cliente_dados_pessoais_id,
        titulo=titulo,
        tipo=tipo,
        arquivo=f,
    )
    return JsonResponse({'ok': True, 'solicitacao_id': sol.id})


@login_required
@require_POST
def api_post_solicitacao_dig_correcao_concluida(request, solicitacao_id):
    """Devolve a solicitação à fila operacional após correção no modal (pré-contrato).

    Equivalente operacional: ``operacional_solicitacao_reabrir`` no evoluir.
    Permissão alinhada a ``api_get_ficha`` com ``tipo=solicitacao_dig`` (SS35 ou vendedor
    da carteira/repasse/presença INSS em ``PENDENTE_CORRECAO``).
    """
    try:
        sid = int(solicitacao_id)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'solicitacao_id inválido.'}, status=400)

    if ContratoExecucao.objects.filter(solicitacao_digitacao_id=sid, status=True).exists():
        return JsonResponse(
            {'ok': False, 'erro': 'Contrato já gerado: use o fluxo de pendências do contrato.'},
            status=409,
        )

    sol = (
        _solicitacao_digitacao_queryset_schema_seguro()
        .select_related('carteira_clientes')
        .filter(pk=sid)
        .first()
    )
    if not sol:
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)

    if sol.estado != EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO:
        return JsonResponse(
            {'ok': False, 'erro': 'Solicitação não está aguardando correção do vendedor.'},
            status=400,
        )

    cart = sol.carteira_clientes
    pode = user_has_access(request.user, COD_SS_ESTEIRA)
    if not pode:
        pode = bool(
            cart is not None
            and (
                cart.user_responsavel_id == request.user.id
                or cart.user_repasse_id == request.user.id
            )
        )
    if not pode:
        return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)

    data = _json_body(request)
    obs_txt = (data.get('observacao') or '').strip()
    obs = obs_txt or 'Correção concluída (modal consulta cliente / loja).'

    with transaction.atomic():
        ant = sol.estado
        sol.estado = EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL
        sol.save(update_fields=['estado'])
        HistoricoEventoDigitacao.objects.create(
            solicitacao=sol,
            estado_anterior=ant,
            estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
            usuario=request.user,
            observacao=obs[:500],
        )
        if cart:
            cart.tag_status_operacional = 'AGUARDANDO_DIGITACAO'
            cart.save(update_fields=['tag_status_operacional'])
            TagStatusOperacional.objects.create(
                carteira_clientes=cart,
                tag='AGUARDANDO_DIGITACAO',
                criado_por=request.user,
            )
            _sincronizar_agregado_operacional(cart)

    return JsonResponse({'ok': True, 'solicitacao_digitacao_id': sol.id, 'estado': sol.estado})


@login_required
@require_POST
def api_post_contrato_cliente_arquivo(request, contrato_id):
    """Anexa arquivo ao ClienteDadosPessoais do contrato (multipart)."""
    try:
        ce = (
            ContratoExecucao.objects.select_related(
                'solicitacao_digitacao', 'proposta_dados__solicitacao_origem',
            )
            .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
            .get(pk=int(contrato_id), status=True)
        )
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    # Permissão alinhada à abertura do modal: qualquer usuário logado que consiga
    # visualizar o contrato pode anexar arquivo. Regras de negócio (etapa CANCELADO,
    # vínculo do cliente) seguem aplicadas abaixo.
    if ce.etapa_operacional == EtapaOperacional.CANCELADO:
        return JsonResponse({'ok': False, 'erro': 'Contrato cancelado: não é permitido alterar arquivos.'}, status=400)
    if not ce.cliente_dados_pessoais_id:
        return JsonResponse({'ok': False, 'erro': 'Cliente não vinculado ao contrato.'}, status=400)
    f = request.FILES.get('arquivo') or request.FILES.get('file')
    if not f:
        return JsonResponse({'ok': False, 'erro': 'Arquivo obrigatório.'}, status=400)
    titulo = (request.POST.get('titulo') or '').strip() or (f.name[:200] if f.name else 'arquivo')
    tipo = f.name.split('.')[-1][:20] if f.name and '.' in f.name else ''
    ClienteArquivo.objects.create(
        cliente_dados_pessoais_id=ce.cliente_dados_pessoais_id,
        titulo=titulo,
        tipo=tipo,
        arquivo=f,
    )
    return JsonResponse({'ok': True, 'contrato_id': ce.id})


def _vendedor_pode_enviar_comprovante_pagamento_contrato(user, ce):
    """Loja INSS (presença na proposta) ou carteira SIAPE vinculada ao contrato + permissão de tela vendedor."""
    if user.is_superuser:
        return True
    if not _acesso_vendedor_loja_ou_consulta(user):
        return False
    from apps.contratos_v2.apis.carteira_contrato_permissoes import (
        contrato_vinculado_carteiras_responsavel,
        lojista_pode_acessar_contrato,
    )

    if lojista_pode_acessar_contrato(user, ce):
        return True
    if contrato_vinculado_carteiras_responsavel(user, ce):
        return True
    return False


@login_required
@require_POST
def api_post_contrato_comprovante_pagamento_vendedor(request, contrato_id):
    """Multipart (titulo, arquivo): comprovante enviado pelo vendedor sem valor; operacional conferência separada."""
    try:
        ce = ContratoExecucao.objects.get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    if ce.etapa_operacional == EtapaOperacional.CANCELADO:
        return JsonResponse({'ok': False, 'erro': 'Contrato cancelado.'}, status=400)
    if not contrato_permite_envio_comprovante_pagamento_vendedor(ce):
        return JsonResponse({'ok': False, 'erro': 'Etapa não permite envio de comprovante pelo vendedor.'}, status=400)
    if not _vendedor_pode_enviar_comprovante_pagamento_contrato(request.user, ce):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
    f = request.FILES.get('arquivo') or request.FILES.get('file')
    ok_arq, err_arq = validar_arquivo_comprovante_vendedor(f)
    if not ok_arq:
        return JsonResponse({'ok': False, 'erro': err_arq}, status=400)
    titulo = (request.POST.get('titulo') or '').strip() or (f.name[:200] if f.name else 'comprovante')
    EnvioComprovantePagamentoVendedor.objects.create(
        contrato_execucao=ce,
        titulo=titulo[:255],
        arquivo=f,
        enviado_por=request.user,
    )
    return JsonResponse({'ok': True, 'contrato_id': ce.id})


@login_required
@require_POST
def api_post_upload_video_contrato(request, contrato_id):
    """
    Envio de vídeo: quem tem Loja INSS ou Consulta SIAPE aplica transição (vendedor_video_enviado);
    CRM (SS35) apenas grava arquivo sem mudar etapa.
    """
    pode_vend = _acesso_vendedor_loja_ou_consulta(request.user)
    pode_crm = user_has_access(request.user, COD_SS_ESTEIRA)
    try:
        ce = ContratoExecucao.objects.get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    pode_cx48 = _vendedor_cx48_carteira_contrato(request.user, ce)
    if not pode_vend and not pode_crm and not pode_cx48:
        return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
    if ce.etapa_operacional == EtapaOperacional.CANCELADO:
        return JsonResponse({'ok': False, 'erro': 'Contrato cancelado: não é permitido alterar vídeo ou arquivos.'}, status=400)
    f = request.FILES.get('video') or request.FILES.get('arquivo')
    if not f:
        return JsonResponse({'ok': False, 'erro': 'Arquivo de vídeo obrigatório.'}, status=400)
    if video_upload_excede_limite(f):
        return JsonResponse({'ok': False, 'erro': MENSAGEM_ERRO_VIDEO_TAMANHO}, status=400)
    # Substituição: arquiva cópia do vídeo anterior para auditoria
    if ce.video_cliente and ce.video_cliente.name:
        try:
            arquivar_video_atual_contrato(ce)
        except Exception:
            return JsonResponse(
                {'ok': False, 'erro': 'Não foi possível arquivar o vídeo anterior. Tente novamente.'},
                status=500,
            )
    ce.video_cliente = f
    ce.video_tamanho = getattr(f, 'size', None)
    ce.destaque_vendedor = False
    ce.flag_video_enviado = True
    ce.save(
        update_fields=[
            'video_cliente',
            'video_tamanho',
            'destaque_vendedor',
            'flag_video_enviado',
            'data_ultima_atualizacao',
        ]
    )
    # Transição de vendedor (Formalizado→Análise / manter Análise): só para perfil vendedor sem papel CRM.
    # Quem tem SS35 usa o CRM (modal arquivos, Pago TC, etc.): upload só persiste vídeo e flag, sem mudar etapa.
    if (pode_vend or pode_cx48) and not pode_crm:
        ce.refresh_from_db()
        e = ce.etapa_operacional
        s = ce.sub_status_operacional
        transicao_video_aplica = (
            (e == EtapaOperacional.ANALISE and s == SubStatusOperacional.ANL_AGUARDANDO)
            or (e == EtapaOperacional.DIGITACAO and s == SubStatusOperacional.DIG_FORMALIZADO)
        )
        if transicao_video_aplica:
            ok, msg = transicao_por_acao(
                ce, request.user, PAPEL_VENDEDOR, 'vendedor_video_enviado', observacao='Upload vídeo'
            )
            if not ok:
                return JsonResponse({'ok': False, 'erro': msg}, status=400)
            ce.refresh_from_db()
            if ce.etapa_operacional == EtapaOperacional.ANALISE:
                ce.fase = FaseContratoExecucao.EM_ANALISE
                ce.save(update_fields=['fase', 'data_ultima_atualizacao'])
    return JsonResponse({'ok': True, 'contrato_id': ce.id})


@login_required
@require_GET
@controle_acess_multiplos(COD_SIAPE_CONSULTA_CLIENTE, COD_SIAPE_CRM_SUPERVISAO)
def api_get_propostas_container(request):
    """Dados agregados para o container Propostas na consulta do cliente (por CPF)."""
    cpf = _norm_cpf(request.GET.get('cpf'))
    if not cpf:
        return JsonResponse({'ok': False, 'erro': 'cpf obrigatório.'}, status=400)
    carteiras = CarteiraClientes.objects.filter(cliente__cpf=cpf, status='ATIVO').select_related('cliente')[:50]
    cards = []
    for cart in carteiras:
        tag = cart.tag_proposta_container or ''
        sc = cart.status_comercial or ''
        rotulo_fluxo = 'outros'
        if sc == 'SIMULACAO':
            rotulo_fluxo = 'simulacao'
        elif sc in ('OPERACIONAL', 'SOLICITACAO_PROPOSTAS', 'PROPOSTAS', 'DIGITACAO', 'INELEGIVEL'):
            rotulo_fluxo = 'proposta'
        cards.append({
            'carteira_id': cart.id,
            'status_comercial': cart.status_comercial,
            'tag_proposta_container': tag,
            'sub_status_propostas_comercial': cart.sub_status_propostas_comercial,
            'fluxo_rotulo': rotulo_fluxo,
            'cliente_nome': cart.cliente.nome if cart.cliente else '',
        })
    destaques = list(
        ContratoExecucao.objects.filter(
            cliente_dados_pessoais__cpf=cpf,
            destaque_vendedor=True,
            status=True,
        ).values('id', 'codigo', 'fase', 'link_formalizacao', 'etapa_operacional', 'sub_status_operacional')
    )
    contratos_cpf = list(
        ContratoExecucao.objects.filter(cliente_dados_pessoais__cpf=cpf, status=True)
        .select_related('proposta_dados__banco', 'proposta_dados__produto')
        .order_by('-data_ultima_atualizacao')[:30]
    )
    contratos_resumo = []
    for c in contratos_cpf:
        contratos_resumo.append({
            'id': c.id,
            'codigo': c.codigo,
            'fase': c.fase,
            'etapa_operacional': c.etapa_operacional,
            'sub_status_operacional': c.sub_status_operacional,
            'link_formalizacao': c.link_formalizacao,
            'proposta_codigo': c.proposta_dados.codigo,
            'banco': c.proposta_dados.banco.titulo if c.proposta_dados.banco_id else '',
            'produto': c.proposta_dados.produto.titulo if c.proposta_dados.produto_id else '',
        })
    return JsonResponse({
        'ok': True,
        'cpf': cpf,
        'cards': cards,
        'contratos_destaque': destaques,
        'contratos': contratos_resumo,
    })


@login_required
@require_POST
@controle_acess_multiplos(COD_SIAPE_CONSULTA_CLIENTE, COD_SIAPE_CRM_SUPERVISAO)
def api_post_solicitar_digitacao(request):
    """
    Vendedor marca propostas aceitas e envia PDF obrigatório (pode repetir por proposta).
    JSON: carteira_id, proposta_ids: [], observacoes, ou multipart com arquivo_pdf e campos.
    """
    carteira_id = request.POST.get('carteira_id') or _json_body(request).get('carteira_id')
    raw_ids = request.POST.get('proposta_ids') or _json_body(request).get('proposta_ids')
    observacoes = request.POST.get('observacoes') or _json_body(request).get('observacoes', '')
    if isinstance(raw_ids, str):
        try:
            proposta_ids = json.loads(raw_ids)
        except json.JSONDecodeError:
            proposta_ids = []
    else:
        proposta_ids = raw_ids or []
    pdf = request.FILES.get('arquivo_pdf') or request.FILES.get('pdf')
    if not carteira_id or not proposta_ids:
        return JsonResponse({'ok': False, 'erro': 'carteira_id e proposta_ids obrigatórios.'}, status=400)
    if not pdf:
        return JsonResponse({'ok': False, 'erro': 'PDF obrigatório.'}, status=400)
    try:
        carteira = CarteiraClientes.objects.get(pk=int(carteira_id), user_responsavel=request.user)
    except (ValueError, CarteiraClientes.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Carteira não encontrada ou sem permissão.'}, status=403)
    pdf_bytes = pdf.read()
    nome_pdf = getattr(pdf, 'name', 'proposta.pdf') or 'proposta.pdf'
    criados = []
    with transaction.atomic():
        for pid in proposta_ids:
            try:
                pd = PropostaDados.objects.get(pk=int(pid))
            except (ValueError, PropostaDados.DoesNotExist):
                continue
            cf = ContentFile(pdf_bytes, name=nome_pdf)
            sol = SolicitacaoDigitacao.objects.create(
                proposta_dados=pd,
                carteira_clientes=carteira,
                observacoes=observacoes or None,
                arquivo_pdf_proposta=cf,
                criado_por=request.user,
            )
            criados.append(sol.id)
            HistoricoEventoDigitacao.objects.create(
                solicitacao=sol,
                estado_anterior='',
                estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
                usuario=request.user,
            )
            pd.aceita_pelo_cliente = True
            pd.save(update_fields=['aceita_pelo_cliente'])
            adicionar_proposta_operacional_na_carteira(carteira, pd)
        _registrar_tabulacao(carteira, request.user, 'OPERACIONAL', sub_status_propostas='ACEITE')
        carteira.tag_proposta_container = 'AGUARDANDO'
        carteira.tag_status_operacional = 'AGUARDANDO_DIGITACAO'
        carteira.save(update_fields=['tag_proposta_container', 'tag_status_operacional'])
        _sincronizar_agregado_operacional(carteira)
    return JsonResponse({'ok': True, 'solicitacoes_digitacao_ids': criados})


@login_required
@require_POST
@controle_acess_multiplos(COD_SIAPE_CONSULTA_CLIENTE, COD_SIAPE_CRM_SUPERVISAO)
def api_post_solicitar_digitacao_sem_pdf(request):
    """
    Vendedor informa os dados operacionais (Banco/Convênio/Produto/valores) e solicita digitação sem PDF.
    Espera multipart com campo POST `payload` (JSON) e arquivos opcionais em `arquivos`.

    payload:
    - carteira_id
    - dados_pessoais/contato/endereco/bancario/representante (mesmo formato da solicitação inicial)
    - propostas: [{banco_id, convenio_id, produto_id, valor_af, valor_tc, valor_liberado, prazo, valor_parcela}]
    - contratos_portados: [{banco_id, valor_af, valor_parcela, valor_devedor_total, prazo_total, prazo_restante, numero_contrato}]
    """
    data = _json_body(request)
    if (not data) and request.POST.get('payload'):
        try:
            data = json.loads(request.POST.get('payload') or '{}')
        except Exception:
            data = {}

    cid = data.get('carteira_id')
    if not cid:
        return JsonResponse({'ok': False, 'erro': 'carteira_id obrigatório.'}, status=400)
    try:
        carteira = CarteiraClientes.objects.select_related('cliente').get(pk=int(cid), user_responsavel=request.user)
    except (ValueError, CarteiraClientes.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Carteira não encontrada.'}, status=403)

    dp = data.get('dados_pessoais') or {}
    cpf = _norm_cpf(dp.get('cpf') or (carteira.cliente and carteira.cliente.cpf))
    if not cpf:
        return JsonResponse({'ok': False, 'erro': 'CPF inválido.'}, status=400)

    propostas = data.get('propostas') or []
    if not propostas:
        return JsonResponse({'ok': False, 'erro': 'propostas obrigatórias.'}, status=400)

    with transaction.atomic():
        cliente_dp, _ = ClienteDadosPessoais.objects.update_or_create(
            cpf=cpf,
            defaults={
                'nome_completo': dp.get('nome_completo') or (carteira.cliente.nome if carteira.cliente else ''),
                'sexo': dp.get('sexo'),
                'data_nascimento': dp.get('data_nascimento'),
                'naturalidade': dp.get('naturalidade'),
                'pais_origem': dp.get('pais_origem'),
                'numero_rg': dp.get('numero_rg'),
                'orgao_emissor_rg': dp.get('orgao_emissor_rg'),
                'uf_emissao_rg': dp.get('uf_emissao_rg'),
                'data_emissao_rg': dp.get('data_emissao_rg'),
                'nome_pai': dp.get('nome_pai'),
                'nome_mae': dp.get('nome_mae'),
            },
        )
        c = data.get('contato') or {}
        ClienteContato.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={
                'email': c.get('email'),
                'email_secundario': c.get('email_secundario'),
                'telefone': c.get('telefone'),
                'telefone_residencial': c.get('telefone_residencial'),
            },
        )
        e = data.get('endereco') or {}
        ClienteEndereco.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={'cep': e.get('cep'), 'logradouro': e.get('logradouro')},
        )
        b = data.get('bancario') or {}
        ClienteBancario.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={
                'banco': b.get('banco'),
                'agencia': b.get('agencia'),
                'dv_agencia': b.get('dv_agencia'),
                'conta': b.get('conta'),
                'dv_conta': b.get('dv_conta'),
                'tipo_conta': b.get('tipo_conta'),
                'tipo_pagamento': b.get('tipo_pagamento'),
                'incluir_seguro': False,
                'matricula': b.get('matricula'),
                'senha': b.get('senha'),
            },
        )
        r = data.get('representante') or {}
        ClienteRepresentante.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={'nome_representante': r.get('nome_representante'), 'cpf_representante': r.get('cpf_representante')},
        )
        for f in request.FILES.getlist('arquivos'):
            ClienteArquivo.objects.create(
                cliente_dados_pessoais=cliente_dp,
                titulo=f.name[:200],
                tipo=f.name.split('.')[-1][:20] if '.' in f.name else '',
                arquivo=f,
            )

        criados = []
        portados_in = data.get('contratos_portados') or []
        for p in propostas:
            pd = PropostaDados.objects.create(
                cliente_dados_pessoais=cliente_dp,
                banco_id=int(p['banco_id']),
                convenio_id=int(p['convenio_id']),
                produto_id=int(p['produto_id']),
                valor_parcela=_dec(p.get('valor_parcela')),
                prazo=p.get('prazo') or None,
                valor_af=_dec(p.get('valor_af')),
                valor_tc=_dec(p.get('valor_tc')),
                valor_liberado=_dec(p.get('valor_liberado')),
                criado_por=request.user,
            )
            adicionar_proposta_operacional_na_carteira(carteira, pd)
            sol = SolicitacaoDigitacao.objects.create(
                proposta_dados=pd,
                carteira_clientes=carteira,
                observacoes=(data.get('observacao_solicitacao') or '').strip() or None,
                arquivo_pdf_proposta=None,
                criado_por=request.user,
            )
            criados.append(sol.id)
            HistoricoEventoDigitacao.objects.create(
                solicitacao=sol,
                estado_anterior='',
                estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
                usuario=request.user,
            )

            # Contratos portados (opcional): mesma lista replicada por proposta criada neste fluxo
            for cp in portados_in:
                kwargs = _kwargs_contrato_portado_de_dict(cp)
                if not kwargs:
                    continue
                kwargs['proposta_dados'] = pd
                ContratoPortado.objects.create(**kwargs)

        _registrar_tabulacao(carteira, request.user, 'DIGITACAO', sub_status_propostas='ACEITE')
        carteira.tag_proposta_container = 'AGUARDANDO'
        carteira.save(update_fields=['tag_proposta_container'])
        _sincronizar_agregado_operacional(carteira)

    return JsonResponse({'ok': True, 'solicitacoes_digitacao_ids': criados, 'message': 'Solicitação enviada ao operacional.'})


@login_required
@require_POST
@controle_acess(COD_SS_ESTEIRA)
def api_post_responder_solicitacao_proposta(request):
    """
    Operacional responde solicitação inicial: inelegível ou lista de propostas (cria PropostaDados).
    JSON: solicitacao_id, resultado: inelegivel | propostas, observacao (opcional, geral),
    propostas: [{ banco_id, convenio_id, produto_id, valores... }]
    """
    data = _json_body(request)
    sid = data.get('solicitacao_id')
    resultado = (data.get('resultado') or '').lower()
    obs_txt = (data.get('observacao') or '').strip() or None
    if not sid:
        return JsonResponse({'ok': False, 'erro': 'solicitacao_id obrigatório.'}, status=400)
    try:
        sol = SolicitacaoPropostaCliente.objects.select_related('carteira_clientes').get(pk=int(sid))
    except (ValueError, SolicitacaoPropostaCliente.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
    cart = sol.carteira_clientes
    existentes_antes = {
        x.id: x for x in PropostaDados.objects.filter(solicitacao_origem=sol)
    }
    ja_tinha_propostas = bool(existentes_antes)

    with transaction.atomic():
        sol.respondido_por = request.user
        sol.data_resposta = timezone.now()
        if resultado == 'inelegivel':
            sol.estado = EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL
            sol.observacao_resposta = obs_txt
            sol.save(update_fields=['estado', 'respondido_por', 'data_resposta', 'observacao_resposta'])
            cart.status_comercial = 'INELEGIVEL'
            cart.tag_proposta_container = 'INELEGIVEL'
            cart.save(update_fields=['status_comercial', 'tag_proposta_container'])
            _registrar_tabulacao(cart, request.user, 'INELEGIVEL')
        else:
            propostas = data.get('propostas') or []
            if not propostas:
                return JsonResponse({'ok': False, 'erro': 'Informe ao menos uma proposta.'}, status=400)
            sol.estado = EstadoSolicitacaoProposta.RESULTADO_PROPOSTAS
            sol.observacao_resposta = obs_txt
            sol.save(update_fields=['estado', 'respondido_por', 'data_resposta', 'observacao_resposta'])

            if ja_tinha_propostas:
                # Retorno subsequente: atualizar por id, criar linhas sem id, remover as não enviadas.
                by_id = {}
                novos = []
                for p in propostas:
                    pid = p.get('id')
                    if pid is not None and str(pid).strip() != '':
                        try:
                            pid = int(pid)
                        except (TypeError, ValueError):
                            return JsonResponse({'ok': False, 'erro': 'id de proposta inválido.'}, status=400)
                        if pid not in existentes_antes:
                            return JsonResponse(
                                {'ok': False, 'erro': 'Proposta não pertence a esta solicitação.'},
                                status=400,
                            )
                        by_id[pid] = p
                    else:
                        novos.append(p)
                manter_ids = set(by_id.keys())
                for eid, obj in list(existentes_antes.items()):
                    if eid not in manter_ids:
                        obj.delete()
                for pid, p in by_id.items():
                    obj = existentes_antes[pid]
                    obj.banco_id = int(p['banco_id'])
                    obj.convenio_id = int(p['convenio_id'])
                    obj.produto_id = int(p['produto_id'])
                    obj.valor_parcela = _dec(p.get('valor_parcela'))
                    obj.prazo = p.get('prazo')
                    obj.valor_af = _dec(p.get('valor_af'))
                    obj.valor_tc = _dec(p.get('valor_tc'))
                    obj.valor_liberado = _dec(p.get('valor_liberado'))
                    obj.save(update_fields=[
                        'banco_id', 'convenio_id', 'produto_id', 'valor_parcela',
                        'prazo', 'valor_af', 'valor_tc', 'valor_liberado',
                    ])
                for p in novos:
                    PropostaDados.objects.create(
                        cliente_dados_pessoais=sol.cliente_dados_pessoais,
                        solicitacao_origem=sol,
                        banco_id=int(p['banco_id']),
                        convenio_id=int(p['convenio_id']),
                        produto_id=int(p['produto_id']),
                        valor_parcela=_dec(p.get('valor_parcela')),
                        prazo=p.get('prazo'),
                        valor_af=_dec(p.get('valor_af')),
                        valor_tc=_dec(p.get('valor_tc')),
                        valor_liberado=_dec(p.get('valor_liberado')),
                        criado_por=request.user,
                    )
            else:
                for p in propostas:
                    PropostaDados.objects.create(
                        cliente_dados_pessoais=sol.cliente_dados_pessoais,
                        solicitacao_origem=sol,
                        banco_id=int(p['banco_id']),
                        convenio_id=int(p['convenio_id']),
                        produto_id=int(p['produto_id']),
                        valor_parcela=_dec(p.get('valor_parcela')),
                        prazo=p.get('prazo'),
                        valor_af=_dec(p.get('valor_af')),
                        valor_tc=_dec(p.get('valor_tc')),
                        valor_liberado=_dec(p.get('valor_liberado')),
                        criado_por=request.user,
                    )
            for pd in PropostaDados.objects.filter(solicitacao_origem=sol):
                adicionar_proposta_operacional_na_carteira(cart, pd)
            cart.tag_proposta_container = 'SUCESSO'
            cart.save(update_fields=['tag_proposta_container'])
            # Mantém a carteira em Simulação até o vendedor selecionar proposta(s) e enviar para digitação.
            _registrar_tabulacao(cart, request.user, 'SIMULACAO', sub_status_propostas='VERIFICANDO')
    return JsonResponse({'ok': True})


def _dec(v):
    """Decimal a partir de valor de formulário/JSON (aceita vírgula como separador decimal)."""
    if v is None or v == '':
        return None
    try:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        s = str(v).strip()
        if not s:
            return None
        # Wizard BR: "377,50" sem separador de milhar
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
        return Decimal(s)
    except Exception:
        return None


def _int_pk_frontend(val):
    """Converte PK vinda do front (JSON/FormData): int, '12', '12.0'; rejeita bool/vazio."""
    if val is None or val is False or val == '':
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val if val > 0 else None
    s = str(val).strip()
    if not s or s.lower() in ('null', 'undefined', 'none'):
        return None
    try:
        n = Decimal(s.replace(',', '.'))
        i = int(n)
        return i if i > 0 else None
    except Exception:
        return None


def _int_portado_contrato(v):
    """Converte valor JSON em int para prazos do contrato portado; None se vazio ou inválido."""
    if v is None or v == '':
        return None
    s = str(v).strip().replace(',', '.')
    if not s:
        return None
    try:
        return int(Decimal(s))
    except Exception:
        return None


def _kwargs_contrato_portado_de_dict(cp):
    """
    Monta kwargs para ContratoPortado a partir do JSON do cliente.
    Retorna None se a linha estiver totalmente vazia (não cria registro).
    Aceita chaves legadas prazo_contratado / prazo_em_aberto.
    """
    if not isinstance(cp, dict):
        return None
    banco_id = _int_pk_frontend(cp.get('banco_id'))
    valor_af = _dec(cp.get('valor_af'))
    valor_parcela = _dec(cp.get('valor_parcela'))
    valor_devedor_total = _dec(cp.get('valor_devedor_total'))
    prazo_total = _int_portado_contrato(cp.get('prazo_total'))
    if prazo_total is None:
        prazo_total = _int_portado_contrato(cp.get('prazo_contratado'))
    prazo_restante = _int_portado_contrato(cp.get('prazo_restante'))
    if prazo_restante is None:
        prazo_restante = _int_portado_contrato(cp.get('prazo_em_aberto'))
    numero = (cp.get('numero_contrato') or '').strip() or None
    tem_banco = banco_id is not None
    tem_vf = valor_af is not None
    tem_vp = valor_parcela is not None
    tem_pt = prazo_total is not None
    tem_pr = prazo_restante is not None
    tem_num = bool(numero)
    tem_dev = valor_devedor_total is not None
    if not (tem_banco or tem_vf or tem_vp or tem_pt or tem_pr or tem_num or tem_dev):
        return None
    return {
        'banco_id': banco_id,
        'valor_af': valor_af,
        'valor_parcela': valor_parcela,
        'valor_devedor_total': valor_devedor_total,
        'prazo_total': prazo_total,
        'prazo_restante': prazo_restante,
        'numero_contrato': numero,
    }


def _proposta_operacional_dict(p):
    return {
        'id': p.id,
        'banco_id': p.banco_id,
        'convenio_id': p.convenio_id,
        'produto_id': p.produto_id,
        'valor_parcela': str(p.valor_parcela) if p.valor_parcela is not None else '',
        'prazo': p.prazo or '',
        'valor_af': str(p.valor_af) if p.valor_af is not None else '',
        'valor_tc': str(p.valor_tc) if p.valor_tc is not None else '',
        'valor_liberado': str(p.valor_liberado) if p.valor_liberado is not None else '',
    }


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_propostas_solicitacao_operacional(request, solicitacao_id):
    try:
        sol = SolicitacaoPropostaCliente.objects.get(pk=int(solicitacao_id))
    except (ValueError, SolicitacaoPropostaCliente.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
    props = list(
        PropostaDados.objects.filter(solicitacao_origem=sol)
        .select_related('banco', 'convenio', 'produto')
        .order_by('id')
    )
    return JsonResponse({
        'ok': True,
        'propostas': [_proposta_operacional_dict(p) for p in props],
        'observacao_resposta': (sol.observacao_resposta or '').strip(),
    })


@login_required
@require_POST
@controle_acess_multiplos(COD_SIAPE_CONSULTA_CLIENTE, COD_SIAPE_CRM_SUPERVISAO)
def api_post_solicitacao_proposta_inicial(request):
    """
    Vendedor envia solicitação com dados do cliente (JSON aninhado).
    JSON: carteira_id, dados_pessoais {}, contato {}, endereco {}, bancario {}, representante {}, arquivos via multipart separado opcional.
    """
    data = _json_body(request)
    if (not data) and request.POST.get('payload'):
        try:
            data = json.loads(request.POST.get('payload') or '{}')
        except Exception:
            data = {}
    cid = data.get('carteira_id')
    if not cid:
        return JsonResponse({'ok': False, 'erro': 'carteira_id obrigatório.'}, status=400)
    try:
        carteira = CarteiraClientes.objects.select_related('cliente').get(pk=int(cid), user_responsavel=request.user)
    except (ValueError, CarteiraClientes.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Carteira não encontrada.'}, status=403)
    dp = data.get('dados_pessoais') or {}
    cpf = _norm_cpf(dp.get('cpf') or (carteira.cliente and carteira.cliente.cpf))
    if not cpf:
        return JsonResponse({'ok': False, 'erro': 'CPF inválido.'}, status=400)
    tipo_tabulacao = (data.get('tipo_tabulacao') or '').strip().upper()
    if tipo_tabulacao not in ('SIMULACAO', 'SOLICITACAO_PROPOSTAS'):
        tipo_tabulacao = 'SOLICITACAO_PROPOSTAS'
    with transaction.atomic():
        cliente_dp, _ = ClienteDadosPessoais.objects.update_or_create(
            cpf=cpf,
            defaults={
                'nome_completo': dp.get('nome_completo') or (carteira.cliente.nome if carteira.cliente else ''),
                'sexo': dp.get('sexo'),
                'data_nascimento': dp.get('data_nascimento'),
                'naturalidade': dp.get('naturalidade'),
                'pais_origem': dp.get('pais_origem'),
                'numero_rg': dp.get('numero_rg'),
                'orgao_emissor_rg': dp.get('orgao_emissor_rg'),
                'uf_emissao_rg': dp.get('uf_emissao_rg'),
                'data_emissao_rg': dp.get('data_emissao_rg'),
                'nome_pai': dp.get('nome_pai'),
                'nome_mae': dp.get('nome_mae'),
            },
        )
        c = data.get('contato') or {}
        ClienteContato.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={
                'email': c.get('email'),
                'email_secundario': c.get('email_secundario'),
                'telefone': c.get('telefone'),
                'telefone_residencial': c.get('telefone_residencial'),
            },
        )
        e = data.get('endereco') or {}
        ClienteEndereco.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={'cep': e.get('cep'), 'logradouro': e.get('logradouro')},
        )
        b = data.get('bancario') or {}
        ClienteBancario.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={
                'banco': b.get('banco'),
                'agencia': b.get('agencia'),
                'dv_agencia': b.get('dv_agencia'),
                'conta': b.get('conta'),
                'dv_conta': b.get('dv_conta'),
                'tipo_conta': b.get('tipo_conta'),
                'tipo_pagamento': b.get('tipo_pagamento'),
                'incluir_seguro': False,
                'matricula': b.get('matricula'),
                'senha': b.get('senha'),
            },
        )
        r = data.get('representante') or {}
        ClienteRepresentante.objects.update_or_create(
            cliente_dados_pessoais=cliente_dp,
            defaults={'nome_representante': r.get('nome_representante'), 'cpf_representante': r.get('cpf_representante')},
        )
        sol = SolicitacaoPropostaCliente.objects.create(
            carteira_clientes=carteira,
            cliente_dados_pessoais=cliente_dp,
            estado=EstadoSolicitacaoProposta.ENVIADA,
            criado_por=request.user,
        )
        for f in request.FILES.getlist('arquivos'):
            ClienteArquivo.objects.create(
                cliente_dados_pessoais=cliente_dp,
                titulo=f.name[:200],
                tipo=f.name.split('.')[-1][:20] if '.' in f.name else '',
                arquivo=f,
            )
        sol.estado = EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL
        sol.save(update_fields=['estado'])
        HistoricoEventoSimulacao.objects.create(
            solicitacao=sol,
            estado_anterior=EstadoSolicitacaoProposta.ENVIADA,
            estado_novo=EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL,
            usuario=request.user,
        )
        carteira.tag_proposta_container = 'AGUARDANDO'
        carteira.save(update_fields=['tag_proposta_container'])
        _registrar_tabulacao(carteira, request.user, tipo_tabulacao, sub_status_propostas='VERIFICANDO')
    return JsonResponse({'ok': True, 'solicitacao_id': sol.id, 'cliente_dados_pessoais_id': cliente_dp.id})


@login_required
@require_GET
def api_get_propostas_dados_por_carteira(request):
    """Lista PropostaDados para montar modal (por carteira)."""
    cid = request.GET.get('carteira_id')
    if not cid:
        return JsonResponse({'ok': False, 'erro': 'carteira_id obrigatório.'}, status=400)
    try:
        carteira = CarteiraClientes.objects.select_related('cliente', 'cliente_operacional').get(
            pk=int(cid),
            user_responsavel=request.user,
        )
    except (ValueError, CarteiraClientes.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Carteira não encontrada.'}, status=403)

    try:
        filtros = Q(solicitacao_origem__carteira_clientes=carteira)
        if carteira.cliente_operacional_id:
            filtros |= Q(cliente_dados_pessoais_id=carteira.cliente_operacional_id)
        cpf = _norm_cpf(carteira.cliente.cpf) if carteira.cliente else None
        if cpf:
            filtros |= Q(cliente_dados_pessoais__cpf=cpf)

        pds = (
            PropostaDados.objects
            .filter(filtros)
            .select_related('banco', 'convenio', 'produto')
            .distinct()
            .order_by('-data_criacao', '-id')
        )
        out = []
        for p in pds:
            contratos = list(
                ContratoExecucao.objects.filter(proposta_dados=p, status=True).values(
                    'id', 'codigo', 'etapa_operacional', 'sub_status_operacional', 'fase'
                )
            )
            out.append({
                'id': p.id,
                'codigo': p.codigo,
                'banco': p.banco.titulo if p.banco_id else '—',
                'convenio': p.convenio.titulo if p.convenio_id else '—',
                'produto': p.produto.titulo if p.produto_id else '—',
                'valor_parcela': str(p.valor_parcela) if p.valor_parcela is not None else None,
                'aceita_pelo_cliente': p.aceita_pelo_cliente,
                'contratos': contratos,
            })
        obs_ret = ''
        sol_obs = (
            SolicitacaoPropostaCliente.objects.filter(
                carteira_clientes=carteira,
                data_resposta__isnull=False,
            )
            .order_by('-data_resposta')
            .only('observacao_resposta')
            .first()
        )
        if sol_obs and sol_obs.observacao_resposta:
            obs_ret = (sol_obs.observacao_resposta or '').strip()

        return JsonResponse({
            'ok': True,
            'propostas': out,
            'total_propostas': len(out),
            'total_disponiveis': len([x for x in out if not x.get('aceita_pelo_cliente')]),
            'observacao_resposta': obs_ret,
        })
    except Exception as exc:
        logger.exception('api_get_propostas_dados_por_carteira: %s', exc)
        return JsonResponse({'ok': False, 'erro': 'Erro interno ao carregar propostas.'}, status=500)


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_solicitacoes_pendentes_operacional(request):
    qs = SolicitacaoPropostaCliente.objects.filter(
        estado__in=[
            EstadoSolicitacaoProposta.ENVIADA,
            EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL,
            EstadoSolicitacaoProposta.RESULTADO_PROPOSTAS,
            EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL,
            'PENDENTE',
        ],
    ).select_related('carteira_clientes__cliente', 'cliente_dados_pessoais', 'criado_por').order_by('-data_criacao')[:100]
    itens = []
    for s in qs:
        sub_status_simulacao = _map_sub_status_simulacao(s.estado)
        itens.append({
            'id': s.id,
            'cpf': s.cliente_dados_pessoais.cpf,
            'nome': s.cliente_dados_pessoais.nome_completo,
            'carteira_id': s.carteira_clientes_id,
            'estado': s.estado,
            'sub_status_simulacao': sub_status_simulacao,
            'vendedor': s.criado_por.get_username() if s.criado_por else '',
        })
    return JsonResponse({'ok': True, 'solicitacoes': itens})


def _crm_supervisao_filtro_user_ids_fluxo(request):
    if request.user.is_superuser:
        return None
    try:
        from apps.rh.funcionarios.models import Funcionario
        sid = Funcionario.objects.get(usuario=request.user).setor_id
        return list(
            Funcionario.objects.filter(setor_id=sid)
            .exclude(usuario__isnull=True)
            .values_list('usuario_id', flat=True)
        )
    except Exception:
        return []


@login_required
@require_GET
@controle_acess('SCT201')
def api_get_supervisao_contratos_v2(request):
    """Kanban ContratoExecucao — formalização e pago cliente (supervisor, nexos)."""
    uids = _crm_supervisao_filtro_user_ids_fluxo(request)
    base = (
        ContratoExecucao.objects.filter(status=True)
        .select_related(
            'cliente_dados_pessoais',
            'proposta_dados',
            'solicitacao_digitacao__carteira_clientes__user_responsavel',
        )
        .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
    )
    if uids is not None:
        if not uids:
            colunas = {'LINK': [], 'CHECADO': [], 'FORMALIZADO': [], 'PAGAMENTO_TC': []}
            return JsonResponse({'ok': True, 'colunas': colunas})
        base = base.filter(solicitacao_digitacao__carteira_clientes__user_responsavel_id__in=uids)
    qs = base.order_by('-data_ultima_atualizacao')[:500]
    colunas = {'LINK': [], 'CHECADO': [], 'FORMALIZADO': [], 'PAGAMENTO_TC': []}
    for c in qs:
        item = {
            'contrato_id': c.id,
            'codigo': c.codigo,
            'cpf': c.cliente_dados_pessoais.cpf,
            'nome': c.cliente_dados_pessoais.nome_completo,
            'proposta_codigo': c.proposta_dados.codigo,
            'link_formalizacao': c.link_formalizacao or '',
            'etapa_operacional': c.etapa_operacional,
            'sub_status_operacional': c.sub_status_operacional,
        }
        sol = c.solicitacao_digitacao
        if sol and sol.carteira_clientes_id:
            cart = sol.carteira_clientes
            u = cart.user_responsavel
            item['vendedor'] = (u.get_full_name() or u.username) if u else ''
            item['carteira_id'] = cart.id
        if c.etapa_operacional == EtapaOperacional.DIGITACAO:
            if c.sub_status_operacional == SubStatusOperacional.DIG_LINK_DISPONIBILIZADO:
                colunas['LINK'].append(item)
            elif c.sub_status_operacional == SubStatusOperacional.DIG_CHECADO:
                colunas['CHECADO'].append(item)
            elif c.sub_status_operacional == SubStatusOperacional.DIG_FORMALIZADO:
                colunas['FORMALIZADO'].append(item)
        elif c.etapa_operacional == EtapaOperacional.PAGAMENTO and c.sub_status_operacional == SubStatusOperacional.PG_PAGO_CLIENTE:
            colunas['PAGAMENTO_TC'].append(item)
    return JsonResponse({'ok': True, 'colunas': colunas})


@login_required
@require_POST
def api_post_contrato_transicao(request, contrato_id):
    """Transição validada (acao + permissão por prefixo)."""
    data = _json_body(request)
    acao = (data.get('acao') or '').strip()
    observacao = (data.get('observacao') or '').strip()
    codigo_perm, papel = _codigo_acesso_para_acao(acao)
    if not codigo_perm or not papel:
        return JsonResponse({'ok': False, 'erro': 'Ação inválida.'}, status=400)
    try:
        ce = ContratoExecucao.objects.get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    if not _usuario_pode_executar_acao_transicao(request.user, acao, ce):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão para esta ação.'}, status=403)
    extras = None
    if acao == 'supervisor_pago_tc':
        rm_dict, err_rm = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
        if err_rm:
            return JsonResponse({'ok': False, 'erro': err_rm}, status=400)
        if rm_dict is not None:
            extras = {'registermoney': rm_dict}
    elif acao == 'operacional_pago_cliente':
        extras = _extras_operacional_pago_cliente(data)
    ok, msg = transicao_por_acao(ce, request.user, papel, acao, observacao=observacao, extras=extras)
    if not ok:
        return JsonResponse({'ok': False, 'erro': msg}, status=400)
    ce.refresh_from_db()
    try:
        sol = ce.solicitacao_digitacao
        cart = sol.carteira_clientes if sol and sol.carteira_clientes_id else None
        if cart and cart.status == 'ATIVO':
            deve_finalizar = False
            if ce.etapa_operacional == EtapaOperacional.CANCELADO:
                deve_finalizar = True
            if ce.tag_financeira == TagFinanceiraContrato.PAGO_TC:
                deve_finalizar = True
            if deve_finalizar:
                TabulacaoVendedor.objects.create(
                    carteira_clientes=cart,
                    user=request.user,
                    tipo='FINALIZADA',
                    observacao='Finalizado automaticamente via contratos (cancelado ou pago TC).',
                )
                cart.status_comercial = 'FINALIZADA'
                cart.save(update_fields=['status_comercial'])
                _sincronizar_agregado_operacional(cart)
    except Exception:
        pass
    return JsonResponse({
        'ok': True,
        'contrato': {
            'id': ce.id,
            'codigo': ce.codigo,
            'fase': ce.fase,
            'etapa_operacional': ce.etapa_operacional,
            'sub_status_operacional': ce.sub_status_operacional,
        },
    })


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_tabelas_cms_por_solicitacao(request):
    """Retorna TabelaCms filtradas pelo banco e produto da proposta vinculada à solicitação de digitação."""
    sid = request.GET.get('solicitacao_digitacao_id')
    if not sid:
        return JsonResponse({'ok': False, 'erro': 'solicitacao_digitacao_id obrigatório.'}, status=400)
    try:
        sol = (
            _solicitacao_digitacao_queryset_schema_seguro()
            .select_related('proposta_dados')
            .get(pk=int(sid))
        )
    except (ValueError, SolicitacaoDigitacao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
    pd = sol.proposta_dados
    tabelas = list(
        TabelaCms.objects.filter(
            banco_id=pd.banco_id,
            produto_id=pd.produto_id,
            status=True,
        ).values('id', 'titulo', 'classificador_banco').order_by('titulo')
    )
    return JsonResponse({
        'ok': True,
        'tabelas': tabelas,
        'tabela_cms_id_proposta': pd.tabela_cms_id,
        'tabela_cms_titulo_proposta': (pd.tabela_cms.titulo if pd.tabela_cms_id else ''),
    })


def _usuario_pode_novo_contrato(user):
    """Consulta SIAPE: enviar proposta para a esteira operacional (CX48)."""
    return user_has_access(user, COD_CX_NOVO_CONTRATO)


def _negar_novo_contrato_json():
    return JsonResponse({'ok': False, 'erro': 'Sem permissão para novo contrato (CX48).'}, status=403)


@login_required
@require_GET
def api_get_tabelas_cms_filtradas(request):
    """Filtra TabelaCms ativas por (banco, convenio, produto) para o modal de
    envio de proposta. Retorna lista vazia quando não há correspondência
    (front exibe "---nenhuma tabela disponível---").

    Permissão: CX48 (novo contrato na consulta SIAPE).
    """
    if not _usuario_pode_novo_contrato(request.user):
        return _negar_novo_contrato_json()
    try:
        banco_id = int(request.GET.get('banco_id') or 0) or None
        convenio_id = int(request.GET.get('convenio_id') or 0) or None
        produto_id = int(request.GET.get('produto_id') or 0) or None
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'Parâmetros inválidos.'}, status=400)
    if not (banco_id and convenio_id and produto_id):
        return JsonResponse({'ok': True, 'tabelas': []})
    tabelas = list(
        TabelaCms.objects.filter(
            banco_id=banco_id,
            convenio_id=convenio_id,
            produto_id=produto_id,
            status=True,
        ).values('id', 'titulo', 'classificador_banco', 'taxa_recebido', 'taxa_repasse', 'taxa_plastico')
        .order_by('titulo')
    )
    # Decimal → str para JSON
    for t in tabelas:
        for k in ('taxa_recebido', 'taxa_repasse', 'taxa_plastico'):
            if t.get(k) is not None:
                t[k] = str(t[k])
    return JsonResponse({'ok': True, 'tabelas': tabelas})


@login_required
@require_GET
def api_get_catalogos_contrato(request):
    """Catálogos banco/convênio/produto para telas operacionais."""
    bancos = list(Banco.objects.filter(status=True).values('id', 'titulo', 'codigo'))
    convenios = list(Convenio.objects.filter(status=True).values('id', 'titulo'))
    produtos = list(
        Produto.objects.filter(status=True).values(
            'id',
            'titulo',
            'flag_port_mais_refin',
            'flag_refin_da_port',
        )
    )
    return JsonResponse({'ok': True, 'bancos': bancos, 'convenios': convenios, 'produtos': produtos})


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints step-by-step: Simulação e Propostas (modais independentes)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_get_cliente_dados_pessoais_lookup(request):
    """Busca ClienteDadosPessoais por CPF e retorna todos os sub-modelos para auto-popular formulário."""
    if not _usuario_pode_novo_contrato(request.user):
        return _negar_novo_contrato_json()
    cpf        = _norm_cpf(request.GET.get('cpf', ''))
    carteira_id = request.GET.get('carteira_id')

    # Carrega dados básicos do siape.Cliente vinculado à carteira (para pré-preenchimento)
    dados_siape = {}
    if carteira_id:
        try:
            carteira_obj = CarteiraClientes.objects.select_related('cliente').get(id=carteira_id)
            cli = carteira_obj.cliente
            dados_siape = {
                'cpf':             cli.cpf or '',
                'nome_completo':   cli.nome or '',
                'data_nascimento': str(cli.data_nascimento) if cli.data_nascimento else '',
            }
            # Se o frontend não enviou CPF, tenta obtê-lo da carteira
            if not cpf:
                cpf = _norm_cpf(cli.cpf or '')
        except (CarteiraClientes.DoesNotExist, ValueError, AttributeError):
            pass

    if not cpf:
        return JsonResponse({'ok': False, 'message': 'CPF não informado.'}, status=400)

    try:
        dp = ClienteDadosPessoais.objects.get(cpf=cpf)
    except ClienteDadosPessoais.DoesNotExist:
        contatos_siape = _contatos_dinamicos_desde_siape(cpf)
        dados_resp = {}
        if contatos_siape:
            dados_resp['contatos_dinamicos'] = contatos_siape
        return JsonResponse({'ok': True, 'encontrado': False, 'dados': dados_resp, 'dados_siape': dados_siape})

    dados = {
        'id': dp.id,
        'nome_completo': dp.nome_completo or '',
        'sexo': dp.sexo or '',
        'data_nascimento': str(dp.data_nascimento) if dp.data_nascimento else '',
        'naturalidade': dp.naturalidade or '',
        'pais_origem': dp.pais_origem or '',
        'cpf': dp.cpf or '',
        'numero_rg': dp.numero_rg or '',
        'orgao_emissor_rg': dp.orgao_emissor_rg or '',
        'uf_emissao_rg': dp.uf_emissao_rg or '',
        'data_emissao_rg': str(dp.data_emissao_rg) if dp.data_emissao_rg else '',
        'nome_pai': dp.nome_pai or '',
        'nome_mae': dp.nome_mae or '',
    }

    # Contatos dinâmicos (se vazio no fluxo contratos, usa telefones ativos do SIAPE)
    dados['contatos_dinamicos'] = list(dp.contatos_dinamicos.values('tipo', 'valor'))
    if not dados['contatos_dinamicos']:
        dados['contatos_dinamicos'] = _contatos_dinamicos_desde_siape(cpf)

    # Endereços dinâmicos
    dados['enderecos_dinamicos'] = list(
        dp.enderecos_dinamicos.values('cep', 'logradouro', 'principal')
    )

    # Representantes dinâmicos
    dados['representantes_dinamicos'] = list(
        dp.representantes.values('nome_representante', 'cpf_representante')
    )

    # Dados bancários (conta de recebimento) — senha não é retornada por segurança
    try:
        cb = dp.bancario
    except ClienteBancario.DoesNotExist:
        cb = None
    if cb:
        dados['bancario'] = {
            'banco': cb.banco or '',
            'agencia': cb.agencia or '',
            'dv_agencia': cb.dv_agencia or '',
            'conta': cb.conta or '',
            'dv_conta': cb.dv_conta or '',
            'tipo_conta': cb.tipo_conta or '',
            'tipo_pagamento': cb.tipo_pagamento or '',
            'matricula': cb.matricula or '',
        }

    return JsonResponse({'ok': True, 'encontrado': True, 'dados': dados})


@login_required
@require_POST
@transaction.atomic
def api_post_cliente_dados_pessoais_salvar(request):
    """Cria ou atualiza ClienteDadosPessoais e sub-modelos (Contato, Endereço, Bancário, Representante)."""
    if not _usuario_pode_novo_contrato(request.user):
        return _negar_novo_contrato_json()
    # Aceita tanto JSON body quanto FormData com campo 'payload'
    if request.POST.get('payload'):
        try:
            data = json.loads(request.POST.get('payload') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'message': 'JSON inválido.'}, status=400)
    else:
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'message': 'JSON inválido.'}, status=400)

    cpf = _norm_cpf(data.get('cpf', ''))
    if not cpf:
        return JsonResponse({'ok': False, 'message': 'CPF obrigatório.'}, status=400)
    nome = (data.get('nome_completo') or '').strip()
    if not nome:
        return JsonResponse({'ok': False, 'message': 'Nome completo obrigatório.'}, status=400)

    # Dados pessoais
    dp, _ = ClienteDadosPessoais.objects.update_or_create(
        cpf=cpf,
        defaults={
            'nome_completo': nome,
            'sexo': (data.get('sexo') or '').strip() or None,
            'data_nascimento': data.get('data_nascimento') or None,
            'naturalidade': (data.get('naturalidade') or '').strip() or None,
            'pais_origem': (data.get('pais_origem') or '').strip() or None,
            'numero_rg': (data.get('numero_rg') or '').strip() or None,
            'orgao_emissor_rg': (data.get('orgao_emissor_rg') or '').strip() or None,
            'uf_emissao_rg': (data.get('uf_emissao_rg') or '').strip() or None,
            'data_emissao_rg': data.get('data_emissao_rg') or None,
            'nome_pai': (data.get('nome_pai') or '').strip() or None,
            'nome_mae': (data.get('nome_mae') or '').strip() or None,
        },
    )

    # Contatos dinâmicos — recria a lista completa
    contatos_data = data.get('contatos_dinamicos') or []
    dp.contatos_dinamicos.all().delete()
    for ct in contatos_data:
        tipo  = (ct.get('tipo')  or '').strip()
        valor = (ct.get('valor') or '').strip()
        if tipo and valor:
            ClienteContatoDinamico.objects.create(
                cliente_dados_pessoais=dp, tipo=tipo, valor=valor
            )

    # Endereços dinâmicos — recria a lista completa
    enderecos_data = data.get('enderecos_dinamicos') or []
    dp.enderecos_dinamicos.all().delete()
    principal_marcado = False
    for en in enderecos_data:
        cep_val        = (en.get('cep')        or '').strip() or None
        logradouro_val = (en.get('logradouro') or '').strip() or None
        is_principal   = bool(en.get('principal')) and not principal_marcado
        if is_principal:
            principal_marcado = True
        if cep_val or logradouro_val:
            ClienteEnderecoDinamico.objects.create(
                cliente_dados_pessoais=dp,
                cep=cep_val,
                logradouro=logradouro_val,
                principal=is_principal,
            )

    # Representantes dinâmicos — recria a lista completa
    reps_data = data.get('representantes_dinamicos') or []
    dp.representantes.all().delete()
    for rp in reps_data:
        nome = (rp.get('nome_representante') or '').strip() or None
        cpf  = (rp.get('cpf_representante')  or '').strip() or None
        if nome or cpf:
            ClienteRepresentante.objects.create(
                cliente_dados_pessoais=dp,
                nome_representante=nome,
                cpf_representante=cpf,
            )

    ban = data.get('bancario') or {}
    ClienteBancario.objects.update_or_create(
        cliente_dados_pessoais=dp,
        defaults={
            'banco': (ban.get('banco') or '').strip() or None,
            'agencia': (ban.get('agencia') or '').strip() or None,
            'dv_agencia': (ban.get('dv_agencia') or '').strip() or None,
            'conta': (ban.get('conta') or '').strip() or None,
            'dv_conta': (ban.get('dv_conta') or '').strip() or None,
            'tipo_conta': (ban.get('tipo_conta') or '').strip() or None,
            'tipo_pagamento': (ban.get('tipo_pagamento') or '').strip() or None,
            # Seguro não é mais ofertado na UI; mantém falso no cadastro
            'incluir_seguro': False,
            'matricula': (ban.get('matricula') or '').strip() or None,
            'senha': (ban.get('senha') or '').strip() or None,
        },
    )

    return JsonResponse({'ok': True, 'cliente_id': dp.id, 'cliente_nome': dp.nome_completo})


@login_required
@require_POST
@transaction.atomic
def api_post_solicitar_simulacao(request):
    """Finaliza o fluxo de Simulação: salva arquivos, cria SolicitacaoPropostaCliente e tabula a carteira."""
    carteira_id = request.POST.get('carteira_id') or ''
    cliente_dp_id = request.POST.get('cliente_dados_pessoais_id') or ''
    observacao = (request.POST.get('observacao') or '').strip()

    if not carteira_id or not cliente_dp_id:
        return JsonResponse({'ok': False, 'message': 'carteira_id e cliente_dados_pessoais_id são obrigatórios.'}, status=400)

    try:
        carteira = CarteiraClientes.objects.get(pk=int(carteira_id), user_responsavel=request.user)
    except (CarteiraClientes.DoesNotExist, ValueError):
        return JsonResponse({'ok': False, 'message': 'Carteira não encontrada ou sem permissão.'}, status=404)

    try:
        dp = ClienteDadosPessoais.objects.get(pk=int(cliente_dp_id))
    except (ClienteDadosPessoais.DoesNotExist, ValueError):
        return JsonResponse({'ok': False, 'message': 'Cliente não encontrado.'}, status=404)

    # Atualiza cliente_operacional na carteira se ainda não associado
    if carteira.cliente_operacional_id != dp.id:
        carteira.cliente_operacional = dp
        carteira.save(update_fields=['cliente_operacional'])

    # Salva arquivos associados ao cliente
    for arq in request.FILES.getlist('arquivos'):
        titulo = arq.name
        ext = titulo.rsplit('.', 1)[-1].lower() if '.' in titulo else ''
        ClienteArquivo.objects.create(
            cliente_dados_pessoais=dp,
            titulo=titulo,
            tipo=ext,
            arquivo=arq,
        )

    # Cria SolicitacaoPropostaCliente
    solicitacao = SolicitacaoPropostaCliente.objects.create(
        carteira_clientes=carteira,
        cliente_dados_pessoais=dp,
        estado=EstadoSolicitacaoProposta.ENVIADA,
        criado_por=request.user,
    )
    solicitacao.estado = EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL
    solicitacao.save(update_fields=['estado'])
    HistoricoEventoSimulacao.objects.create(
        solicitacao=solicitacao,
        estado_anterior=EstadoSolicitacaoProposta.ENVIADA,
        estado_novo=EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL,
        usuario=request.user,
    )

    # Tabula carteira
    _registrar_tabulacao(carteira, request.user, 'SIMULACAO', observacao=observacao)
    carteira.tag_proposta_container = 'AGUARDANDO'
    carteira.tag_status_operacional = 'AGUARDANDO_SIMULACAO'
    carteira.save(update_fields=['tag_proposta_container', 'tag_status_operacional'])
    _sincronizar_agregado_operacional(carteira)

    # Registra tag histórica
    TagStatusOperacional.objects.create(
        carteira_clientes=carteira,
        tag='AGUARDANDO_SIMULACAO',
        criado_por=request.user,
    )

    return JsonResponse({
        'ok': True,
        'message': 'Solicitação de simulação enviada com sucesso.',
        'solicitacao_id': solicitacao.id,
        'cliente_id': dp.id,
    })


@login_required
@require_POST
@transaction.atomic
def api_post_solicitar_propostas(request):
    """Finaliza o fluxo de Propostas: salva arquivos, cria PropostaDados, ContratoPortado e tabula a carteira.
    Cada item em POST `propostas` (JSON) pode incluir `contratos_portados`: lista de dicts para aquela linha."""
    if not _usuario_pode_novo_contrato(request.user):
        return _negar_novo_contrato_json()
    carteira_id = request.POST.get('carteira_id') or ''
    cliente_dp_id = request.POST.get('cliente_dados_pessoais_id') or ''
    observacao = (request.POST.get('observacao') or '').strip()
    propostas_json = request.POST.get('propostas') or '[]'
    if not carteira_id or not cliente_dp_id:
        return JsonResponse({'ok': False, 'message': 'carteira_id e cliente_dados_pessoais_id são obrigatórios.'}, status=400)

    try:
        carteira = CarteiraClientes.objects.get(pk=int(carteira_id), user_responsavel=request.user)
    except (CarteiraClientes.DoesNotExist, ValueError):
        return JsonResponse({'ok': False, 'message': 'Carteira não encontrada ou sem permissão.'}, status=404)

    try:
        dp = ClienteDadosPessoais.objects.get(pk=int(cliente_dp_id))
    except (ClienteDadosPessoais.DoesNotExist, ValueError):
        return JsonResponse({'ok': False, 'message': 'Cliente não encontrado.'}, status=404)

    try:
        propostas_data = json.loads(propostas_json)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'JSON das propostas inválido ou corrompido no envio.'}, status=400)
    if not isinstance(propostas_data, list):
        return JsonResponse({'ok': False, 'message': 'Campo propostas deve ser uma lista.'}, status=400)
    if not propostas_data:
        return JsonResponse({'ok': False, 'message': 'Informe ao menos uma proposta.'}, status=400)

    # Atualiza cliente_operacional na carteira se ainda não associado
    if carteira.cliente_operacional_id != dp.id:
        carteira.cliente_operacional = dp
        carteira.save(update_fields=['cliente_operacional'])

    # Salva arquivos associados ao cliente
    for arq in request.FILES.getlist('arquivos'):
        titulo = arq.name
        ext = titulo.rsplit('.', 1)[-1].lower() if '.' in titulo else ''
        ClienteArquivo.objects.create(
            cliente_dados_pessoais=dp,
            titulo=titulo,
            tipo=ext,
            arquivo=arq,
        )

    # Cria PropostaDados e solicitações de digitação (fila unificada CRM / Evoluir + tabela CMS)
    propostas_criadas = []
    solicitacoes_digitacao_ids = []
    erros_linhas = []
    for idx, prop in enumerate(propostas_data, start=1):
        if not isinstance(prop, dict):
            erros_linhas.append('Proposta #%d: formato inválido (esperado objeto).' % idx)
            continue
        banco_id = _int_pk_frontend(prop.get('banco_id'))
        convenio_id = _int_pk_frontend(prop.get('convenio_id'))
        produto_id = _int_pk_frontend(prop.get('produto_id'))
        if not (banco_id and convenio_id and produto_id):
            erros_linhas.append(
                'Proposta #%d: informe Banco, Convênio e Produto (IDs ausentes ou inválidos).' % idx
            )
            continue
        try:
            banco_obj = Banco.objects.get(pk=banco_id)
            convenio_obj = Convenio.objects.get(pk=convenio_id)
            produto_obj = Produto.objects.get(pk=produto_id)
        except (Banco.DoesNotExist, Convenio.DoesNotExist, Produto.DoesNotExist):
            erros_linhas.append(
                'Proposta #%d: banco (%s), convênio (%s) ou produto (%s) não encontrado no cadastro.'
                % (idx, banco_id, convenio_id, produto_id)
            )
            continue

        # Sanitização numérica: _dec converte string/None -> Decimal/None; rejeita negativos trocando por None.
        def _dec_nneg(v):
            d = _dec(v)
            if d is None:
                return None
            return d if d >= 0 else None

        valor_parcela = _dec_nneg(prop.get('valor_parcela'))
        valor_af = _dec_nneg(prop.get('valor_af'))
        valor_tc = _dec_nneg(prop.get('valor_tc'))
        coeficiente = _dec_nneg(prop.get('coeficiente'))

        # Prazo: inteiro positivo; aceita "96" ou "96.0" vindos do JSON.
        prazo_raw = prop.get('prazo')
        prazo_val = None
        if prazo_raw not in (None, '', '0', 0):
            try:
                pv = int(Decimal(str(prazo_raw).strip().replace(',', '.')))
                if pv >= 1:
                    prazo_val = pv
            except Exception:
                prazo_val = None

        # Regra de segurança: Liberado é SEMPRE recalculado no servidor (AF - TC, ou AF se TC=None/0).
        # Nunca confiar no valor_liberado enviado pelo cliente.
        if valor_af is not None:
            tc_eff = valor_tc if (valor_tc is not None) else Decimal('0')
            liberado_calc = valor_af - tc_eff
            if liberado_calc < 0:
                liberado_calc = Decimal('0')
        else:
            liberado_calc = None

        # Tabela CMS obrigatória; deve pertencer à tripla (banco, convênio, produto) e estar ativa.
        tabela_cms_raw = prop.get('tabela_cms_id')
        tcm_pk = _int_pk_frontend(tabela_cms_raw)
        if tcm_pk is None:
            erros_linhas.append('Proposta #%d: Tabela CMS é obrigatória.' % idx)
            continue
        try:
            tabela_cms_obj = TabelaCms.objects.get(
                pk=tcm_pk,
                banco_id=banco_obj.id,
                convenio_id=convenio_obj.id,
                produto_id=produto_obj.id,
                status=True,
            )
        except (TabelaCms.DoesNotExist, ValueError):
            erros_linhas.append(
                'Proposta #%d: Tabela CMS inválida ou incompatível com Banco, Convênio e Produto.'
                % idx
            )
            continue

        if proposta_ja_existe_para_cliente(
            dp,
            banco_obj.id,
            convenio_obj.id,
            produto_obj.id,
            valor_parcela,
            prazo_val,
            coeficiente,
        ):
            erros_linhas.append(MSG_PROPOSTA_JA_DIGITADA)
            continue

        pd_obj = PropostaDados.objects.create(
            cliente_dados_pessoais=dp,
            banco=banco_obj,
            convenio=convenio_obj,
            produto=produto_obj,
            tabela_cms=tabela_cms_obj,
            valor_parcela=valor_parcela,
            prazo=prazo_val,
            coeficiente=coeficiente,
            valor_af=valor_af,
            valor_tc=valor_tc,
            valor_liberado=liberado_calc,
            criado_por=request.user,
        )
        propostas_criadas.append(pd_obj)
        adicionar_proposta_operacional_na_carteira(carteira, pd_obj)

        # Dados bancários desta proposta (opcional)
        ban = prop.get('bancario') or {}
        if any((ban.get(k) or '').strip() for k in ('banco', 'agencia', 'conta')):
            ClienteBancario.objects.create(
                proposta_dados=pd_obj,
                banco=          (ban.get('banco')          or '').strip() or None,
                agencia=        (ban.get('agencia')        or '').strip() or None,
                dv_agencia=     (ban.get('dv_agencia')     or '').strip() or None,
                conta=          (ban.get('conta')          or '').strip() or None,
                dv_conta=       (ban.get('dv_conta')       or '').strip() or None,
                tipo_conta=     (ban.get('tipo_conta')     or '').strip() or None,
                tipo_pagamento= (ban.get('tipo_pagamento') or '').strip() or None,
                matricula=      (ban.get('matricula')      or '').strip() or None,
            )

        # Contratos portados se produto for portabilidade ou refinanciamento (mesma regra do wizard)
        nome_produto = produto_obj.titulo.upper()
        is_port = any(kw in nome_produto for kw in ('PORT', 'PORTABILIDADE', 'REFIN', 'REFINANCIAMENTO'))
        if is_port:
            portados_do_prop = prop.get('contratos_portados') or []
            if not isinstance(portados_do_prop, list):
                portados_do_prop = []
            for port in portados_do_prop:
                kwargs = _kwargs_contrato_portado_de_dict(port)
                if not kwargs:
                    continue
                kwargs['proposta_dados'] = pd_obj
                try:
                    ContratoPortado.objects.create(**kwargs)
                except ValidationError as ve:
                    transaction.set_rollback(True)
                    msgs = []
                    if getattr(ve, 'message_dict', None):
                        for _k, msg_list in ve.message_dict.items():
                            msgs.extend([str(m) for m in (msg_list or [])])
                    else:
                        msgs = [str(m) for m in ve.messages]
                    return JsonResponse({
                        'ok': False,
                        'message': 'Contrato de origem inválido na proposta #%d: %s' % (idx, '; '.join(msgs) or str(ve)),
                    }, status=400)
                except IntegrityError as ie:
                    transaction.set_rollback(True)
                    return JsonResponse({
                        'ok': False,
                        'message': 'Contrato de origem na proposta #%d: dados inconsistentes (%s).' % (idx, str(ie)),
                    }, status=400)

        # Mesmo fluxo que solicitar-digitacao-sem-pdf: uma solicitação por proposta (idempotente por par)
        if not SolicitacaoDigitacao.objects.filter(
            proposta_dados=pd_obj,
            carteira_clientes=carteira,
        ).exists():
            sol = SolicitacaoDigitacao.objects.create(
                proposta_dados=pd_obj,
                carteira_clientes=carteira,
                observacoes=observacao or None,
                arquivo_pdf_proposta=None,
                criado_por=request.user,
            )
            solicitacoes_digitacao_ids.append(sol.id)
            HistoricoEventoDigitacao.objects.create(
                solicitacao=sol,
                estado_anterior='',
                estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
                usuario=request.user,
            )

    if not propostas_criadas:
        msg = 'Nenhuma proposta válida. Verifique Banco, Convênio, Produto e Tabela CMS em cada linha.'
        if erros_linhas:
            msg = ' '.join(erros_linhas[:15])
            if len(erros_linhas) > 15:
                msg += ' (+%d)' % (len(erros_linhas) - 15)
        return JsonResponse({'ok': False, 'message': msg}, status=400)

    # Tabula carteira
    _registrar_tabulacao(carteira, request.user, 'OPERACIONAL', observacao=observacao)
    carteira.tag_proposta_container = 'AGUARDANDO'
    carteira.tag_status_operacional = 'AGUARDANDO_DIGITACAO'
    carteira.save(update_fields=['tag_proposta_container', 'tag_status_operacional'])
    _sincronizar_agregado_operacional(carteira)

    # Registra tag histórica
    TagStatusOperacional.objects.create(
        carteira_clientes=carteira,
        tag='AGUARDANDO_DIGITACAO',
        criado_por=request.user,
    )

    return JsonResponse({
        'ok': True,
        'message': 'Propostas enviadas com sucesso.',
        'propostas_criadas': len(propostas_criadas),
        'solicitacoes_digitacao_ids': solicitacoes_digitacao_ids,
        'cliente_id': dp.id,
    })


@csrf_exempt
@login_required
@require_POST
@transaction.atomic
def api_post_enviar_propostas_simuladas_para_digitacao(request):
    """
    Vendedor escolhe propostas simuladas já criadas pelo operacional e envia para digitação.
    JSON: carteira_id, proposta_ids: [], observacoes?
    """
    data = _json_body(request)
    carteira_id = data.get('carteira_id')
    proposta_ids = data.get('proposta_ids') or []
    observacoes = (data.get('observacoes') or '').strip()

    if not carteira_id or not proposta_ids:
        return JsonResponse({'ok': False, 'erro': 'carteira_id e proposta_ids são obrigatórios.'}, status=400)

    try:
        carteira = CarteiraClientes.objects.get(pk=int(carteira_id), user_responsavel=request.user)
    except (ValueError, CarteiraClientes.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Carteira não encontrada.'}, status=403)

    try:
        ids = [int(x) for x in proposta_ids]
    except Exception:
        return JsonResponse({'ok': False, 'erro': 'proposta_ids inválido.'}, status=400)

    qs_props = PropostaDados.objects.filter(id__in=ids)
    if carteira.cliente_operacional_id:
        qs_props = qs_props.filter(cliente_dados_pessoais_id=carteira.cliente_operacional_id)
    elif carteira.cliente_id and carteira.cliente.cpf:
        cpf = _norm_cpf(carteira.cliente.cpf)
        if cpf:
            qs_props = qs_props.filter(cliente_dados_pessoais__cpf=cpf)
    propostas = list(qs_props)
    if not propostas:
        return JsonResponse({'ok': False, 'erro': 'Nenhuma proposta válida encontrada para esta carteira.'}, status=400)

    criadas = []
    for proposta in propostas:
        existe = SolicitacaoDigitacao.objects.filter(
            proposta_dados=proposta,
            carteira_clientes=carteira,
        ).exists()
        if existe:
            adicionar_proposta_operacional_na_carteira(carteira, proposta)
            continue
        sol = SolicitacaoDigitacao.objects.create(
            proposta_dados=proposta,
            carteira_clientes=carteira,
            observacoes=observacoes or None,
            arquivo_pdf_proposta=None,
            criado_por=request.user,
        )
        criadas.append(sol.id)
        HistoricoEventoDigitacao.objects.create(
            solicitacao=sol,
            estado_anterior='',
            estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
            usuario=request.user,
        )
        proposta.aceita_pelo_cliente = True
        proposta.save(update_fields=['aceita_pelo_cliente'])
        adicionar_proposta_operacional_na_carteira(carteira, proposta)

    if not criadas:
        return JsonResponse({'ok': False, 'erro': 'As propostas selecionadas já foram enviadas para digitação.'}, status=400)

    _registrar_tabulacao(carteira, request.user, 'OPERACIONAL', sub_status_propostas='ACEITE')
    carteira.tag_proposta_container = 'AGUARDANDO'
    carteira.tag_status_operacional = 'AGUARDANDO_DIGITACAO'
    carteira.save(update_fields=['tag_proposta_container', 'tag_status_operacional'])
    _sincronizar_agregado_operacional(carteira)

    TagStatusOperacional.objects.create(
        carteira_clientes=carteira,
        tag='AGUARDANDO_DIGITACAO',
        criado_por=request.user,
    )

    return JsonResponse({'ok': True, 'solicitacoes_digitacao_ids': criadas, 'message': 'Propostas enviadas para digitação.'})


# ---------------------------------------------------------------------------
# CRM Unificado — Fila, Ficha, Transições e Evoluir
# ---------------------------------------------------------------------------

def _esteira_agora():
    """'Agora' no fuso do projeto — naive se USE_TZ=False (padrão MoneyConsig)."""
    agora = timezone.now()
    if timezone.is_aware(agora):
        return timezone.localtime(agora)
    return agora


def _esteira_as_local_dt(dt):
    """Normaliza data_criacao para comparar com _esteira_agora() (naive ou aware)."""
    if not dt:
        return None
    if timezone.is_aware(timezone.now()):
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return timezone.localtime(dt)
    if timezone.is_aware(dt):
        return timezone.make_naive(dt, timezone.get_current_timezone())
    return dt


def _esteira_filtros_from_request(request):
    """Query params opcionais compartilhados entre fila unificada e resumo KPI."""
    periodo = (request.GET.get('periodo') or '').strip() or None
    if periodo and periodo not in ('7d', '30d', 'mes_atual', 'mes_anterior'):
        periodo = None
    try:
        banco_id = int(request.GET.get('banco_id') or 0) or None
    except (TypeError, ValueError):
        banco_id = None
    try:
        convenio_id = int(request.GET.get('convenio_id') or 0) or None
    except (TypeError, ValueError):
        convenio_id = None
    try:
        produto_id = int(request.GET.get('produto_id') or 0) or None
    except (TypeError, ValueError):
        produto_id = None
    try:
        solicitante_id = int(request.GET.get('solicitante_id') or 0) or None
    except (TypeError, ValueError):
        solicitante_id = None
    return {
        'periodo': periodo,
        'banco_id': banco_id,
        'convenio_id': convenio_id,
        'produto_id': produto_id,
        'solicitante_id': solicitante_id,
    }


def _esteira_periodo_bounds(periodo):
    """Retorna (inicio, fim) para filtro por data_criacao; fim exclusivo quando aplicável."""
    if not periodo:
        return None, None
    now = _esteira_agora()
    if periodo == '7d':
        return now - timedelta(days=7), now
    if periodo == '30d':
        return now - timedelta(days=30), now
    if periodo == 'mes_atual':
        inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            fim = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            fim = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return inicio, fim
    if periodo == 'mes_anterior':
        inicio_atual = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fim = inicio_atual
        if inicio_atual.month == 1:
            inicio = inicio_atual.replace(year=inicio_atual.year - 1, month=12, day=1)
        else:
            inicio = inicio_atual.replace(month=inicio_atual.month - 1, day=1)
        return inicio, fim
    return None, None


def _esteira_mes_calendario_bounds(offset_meses=0):
    """offset_meses=0 mês atual; -1 mês anterior. Retorna (inicio, fim) com fim exclusivo."""
    now = _esteira_agora()
    y, m = now.year, now.month + offset_meses
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    inicio = now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)
    if m == 12:
        fim = inicio.replace(year=y + 1, month=1, day=1)
    else:
        fim = inicio.replace(month=m + 1, day=1)
    return inicio, fim


def _esteira_item_passa_filtros(item, filtros, aplicar_periodo=True):
    if filtros.get('banco_id') and item.get('banco_id') != filtros['banco_id']:
        return False
    if filtros.get('convenio_id') and item.get('convenio_id') != filtros['convenio_id']:
        return False
    if filtros.get('produto_id') and item.get('produto_id') != filtros['produto_id']:
        return False
    if filtros.get('solicitante_id') and item.get('solicitante_id') != filtros['solicitante_id']:
        return False
    if aplicar_periodo and filtros.get('periodo'):
        dt = item.get('data_criacao_dt')
        if dt is None:
            return False
        inicio, fim = _esteira_periodo_bounds(filtros['periodo'])
        if inicio and dt < inicio:
            return False
        if fim and dt >= fim:
            return False
    return True


def _esteira_filtrar_itens(itens, filtros, aplicar_periodo=True):
    return [it for it in itens if _esteira_item_passa_filtros(it, filtros, aplicar_periodo)]


def _esteira_serializar_item(item):
    d = {k: v for k, v in item.items() if k != 'data_criacao_dt'}
    dt = item.get('data_criacao_dt')
    d['data_criacao'] = dt.isoformat() if dt else ''
    return d


def _esteira_bucket_flags(item):
    etapa = item.get('etapa') or ''
    tem_pend = bool(item.get('tem_pendencia'))
    return {
        'em_andamento': etapa != EtapaOperacional.CANCELADO,
        'pendencias': etapa == EtapaOperacional.PENDENCIAS or tem_pend,
        'formalizacao': etapa == EtapaOperacional.FORMALIZACAO,
        'pagamentos': etapa == EtapaOperacional.PAGAMENTO,
        'cancelados': etapa == EtapaOperacional.CANCELADO,
    }


def _esteira_variacao_pct(atual, anterior):
    if not anterior:
        return None, 'neutral'
    pct = round((atual - anterior) / anterior * 100.0, 1)
    if pct > 0:
        return pct, 'up'
    if pct < 0:
        return pct, 'down'
    return pct, 'neutral'


def _esteira_calcular_kpis(itens_filtrados, itens_base_variacao):
    """Totais na fila filtrada; variação % por criação no mês calendário vs mês anterior."""
    buckets = ('em_andamento', 'pendencias', 'formalizacao', 'pagamentos', 'cancelados')
    totais = {b: 0 for b in buckets}
    for it in itens_filtrados:
        flags = _esteira_bucket_flags(it)
        for b in buckets:
            if flags[b]:
                totais[b] += 1

    inicio_atual, fim_atual = _esteira_mes_calendario_bounds(0)
    inicio_ant, fim_ant = _esteira_mes_calendario_bounds(-1)
    mes_atual = {b: 0 for b in buckets}
    mes_anterior = {b: 0 for b in buckets}
    for it in itens_base_variacao:
        dt = it.get('data_criacao_dt')
        if not dt:
            continue
        flags = _esteira_bucket_flags(it)
        if inicio_atual <= dt < fim_atual:
            for b in buckets:
                if flags[b]:
                    mes_atual[b] += 1
        elif inicio_ant <= dt < fim_ant:
            for b in buckets:
                if flags[b]:
                    mes_anterior[b] += 1

    kpis = {}
    for b in buckets:
        pct, tend = _esteira_variacao_pct(mes_atual[b], mes_anterior[b])
        kpis[b] = {
            'total': totais[b],
            'variacao_pct': pct,
            'tendencia': tend,
        }
    return kpis


def _esteira_repasse_campos_de_solicitacao(sol):
    """Solicitante e indicadores de repasse para linhas da esteira (pré-contrato)."""
    from apps.contratos_v2.services.repasse_carteira import resolver_contexto_repasse_contrato_from_carteira

    criado = ''
    criado_id = getattr(sol, 'criado_por_id', None)
    if getattr(sol, 'criado_por', None):
        criado = sol.criado_por.get_full_name() or sol.criado_por.username
    out = {
        'tem_repasse': False,
        'nome_repasse': '',
        'solicitante': criado,
        'solicitante_id': criado_id,
        'solicitante_label': criado,
    }
    cart = getattr(sol, 'carteira_clientes', None)
    if cart:
        ctx = resolver_contexto_repasse_contrato_from_carteira(cart)
        out['tem_repasse'] = ctx['tem_repasse']
        out['nome_repasse'] = ctx['nome_repasse']
        if ctx['tem_repasse']:
            out['solicitante'] = ctx['nome_responsavel_carteira'] or criado
            out['solicitante_label'] = ctx['solicitante_label'] or out['solicitante']
    return out


def _esteira_repasse_campos_de_contrato(ce):
    """Solicitante e indicadores de repasse para contratos na esteira."""
    from apps.contratos_v2.services.repasse_carteira import repasse_dict_esteira_ficha

    criado = ''
    criado_id = None
    if ce.solicitacao_digitacao_id and getattr(ce.solicitacao_digitacao, 'criado_por', None):
        u = ce.solicitacao_digitacao.criado_por
        criado = u.get_full_name() or u.username
        criado_id = u.id
    ctx = repasse_dict_esteira_ficha(ce)
    solicitante = criado
    label = criado
    if ctx['tem_repasse']:
        solicitante = ctx['nome_responsavel_carteira'] or criado
        label = ctx['solicitante_label'] or solicitante
    return {
        'tem_repasse': ctx['tem_repasse'],
        'nome_repasse': ctx['nome_repasse'],
        'solicitante': solicitante,
        'solicitante_id': criado_id,
        'solicitante_label': label,
    }


def _build_fila_unificada_itens():
    """Monta lista unificada (objetos internos com data_criacao_dt para filtros/KPI)."""
    out = []
    etapa_labels = dict(EtapaOperacional.CHOICES)
    sub_labels = dict(SubStatusOperacional.CHOICES)

    # 1. Simulações (SolicitacaoPropostaCliente)
    qs_sim = (
        SolicitacaoPropostaCliente.objects
        .filter(estado__in=[
            EstadoSolicitacaoProposta.ENVIADA,
            EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL,
            EstadoSolicitacaoProposta.RESULTADO_PROPOSTAS,
            EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL,
            'PENDENTE',
        ])
        .select_related('cliente_dados_pessoais', 'criado_por')
        .order_by('-data_criacao')[:200]
    )
    _sim_choices = dict(EstadoSolicitacaoProposta.CHOICES)
    for s in qs_sim:
        prop = (
            PropostaDados.objects
            .filter(solicitacao_origem=s)
            .select_related('banco', 'convenio', 'produto')
            .first()
        )
        solicitante = ''
        if s.criado_por:
            solicitante = s.criado_por.get_full_name() or s.criado_por.username
        out.append({
            'tipo': 'simulacao',
            'id': s.id,
            'proposta_codigo': prop.codigo if prop else '',
            'contrato_codigo': '',
            'nome_cliente': s.cliente_dados_pessoais.nome_completo,
            'cpf_cliente': s.cliente_dados_pessoais.cpf,
            'banco': prop.banco.titulo if prop and prop.banco_id else '—',
            'convenio': prop.convenio.titulo if prop and prop.convenio_id else '—',
            'produto': prop.produto.titulo if prop and prop.produto_id else '—',
            'banco_id': prop.banco_id if prop else None,
            'convenio_id': prop.convenio_id if prop else None,
            'produto_id': prop.produto_id if prop else None,
            'solicitante': solicitante,
            'solicitante_id': s.criado_por_id,
            'tem_pendencia': False,
            'link_formalizacao': '',
            'etapa': 'SIMULACAO',
            'etapa_label': 'Simulação',
            'sub_status': s.estado,
            'sub_status_label': _sim_choices.get(s.estado, s.estado),
            'observacao_resposta': (s.observacao_resposta or '').strip(),
            'data_criacao_dt': _esteira_as_local_dt(s.data_criacao),
        })

    # 2. SolicitacaoDigitacao pendentes (contrato ainda não gerado; inclui correção vendedor)
    _dig_labels = dict(EstadoSolicitacaoDigitacao.CHOICES)
    qs_dig = (
        SolicitacaoDigitacao.objects
        .filter(estado__in=[
            EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
            EstadoSolicitacaoDigitacao.EM_DIGITACAO,
            EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO,
        ])
        .select_related(
            'proposta_dados__banco',
            'proposta_dados__convenio',
            'proposta_dados__produto',
            'proposta_dados__cliente_dados_pessoais',
            'criado_por',
            'carteira_clientes',
            'carteira_clientes__user_repasse',
            'carteira_clientes__user_responsavel',
        )
        .order_by('-data_criacao')[:200]
    )
    for s in qs_dig:
        pd = s.proposta_dados
        rep_est = _esteira_repasse_campos_de_solicitacao(s)
        st = s.estado
        em_pend_correcao = st == EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO
        num_pre, _ = _solicitacao_digitacao_campos_pre_contrato_seguros(s)
        out.append({
            'tipo': 'solicitacao_dig',
            'id': s.id,
            'proposta_codigo': pd.codigo if pd else '',
            'contrato_codigo': '',
            'nome_cliente': pd.cliente_dados_pessoais.nome_completo if pd and pd.cliente_dados_pessoais_id else '',
            'cpf_cliente': pd.cliente_dados_pessoais.cpf if pd and pd.cliente_dados_pessoais_id else '',
            'banco': pd.banco.titulo if pd and pd.banco_id else '—',
            'convenio': pd.convenio.titulo if pd and pd.convenio_id else '—',
            'produto': pd.produto.titulo if pd and pd.produto_id else '—',
            'banco_id': pd.banco_id if pd else None,
            'convenio_id': pd.convenio_id if pd else None,
            'produto_id': pd.produto_id if pd else None,
            'solicitante': rep_est['solicitante'],
            'solicitante_id': rep_est['solicitante_id'],
            'solicitante_label': rep_est['solicitante_label'],
            'tem_repasse': rep_est['tem_repasse'],
            'nome_repasse': rep_est['nome_repasse'],
            'tem_pendencia': em_pend_correcao,
            'link_formalizacao': '',
            'etapa': EtapaOperacional.PENDENCIAS if em_pend_correcao else EtapaOperacional.DIGITACAO,
            'etapa_label': (
                etapa_labels.get(EtapaOperacional.PENDENCIAS, 'Pendências')
                if em_pend_correcao
                else etapa_labels.get('DIGITACAO', 'Digitando')
            ),
            'sub_status': st,
            'sub_status_label': _dig_labels.get(st, st),
            'requer_geracao_contrato': _solicitacao_digitacao_requer_geracao_contrato(st, em_pend_correcao),
            'numero_contrato_banco_pre': num_pre,
            'data_criacao_dt': _esteira_as_local_dt(s.data_criacao),
        })

    # 2b. Pré-contrato cancelado: última solicitação da proposta em CANCELADA e sem execução ativa.
    # Assim a aba Cancelado do CRM lista o mesmo tipo de caso já tratado em consulta cliente.
    ultima_sol_por_pd = {}
    for s in (
        SolicitacaoDigitacao.objects.select_related(
            'proposta_dados__banco',
            'proposta_dados__convenio',
            'proposta_dados__produto',
            'proposta_dados__cliente_dados_pessoais',
            'criado_por',
            'carteira_clientes',
            'carteira_clientes__user_repasse',
            'carteira_clientes__user_responsavel',
        )
        .order_by('-data_criacao')
        .iterator(chunk_size=500)
    ):
        pid = s.proposta_dados_id
        if not pid or pid in ultima_sol_por_pd:
            continue
        ultima_sol_por_pd[pid] = s

    pd_ids_com_ce_ativo = set(
        ContratoExecucao.objects.filter(status=True).values_list('proposta_dados_id', flat=True)
    )

    for _pid, s in ultima_sol_por_pd.items():
        if s.estado != EstadoSolicitacaoDigitacao.CANCELADA:
            continue
        if s.proposta_dados_id in pd_ids_com_ce_ativo:
            continue
        pd = s.proposta_dados
        if pd is None:
            continue
        rep_est = _esteira_repasse_campos_de_solicitacao(s)
        out.append({
            'tipo': 'solicitacao_dig',
            'id': s.id,
            'proposta_codigo': pd.codigo if pd else '',
            'contrato_codigo': '',
            'nome_cliente': pd.cliente_dados_pessoais.nome_completo if pd.cliente_dados_pessoais_id else '',
            'cpf_cliente': pd.cliente_dados_pessoais.cpf if pd.cliente_dados_pessoais_id else '',
            'banco': pd.banco.titulo if pd.banco_id else '—',
            'convenio': pd.convenio.titulo if pd.convenio_id else '—',
            'produto': pd.produto.titulo if pd.produto_id else '—',
            'banco_id': pd.banco_id if pd else None,
            'convenio_id': pd.convenio_id if pd else None,
            'produto_id': pd.produto_id if pd else None,
            'solicitante': rep_est['solicitante'],
            'solicitante_id': rep_est['solicitante_id'],
            'solicitante_label': rep_est['solicitante_label'],
            'tem_repasse': rep_est['tem_repasse'],
            'nome_repasse': rep_est['nome_repasse'],
            'tem_pendencia': False,
            'link_formalizacao': '',
            'etapa': EtapaOperacional.CANCELADO,
            'etapa_label': etapa_labels.get(EtapaOperacional.CANCELADO, 'Cancelado'),
            'sub_status': EstadoSolicitacaoDigitacao.CANCELADA,
            'sub_status_label': _dig_labels.get(EstadoSolicitacaoDigitacao.CANCELADA, 'Cancelada'),
            'data_criacao_dt': _esteira_as_local_dt(s.data_criacao),
        })

    # 3. ContratoExecucao (todos ativos)
    qs_ce = (
        ContratoExecucao.objects
        .filter(status=True)
        .select_related(
            'proposta_dados__banco',
            'proposta_dados__convenio',
            'proposta_dados__produto',
            'cliente_dados_pessoais',
            'solicitacao_digitacao__criado_por',
            'solicitacao_digitacao__carteira_clientes',
            'solicitacao_digitacao__carteira_clientes__user_repasse',
            'solicitacao_digitacao__carteira_clientes__user_responsavel',
            'user_repasse_snapshot',
            'carteira_clientes_snapshot',
            'carteira_clientes_snapshot__user_responsavel',
        )
        .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
        .order_by('-data_ultima_atualizacao')[:500]
    )
    for ce in qs_ce:
        try:
            op = ce.dados_operacionais
            banco = op.banco.titulo if op.banco_id else '—'
            convenio = op.convenio.titulo if op.convenio_id else '—'
            produto = op.produto.titulo if op.produto_id else '—'
        except Exception:
            pd2 = ce.proposta_dados
            banco = pd2.banco.titulo if pd2 and pd2.banco_id else '—'
            convenio = pd2.convenio.titulo if pd2 and pd2.convenio_id else '—'
            produto = pd2.produto.titulo if pd2 and pd2.produto_id else '—'
        rep_est = _esteira_repasse_campos_de_contrato(ce)
        banco_id_ce = convenio_id_ce = produto_id_ce = None
        try:
            op_ce = ce.dados_operacionais
            banco_id_ce = op_ce.banco_id
            convenio_id_ce = op_ce.convenio_id
            produto_id_ce = op_ce.produto_id
        except Exception:
            pd2_ids = ce.proposta_dados
            if pd2_ids:
                banco_id_ce = pd2_ids.banco_id
                convenio_id_ce = pd2_ids.convenio_id
                produto_id_ce = pd2_ids.produto_id
        out.append({
            'tipo': 'contrato',
            'id': ce.id,
            'proposta_codigo': ce.proposta_dados.codigo if ce.proposta_dados_id else '',
            'contrato_codigo': ce.codigo or '',
            'nome_cliente': ce.cliente_dados_pessoais.nome_completo,
            'cpf_cliente': ce.cliente_dados_pessoais.cpf,
            'banco': banco,
            'convenio': convenio,
            'produto': produto,
            'banco_id': banco_id_ce,
            'convenio_id': convenio_id_ce,
            'produto_id': produto_id_ce,
            'solicitante': rep_est['solicitante'],
            'solicitante_id': rep_est['solicitante_id'],
            'solicitante_label': rep_est['solicitante_label'],
            'tem_repasse': rep_est['tem_repasse'],
            'nome_repasse': rep_est['nome_repasse'],
            'tem_pendencia': ce.etapa_operacional == EtapaOperacional.PENDENCIAS,
            'link_formalizacao': ce.link_formalizacao or '',
            'etapa': ce.etapa_operacional,
            'etapa_label': etapa_labels.get(ce.etapa_operacional, ce.etapa_operacional),
            'sub_status': ce.sub_status_operacional,
            'sub_status_label': sub_labels.get(ce.sub_status_operacional, ce.sub_status_operacional),
            'portabilidade': ce.portabilidade,
            'data_criacao_dt': _esteira_as_local_dt(ce.data_criacao),
        })

    return out


def _esteira_solicitantes_opcoes(itens):
    """Lista única de solicitantes para o select (id + nome)."""
    vistos = {}
    for it in itens:
        sid = it.get('solicitante_id')
        nome = str(it.get('solicitante') or '').strip()
        if sid and nome and sid not in vistos:
            vistos[sid] = nome
    return [{'id': k, 'nome': v} for k, v in sorted(vistos.items(), key=lambda x: x[1].lower())]


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_fila_unificada(request):
    """Retorna simulações, solicitações de digitação pendentes e contratos em lista unificada."""
    filtros = _esteira_filtros_from_request(request)
    todos = _build_fila_unificada_itens()
    filtrados = _esteira_filtrar_itens(todos, filtros, aplicar_periodo=True)
    itens_json = [_esteira_serializar_item(it) for it in filtrados]
    return JsonResponse({'ok': True, 'itens': itens_json})


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_esteira_resumo(request):
    """KPIs da esteira operacional (totais + variação % vs mês anterior por criação)."""
    filtros = _esteira_filtros_from_request(request)
    todos = _build_fila_unificada_itens()
    filtrados = _esteira_filtrar_itens(todos, filtros, aplicar_periodo=True)
    filtros_sem_periodo = dict(filtros)
    filtros_sem_periodo['periodo'] = None
    base_variacao = _esteira_filtrar_itens(todos, filtros_sem_periodo, aplicar_periodo=False)
    kpis = _esteira_calcular_kpis(filtrados, base_variacao)
    return JsonResponse({
        'ok': True,
        'kpis': kpis,
        'solicitantes': _esteira_solicitantes_opcoes(todos),
    })


def _bancario_ficha_dict(b):
    """Dados bancários (ClienteBancario) para ficha/PDF — não expõe senha em texto claro."""
    if b is None:
        return None
    tem_senha = bool(b.senha and str(b.senha).strip())
    return {
        'banco': b.banco or '',
        'agencia': b.agencia or '',
        'dv_agencia': b.dv_agencia or '',
        'conta': b.conta or '',
        'dv_conta': b.dv_conta or '',
        'tipo_conta': b.tipo_conta or '',
        'tipo_pagamento': b.tipo_pagamento or '',
        'incluir_seguro': bool(b.incluir_seguro),
        'matricula': b.matricula or '',
        'senha_cadastrada': tem_senha,
    }


def _bancario_ficha_dict_vazio():
    """Estrutura vazia para PDF exibir todas as células mesmo sem ClienteBancario."""
    return {
        'banco': '',
        'agencia': '',
        'dv_agencia': '',
        'conta': '',
        'dv_conta': '',
        'tipo_conta': '',
        'tipo_pagamento': '',
        'incluir_seguro': False,
        'matricula': '',
        'senha_cadastrada': False,
    }


def _produto_exige_contrato_portado(titulo_produto):
    """Exibe contrato portado na ficha/PDF só se o título do produto indicar PORT ou REFIN (catálogo por nome)."""
    u = (titulo_produto or '').upper()
    return 'PORT' in u or 'REFIN' in u


def _rotulo_contrato_origem_produto(titulo_produto):
    """Rótulo da seção de contrato de origem conforme o produto (PORT vs REFIN)."""
    u = (titulo_produto or '').upper()
    if 'REFIN' in u:
        return 'Contrato refinanciado'
    if 'PORT' in u:
        return 'Contrato portado'
    return 'Contrato de origem'


def _bancario_tem_dados(b):
    """True se há algum dado bancário preenchido (para omitir seção vazia no PDF)."""
    if not b:
        return False
    for k in ('banco', 'agencia', 'dv_agencia', 'conta', 'dv_conta', 'tipo_conta', 'tipo_pagamento', 'matricula'):
        if str(b.get(k) or '').strip():
            return True
    return bool(b.get('incluir_seguro')) or bool(b.get('senha_cadastrada'))


def _fmt_moeda_pdf(val):
    """Formata valor numérico para exibição em PDF (R$ pt-BR)."""
    if val is None:
        return '—'
    s = str(val).strip()
    if not s:
        return '—'
    try:
        from decimal import Decimal
        d = Decimal(s.replace(',', '.'))
        neg = d < 0
        d = abs(d)
        inteiro, _, frac = f'{d:.2f}'.partition('.')
        partes = []
        while inteiro:
            partes.insert(0, inteiro[-3:])
            inteiro = inteiro[:-3]
        inteiro_fmt = '.'.join(partes) if partes else '0'
        out = f'R$ {inteiro_fmt},{frac}'
        return ('- ' + out) if neg else out
    except Exception:
        return s


def _fmt_taxa_snapshot(val):
    if val is None:
        return ''
    return str(val)


def _contrato_portado_ficha_dict(cp):
    """Contrato de origem (portabilidade) para exibição na ficha do CRM."""
    return {
        'id': cp.id,
        'banco': cp.banco.titulo if cp.banco_id else '—',
        'numero_contrato': (cp.numero_contrato or '').strip(),
        'valor_parcela': str(cp.valor_parcela) if cp.valor_parcela is not None else '',
        'valor_af': str(cp.valor_af) if cp.valor_af is not None else '',
        'valor_devedor_total': str(cp.valor_devedor_total) if cp.valor_devedor_total is not None else '',
        'prazo_total': cp.prazo_total if cp.prazo_total is not None else '',
        'prazo_restante': cp.prazo_restante if cp.prazo_restante is not None else '',
    }


def _proposta_ficha_dict(p, solicitante_override=None):
    from apps.contratos_v2.services.port_refin import (
        exibe_valor_saldo_ficha_produto,
        produto_indica_portabilidade,
    )

    prod = p.produto if p.produto_id else None
    titulo_prod = prod.titulo if prod else ''
    exibe_saldo, rotulo_saldo = exibe_valor_saldo_ficha_produto(prod)
    exige_port = _produto_exige_contrato_portado(titulo_prod)
    if exige_port:
        portados = [_contrato_portado_ficha_dict(cp) for cp in p.contratos_portados.all()]
    else:
        portados = []
    db_prop = None
    try:
        db_prop = p.dados_bancarios
    except ClienteBancario.DoesNotExist:
        db_prop = None
    banc_prop = _bancario_ficha_dict(db_prop) if db_prop else _bancario_ficha_dict_vazio()
    solicitante = (solicitante_override or '').strip()
    if not solicitante and p.criado_por_id:
        solicitante = p.criado_por.get_full_name() or p.criado_por.username
    tabela_cms = ''
    if p.tabela_cms_id:
        tabela_cms = (p.tabela_cms.titulo or '').strip()
    return {
        'id': p.id,
        'codigo': p.codigo,
        'banco': p.banco.titulo if p.banco_id else '—',
        'convenio': p.convenio.titulo if p.convenio_id else '—',
        'produto': titulo_prod or '—',
        'tabela_cms': tabela_cms,
        'solicitante': solicitante,
        'valor_parcela': str(p.valor_parcela) if p.valor_parcela is not None else '',
        'prazo': p.prazo or '',
        'valor_af': str(p.valor_af) if p.valor_af is not None else '',
        'valor_tc': str(p.valor_tc) if p.valor_tc is not None else '',
        'valor_liberado': str(p.valor_liberado) if p.valor_liberado is not None else '',
        'valor_saldo': str(p.valor_saldo) if getattr(p, 'valor_saldo', None) is not None else '',
        'exibe_valor_saldo': exibe_saldo,
        'rotulo_valor_saldo': rotulo_saldo,
        'portabilidade_produto': produto_indica_portabilidade(prod),
        'coeficiente': str(p.coeficiente) if getattr(p, 'coeficiente', None) is not None else '',
        'aceita_pelo_cliente': bool(p.aceita_pelo_cliente),
        'criado_por': (p.criado_por.get_full_name() or p.criado_por.username) if p.criado_por_id else '',
        'data_criacao': p.data_criacao.strftime('%d/%m/%Y %H:%M') if p.data_criacao else '',
        'produto_exige_portado': exige_port,
        'rotulo_contrato_origem': _rotulo_contrato_origem_produto(titulo_prod),
        'contratos_portados': portados,
        'dados_bancarios_proposta': banc_prop,
    }


class FichaPayloadError(Exception):
    """Erro ao montar payload da ficha (mensagem + HTTP status)."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _observacao_pendencia_correcao_digitacao(sol):
    """Observação informada ao marcar pendência (transição que entra em PENDENTE_CORRECAO).

    Ignora eventos com mesmo estado anterior/novo (ex.: auditoria de edição CRM no modal),
    que também usam estado_novo=PENDENTE_CORRECAO mas não são a devolução ao vendedor.
    """
    if not sol or not getattr(sol, 'pk', None):
        return ''
    h = (
        sol.historico_eventos.filter(estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO)
        .exclude(estado_anterior=EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO)
        .order_by('-data')
        .only('observacao')
        .first()
    )
    if h and (h.observacao or '').strip():
        return (h.observacao or '').strip()
    return ''


def _ficha_montar_payload(tipo, pk):
    """Monta dict solicitacao, propostas, contrato, historico, dados_pessoais (incl. dados bancários)."""
    resultado = {}
    dp = None

    if tipo == 'simulacao':
        try:
            sol = SolicitacaoPropostaCliente.objects.select_related(
                'cliente_dados_pessoais',
                'cliente_dados_pessoais__bancario',
                'criado_por',
                'carteira_clientes',
                'carteira_clientes__user_repasse',
                'carteira_clientes__user_responsavel',
            ).get(pk=pk)
        except SolicitacaoPropostaCliente.DoesNotExist:
            raise FichaPayloadError('Solicitação não encontrada.', 404)
        dp = sol.cliente_dados_pessoais
        _cp_qs = ContratoPortado.objects.select_related('banco')
        sol_criado = (sol.criado_por.get_full_name() or sol.criado_por.username) if sol.criado_por else ''
        propostas = list(
            PropostaDados.objects.filter(solicitacao_origem=sol)
            .select_related('banco', 'convenio', 'produto', 'tabela_cms', 'dados_bancarios', 'criado_por')
            .prefetch_related(Prefetch('contratos_portados', queryset=_cp_qs))
            .order_by('id')
        )
        resultado['solicitacao'] = {
            'id': sol.id,
            'estado': sol.estado,
            'criado_por': sol_criado,
            'data_criacao': sol.data_criacao.strftime('%d/%m/%Y %H:%M') if sol.data_criacao else '',
            'observacao_resposta': (sol.observacao_resposta or '').strip(),
        }
        resultado['propostas'] = [_proposta_ficha_dict(p, solicitante_override=sol_criado or None) for p in propostas]
        resultado['contrato'] = None
        resultado['historico'] = _historico_simulacao_list(sol)
        from apps.contratos_v2.services.repasse_carteira import repasse_dict_ficha

        resultado['repasse'] = repasse_dict_ficha(
            carteira=sol.carteira_clientes if sol.carteira_clientes_id else None,
            nome_solicitante_criador=sol_criado,
        )

    elif tipo == 'solicitacao_dig':
        _cp_qs_dig = ContratoPortado.objects.select_related('banco')
        try:
            sol = (
                _solicitacao_digitacao_queryset_schema_seguro()
                .select_related(
                    'proposta_dados__banco',
                    'proposta_dados__convenio',
                    'proposta_dados__produto',
                    'proposta_dados__tabela_cms',
                    'proposta_dados__criado_por',
                    'proposta_dados__cliente_dados_pessoais',
                    'proposta_dados__cliente_dados_pessoais__bancario',
                    'proposta_dados__dados_bancarios',
                    'criado_por',
                    'carteira_clientes',
                    'carteira_clientes__user_repasse',
                    'carteira_clientes__user_responsavel',
                )
                .prefetch_related(
                    Prefetch('proposta_dados__contratos_portados', queryset=_cp_qs_dig)
                )
                .get(pk=pk)
            )
        except SolicitacaoDigitacao.DoesNotExist:
            raise FichaPayloadError('Solicitação não encontrada.', 404)
        # Defesa contra solicitação sem proposta/cliente associado (caso raro mas evita 500).
        pd = sol.proposta_dados
        if pd is None:
            raise FichaPayloadError('Solicitação sem proposta associada.', 400)
        dp = pd.cliente_dados_pessoais
        if dp is None:
            raise FichaPayloadError('Proposta sem cliente associado.', 400)
        num_pre, link_pre = _solicitacao_digitacao_campos_pre_contrato_seguros(sol)
        sol_criado_dig = (sol.criado_por.get_full_name() or sol.criado_por.username) if sol.criado_por else ''
        resultado['solicitacao'] = {
            'id': sol.id,
            'estado': sol.estado,
            'criado_por': sol_criado_dig,
            'data_criacao': sol.data_criacao.strftime('%d/%m/%Y %H:%M') if sol.data_criacao else '',
            'observacoes': (sol.observacoes or '').strip(),
            'observacao_pendencia_operacional': _observacao_pendencia_correcao_digitacao(sol),
            'numero_contrato_banco_pre': num_pre,
            'link_formalizacao_pre': link_pre,
        }
        resultado['propostas'] = [_proposta_ficha_dict(pd, solicitante_override=sol_criado_dig or None)]
        resultado['contrato'] = None
        resultado['historico'] = _historico_digitacao_list(sol)
        from apps.contratos_v2.services.repasse_carteira import repasse_dict_ficha

        resultado['repasse'] = repasse_dict_ficha(
            carteira=sol.carteira_clientes if sol.carteira_clientes_id else None,
            nome_solicitante_criador=sol_criado_dig,
        )

    elif tipo == 'contrato':
        _cp_qs_ce = ContratoPortado.objects.select_related('banco')
        try:
            ce = (
                ContratoExecucao.objects.select_related(
                    'proposta_dados__banco',
                    'proposta_dados__convenio',
                    'proposta_dados__produto',
                    'proposta_dados__tabela_cms',
                    'proposta_dados__criado_por',
                    'proposta_dados__dados_bancarios',
                    'cliente_dados_pessoais',
                    'cliente_dados_pessoais__bancario',
                    'solicitacao_digitacao__criado_por',
                    'solicitacao_digitacao__carteira_clientes__user_repasse',
                    'solicitacao_digitacao__carteira_clientes__user_responsavel',
                    'user_repasse_snapshot',
                    'carteira_clientes_snapshot',
                    'dados_operacionais',
                    'dados_operacionais__tabela_cms',
                    'dados_operacionais__banco',
                    'dados_operacionais__convenio',
                    'dados_operacionais__produto',
                )
                .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
                .prefetch_related(
                    Prefetch('proposta_dados__contratos_portados', queryset=_cp_qs_ce)
                )
                .get(pk=pk, status=True)
            )
        except ContratoExecucao.DoesNotExist:
            raise FichaPayloadError('Contrato não encontrado.', 404)
        dp = ce.cliente_dados_pessoais
        pd = ce.proposta_dados
        exibir_pdf = ce.sub_status_operacional == SubStatusOperacional.ANU_AGUARDANDO
        nr_sup = ce.nivel_risco_checagem_supervisor
        nr_sup_lbl = (
            dict(ContratoExecucao.NivelRiscoChecagemSupervisor.choices).get(nr_sup, '') if nr_sup else ''
        )
        obs_entrada_pend = ''
        try:
            # Observação do modal Evoluir ao entrar em pendências (não mudanças só de sub-status).
            h_pend = (
                HistoricoTransicaoContrato.objects.filter(
                    contrato_execucao=ce,
                    etapa_nova=EtapaOperacional.PENDENCIAS,
                )
                .exclude(etapa_anterior=EtapaOperacional.PENDENCIAS)
                .order_by('-data')
                .only('observacao')
                .first()
            )
            if h_pend and getattr(h_pend, 'observacao', None):
                obs_entrada_pend = (h_pend.observacao or '').strip()
        except Exception:
            pass
        sol_vend_ctr = ''
        if ce.solicitacao_digitacao_id and getattr(ce, 'solicitacao_digitacao', None):
            u_sol = ce.solicitacao_digitacao.criado_por
            if u_sol:
                sol_vend_ctr = u_sol.get_full_name() or u_sol.username
        base_ctr = {
            'id': ce.id,
            'codigo': ce.codigo,
            'data_criacao': ce.data_criacao.strftime('%d/%m/%Y %H:%M') if ce.data_criacao else '',
            'etapa_operacional': ce.etapa_operacional,
            'sub_status_operacional': ce.sub_status_operacional,
            'link_formalizacao': ce.link_formalizacao or '',
            'portabilidade': ce.portabilidade,
            'exibir_secao_contrato_pdf': exibir_pdf,
            'nivel_risco_checagem_supervisor': nr_sup or '',
            'nivel_risco_checagem_supervisor_label': nr_sup_lbl,
            'observacao_checagem_consultor': (ce.observacao_checagem_consultor or '').strip(),
            'pendencia_etapa_origem': (getattr(ce, 'pendencia_etapa_origem', None) or '').strip(),
            'pendencia_sub_origem': (getattr(ce, 'pendencia_sub_origem', None) or '').strip(),
            'observacao_entrada_pendencias': obs_entrada_pend,
        }
        try:
            op = ce.dados_operacionais
            titulo_tab = (op.tabela_cms_titulo_snapshot or '').strip() or (
                op.tabela_cms.titulo if op.tabela_cms_id else ''
            )
            prod_ctr = op.produto if op.produto_id else None
            from apps.contratos_v2.services.port_refin import (
                contrato_indica_portabilidade,
                exibe_valor_saldo_ficha_produto,
                resolver_valor_saldo_exibicao_ce,
            )

            exibe_saldo_ctr, rotulo_saldo_ctr = exibe_valor_saldo_ficha_produto(prod_ctr)
            vs_local = op.valor_saldo if op.valor_saldo is not None else None
            valor_saldo_ctr = resolver_valor_saldo_exibicao_ce(ce, vs_local) if exibe_saldo_ctr else ''
            if not valor_saldo_ctr and vs_local is not None:
                valor_saldo_ctr = str(vs_local)
            contrato_dict = {
                **base_ctr,
                'tabela_cms': titulo_tab or '—',
                'taxa_recebido_snapshot': _fmt_taxa_snapshot(op.taxa_recebido_snapshot),
                'taxa_repasse_snapshot': _fmt_taxa_snapshot(op.taxa_repasse_snapshot),
                'taxa_plastico_snapshot': _fmt_taxa_snapshot(op.taxa_plastico_snapshot),
                'data_att_cms': op.data_att_cms.strftime('%d/%m/%Y %H:%M') if op.data_att_cms else '',
                'valor_parcela': str(op.valor_parcela) if op.valor_parcela is not None else '',
                'prazo': op.prazo or '',
                'valor_af': str(op.valor_af) if op.valor_af is not None else '',
                'valor_tc': str(op.valor_tc) if op.valor_tc is not None else '',
                'valor_liberado': str(op.valor_liberado) if op.valor_liberado is not None else '',
                'valor_saldo': valor_saldo_ctr,
                'exibe_valor_saldo': exibe_saldo_ctr,
                'rotulo_valor_saldo': rotulo_saldo_ctr,
                'portabilidade_efetiva': contrato_indica_portabilidade(ce),
            }
        except Exception:
            from apps.contratos_v2.services.port_refin import contrato_indica_portabilidade

            contrato_dict = {
                **base_ctr,
                'tabela_cms': '—',
                'taxa_recebido_snapshot': '',
                'taxa_repasse_snapshot': '',
                'taxa_plastico_snapshot': '',
                'data_att_cms': '',
                'valor_parcela': '',
                'prazo': '',
                'valor_af': '',
                'valor_tc': '',
                'valor_liberado': '',
                'valor_saldo': '',
                'exibe_valor_saldo': False,
                'rotulo_valor_saldo': 'Valor Saldo',
                'portabilidade_efetiva': contrato_indica_portabilidade(ce),
            }
        if 'data_criacao' not in contrato_dict:
            contrato_dict['data_criacao'] = base_ctr.get('data_criacao', '')
        try:
            from apps.contratos_v2.services.port_refin import vinculo_port_refin_dict

            contrato_dict['vinculo_port_refin'] = vinculo_port_refin_dict(ce)
        except Exception:
            contrato_dict['vinculo_port_refin'] = {'papel': None}
        from apps.contratos_v2.services.repasse_carteira import repasse_dict_ficha

        resultado['repasse'] = repasse_dict_ficha(
            ce=ce,
            nome_solicitante_criador=sol_vend_ctr,
        )
        resultado['solicitacao'] = None
        resultado['propostas'] = [_proposta_ficha_dict(pd, solicitante_override=sol_vend_ctr or None)]
        resultado['contrato'] = contrato_dict
        resultado['historico'] = _historico_contrato_list(ce)
    else:
        raise FichaPayloadError('tipo inválido.', 400)

    dp_dict = {
        'id': dp.id,
        'nome_completo': dp.nome_completo,
        'cpf': dp.cpf,
        'sexo': dp.sexo or '',
        'data_nascimento': str(dp.data_nascimento) if dp.data_nascimento else '',
        'naturalidade': dp.naturalidade or '',
        'pais_origem': dp.pais_origem or '',
        'numero_rg': dp.numero_rg or '',
        'orgao_emissor_rg': dp.orgao_emissor_rg or '',
        'uf_emissao_rg': dp.uf_emissao_rg or '',
        'data_emissao_rg': str(dp.data_emissao_rg) if dp.data_emissao_rg else '',
        'nome_pai': dp.nome_pai or '',
        'nome_mae': dp.nome_mae or '',
        'data_criacao': dp.data_criacao.strftime('%d/%m/%Y %H:%M') if dp.data_criacao else '',
        'data_atualizacao': dp.data_atualizacao.strftime('%d/%m/%Y %H:%M') if dp.data_atualizacao else '',
        'email': '', 'telefone': '', 'telefone_residencial': '', 'email_secundario': '',
        'cep': '', 'logradouro': '',
    }
    try:
        ct = dp.contato
        dp_dict['email'] = ct.email or ''
        dp_dict['email_secundario'] = ct.email_secundario or ''
        dp_dict['telefone'] = ct.telefone or ''
        dp_dict['telefone_residencial'] = ct.telefone_residencial or ''
    except Exception:
        pass
    try:
        end = dp.endereco
        dp_dict['cep'] = end.cep or ''
        dp_dict['logradouro'] = end.logradouro or ''
    except Exception:
        pass
    dp_dict['contatos_dinamicos'] = [
        {'tipo': c.tipo, 'tipo_label': c.get_tipo_display(), 'valor': c.valor or ''}
        for c in dp.contatos_dinamicos.order_by('id')
    ]
    dp_dict['enderecos_dinamicos'] = list(
        dp.enderecos_dinamicos.order_by('-principal', 'id').values('cep', 'logradouro', 'principal')
    )
    dp_dict['representantes'] = list(dp.representantes.values('nome_representante', 'cpf_representante'))
    try:
        bd = dp.bancario
        dp_dict['dados_bancarios'] = _bancario_ficha_dict(bd)
    except ClienteBancario.DoesNotExist:
        # Sempre dict completo para telas (ex.: checagem loja) exibirem rótulos com "—".
        dp_dict['dados_bancarios'] = _bancario_ficha_dict_vazio()
    resultado['dados_pessoais'] = dp_dict
    return resultado


_FICHA_PDF_LABEL_TIPO = {
    'solicitacao_dig': 'Solicitação de digitação',
    'contrato': 'Contrato em execução',
    'simulacao': 'Simulação',
}


def _ficha_pdf_reportlab(payload, tipo_label):
    """Gera bytes PDF a partir do mesmo dict da ficha (sem histórico).
    Layout referência Proposta de Empréstimo: faixas ordenadas; rótulos em maiúsculas; valores destacados;
    campos vazios como —; contatos/endereços via cadastro dinâmico.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    left_m = right_m = top_m = bottom_m = 1.35 * cm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=left_m,
        rightMargin=right_m,
        topMargin=top_m,
        bottomMargin=bottom_m,
    )
    usable_w = A4[0] - left_m - right_m
    col_w = usable_w / 3.0
    cols = 3
    pad_pt = 3
    border_pt = 1

    styles = getSampleStyleSheet()
    banner_style = ParagraphStyle(
        'FichaBanner',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=0,
    )
    subheading_style = ParagraphStyle(
        'FichaSubheading',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
        spaceAfter=0,
        spaceBefore=2,
    )
    field_wrap = ParagraphStyle(
        'FichaFieldWrap',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        spaceAfter=0,
        spaceBefore=0,
        wordWrap='CJK',
    )

    elements = []

    def esc(s):
        if s is None:
            return ''
        t = str(s)
        return (
            t.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )

    def _disp(v):
        """Valor para exibição: vazio vira —."""
        if v is None:
            return '—'
        if isinstance(v, bool):
            return 'Sim' if v else 'Não'
        s = str(v).strip()
        return s if s else '—'

    def _table_shell():
        return [
            ('BOX', (0, 0), (-1, -1), border_pt, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), border_pt, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), pad_pt),
            ('RIGHTPADDING', (0, 0), (-1, -1), pad_pt),
            ('TOPPADDING', (0, 0), (-1, -1), pad_pt),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad_pt),
        ]

    def add_section_banner(titulo):
        """Faixa com borda, título centralizado (estilo formulário)."""
        p = Paragraph('<para alignment="center"><b>' + esc(titulo) + '</b></para>', banner_style)
        tbl = Table([[p]], colWidths=[usable_w])
        tbl.setStyle(TableStyle([('BOX', (0, 0), (0, 0), border_pt, colors.black), ('ALIGN', (0, 0), (0, 0), 'CENTER'), ('VALIGN', (0, 0), (0, 0), 'MIDDLE'), ('LEFTPADDING', (0, 0), (0, 0), pad_pt), ('RIGHTPADDING', (0, 0), (0, 0), pad_pt), ('TOPPADDING', (0, 0), (0, 0), pad_pt), ('BOTTOMPADDING', (0, 0), (0, 0), pad_pt)]))
        elements.append(tbl)

    def add_subheading(txt):
        """Subtítulo alinhado à esquerda dentro da seção Dados da operação."""
        p = Paragraph('<b>' + esc(txt) + '</b>', subheading_style)
        t = Table([[p]], colWidths=[usable_w])
        t.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), pad_pt),
            ('RIGHTPADDING', (0, 0), (-1, -1), pad_pt),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(t)

    def make_field_cell(titulo, valor):
        """Rótulo em maiúsculas, negrito, menor; valor maior abaixo."""
        lab = esc(str(titulo or '')).upper()
        val = esc(_disp(valor))
        html = (
            '<b><font name="Helvetica-Bold" size="6">' + lab + '</font></b><br/>'
            '<font name="Helvetica" size="8">' + val + '</font>'
        )
        return Paragraph(html, field_wrap)

    def _pairs_append_sempre(pairs, titulo, valor):
        pairs.append((titulo, _disp(valor)))

    def _campo_largura_total(titulo, valor):
        t = str(titulo or '')
        sv = str(valor if valor is not None else '')
        if len(sv) > 90:
            return True
        for chave in (
            'Observação',
            'Logradouro',
            'Link formalização',
            'Endereço adicional',
            'Contrato origem',
        ):
            if chave in t:
                return True
        return False

    def add_kv_grid(pairs):
        """Grade: linha inteira para campos longos; demais em 3 colunas."""
        if not pairs:
            return
        i = 0
        n = len(pairs)
        while i < n:
            titulo, valor = pairs[i]
            if _campo_largura_total(titulo, valor):
                tbl = Table([[make_field_cell(titulo, valor)]], colWidths=[usable_w])
                tbl.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), border_pt, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), pad_pt), ('RIGHTPADDING', (0, 0), (-1, -1), pad_pt), ('TOPPADDING', (0, 0), (-1, -1), pad_pt), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_pt)]))
                elements.append(tbl)
                i += 1
                continue
            chunk_cells = []
            while i < n and len(chunk_cells) < cols:
                t2, v2 = pairs[i]
                if _campo_largura_total(t2, v2):
                    break
                chunk_cells.append(make_field_cell(t2, v2))
                i += 1
            if not chunk_cells:
                continue
            while len(chunk_cells) < cols:
                chunk_cells.append(make_field_cell('\u00a0', '—'))
            tbl = Table([chunk_cells], colWidths=[col_w] * cols)
            tbl.setStyle(TableStyle(_table_shell()))
            elements.append(tbl)
        elements.append(Spacer(1, 2))

    props0 = payload.get('propostas') or []
    dp = payload.get('dados_pessoais') or {}
    sol = payload.get('solicitacao')
    ctr = payload.get('contrato')
    tem_contrato_ficha = bool(ctr)

    def _bloco_contrato():
        mostrar_ctr = bool(ctr)
        if not mostrar_ctr and sol:
            if (sol.get('numero_contrato_banco_pre') or '').strip() or (sol.get('link_formalizacao_pre') or '').strip():
                mostrar_ctr = True
        if not mostrar_ctr:
            return
        add_section_banner('Dados do Contrato')
        pr = []
        if ctr:
            _pairs_append_sempre(pr, 'Nº contrato', ctr.get('codigo'))
            _pairs_append_sempre(pr, 'Etapa operacional', ctr.get('etapa_operacional'))
            _pairs_append_sempre(pr, 'Sub-status', ctr.get('sub_status_operacional'))
            _pairs_append_sempre(pr, 'Tabela CMS', ctr.get('tabela_cms'))
            _pairs_append_sempre(pr, 'Valor TC', _fmt_moeda_pdf(ctr.get('valor_tc')))
            _pairs_append_sempre(pr, 'Valor AF', _fmt_moeda_pdf(ctr.get('valor_af')))
            _pairs_append_sempre(pr, 'Valor parcela', _fmt_moeda_pdf(ctr.get('valor_parcela')))
            _pairs_append_sempre(pr, 'Prazo (meses)', ctr.get('prazo'))
            _pairs_append_sempre(pr, 'Valor liberado', _fmt_moeda_pdf(ctr.get('valor_liberado')))
            _pairs_append_sempre(pr, 'Portabilidade', 'Sim' if ctr.get('portabilidade') else 'Não')
            _pairs_append_sempre(pr, 'Link formalização', ctr.get('link_formalizacao'))
            if ctr.get('exibir_secao_contrato_pdf'):
                _pairs_append_sempre(pr, 'Taxa recebido (snapshot)', ctr.get('taxa_recebido_snapshot'))
                _pairs_append_sempre(pr, 'Taxa repasse (snapshot)', ctr.get('taxa_repasse_snapshot'))
                _pairs_append_sempre(pr, 'Taxa plástico (snapshot)', ctr.get('taxa_plastico_snapshot'))
                _pairs_append_sempre(pr, 'Última alteração CMS', ctr.get('data_att_cms'))
        elif sol:
            _pairs_append_sempre(pr, 'Nº contrato (banco)', sol.get('numero_contrato_banco_pre'))
            _pairs_append_sempre(pr, 'Link formalização', sol.get('link_formalizacao_pre'))
        add_kv_grid(pr)

    def _bloco_proposta():
        if not props0:
            return
        tit_prop = 'Dados Proposta' if tem_contrato_ficha else 'Proposta de Empréstimo'
        add_section_banner(tit_prop)
        for idx, p in enumerate(props0):
            if len(props0) > 1:
                add_subheading('Proposta #' + str(idx + 1))
            pr_prop = []
            _pairs_append_sempre(pr_prop, 'Banco', p.get('banco'))
            _pairs_append_sempre(pr_prop, 'Convênio', p.get('convenio'))
            _pairs_append_sempre(pr_prop, 'Produto', p.get('produto'))
            _pairs_append_sempre(pr_prop, 'Tabela', p.get('tabela_cms'))
            _pairs_append_sempre(pr_prop, 'Solicitante', p.get('solicitante'))
            _pairs_append_sempre(pr_prop, 'Valor TC', _fmt_moeda_pdf(p.get('valor_tc')))
            _pairs_append_sempre(pr_prop, 'Valor AF', _fmt_moeda_pdf(p.get('valor_af')))
            _pairs_append_sempre(pr_prop, 'Valor parcela', _fmt_moeda_pdf(p.get('valor_parcela')))
            _pairs_append_sempre(pr_prop, 'Prazo (meses)', p.get('prazo'))
            _pairs_append_sempre(pr_prop, 'Valor liberado', _fmt_moeda_pdf(p.get('valor_liberado')))
            _pairs_append_sempre(pr_prop, 'Código da proposta', p.get('codigo'))
            add_kv_grid(pr_prop)

    def _bloco_portado_refin():
        for idx, p in enumerate(props0):
            if not p.get('produto_exige_portado'):
                continue
            tit_sec = p.get('rotulo_contrato_origem') or 'Contrato de origem'
            if len(props0) > 1:
                tit_sec = tit_sec + ' — proposta #' + str(idx + 1)
            add_section_banner(tit_sec)
            portados = p.get('contratos_portados') or []
            if not portados:
                pr = []
                _pairs_append_sempre(pr, 'Banco origem', '')
                _pairs_append_sempre(pr, 'Nº contrato', '')
                _pairs_append_sempre(pr, 'Valor parcela', '')
                _pairs_append_sempre(pr, 'Valor AF', '')
                _pairs_append_sempre(pr, 'Saldo devedor', '')
                _pairs_append_sempre(pr, 'Prazo total', '')
                _pairs_append_sempre(pr, 'Prazo restante', '')
                add_kv_grid(pr)
                continue
            for j, cp in enumerate(portados):
                if len(portados) > 1:
                    add_subheading(tit_sec + ' #' + str(j + 1))
                pr = []
                _pairs_append_sempre(pr, 'Banco origem', cp.get('banco'))
                _pairs_append_sempre(pr, 'Nº contrato', cp.get('numero_contrato'))
                _pairs_append_sempre(pr, 'Valor parcela', _fmt_moeda_pdf(cp.get('valor_parcela')))
                _pairs_append_sempre(pr, 'Valor AF', _fmt_moeda_pdf(cp.get('valor_af')))
                _pairs_append_sempre(pr, 'Saldo devedor', _fmt_moeda_pdf(cp.get('valor_devedor_total')))
                _pairs_append_sempre(pr, 'Prazo total', cp.get('prazo_total'))
                _pairs_append_sempre(pr, 'Prazo restante', cp.get('prazo_restante'))
                add_kv_grid(pr)

    def _bloco_bancario_proposta():
        for idx, p in enumerate(props0):
            dbp = p.get('dados_bancarios_proposta')
            if not _bancario_tem_dados(dbp):
                continue
            add_section_banner('Dados bancários (proposta #' + str(idx + 1) + ')')
            pr = []
            _pairs_append_sempre(pr, 'Banco', dbp.get('banco'))
            _pairs_append_sempre(pr, 'Agência', dbp.get('agencia'))
            _pairs_append_sempre(pr, 'DV agência', dbp.get('dv_agencia'))
            _pairs_append_sempre(pr, 'Conta', dbp.get('conta'))
            _pairs_append_sempre(pr, 'DV conta', dbp.get('dv_conta'))
            _pairs_append_sempre(pr, 'Tipo de conta', dbp.get('tipo_conta'))
            _pairs_append_sempre(pr, 'Tipo de pagamento', dbp.get('tipo_pagamento'))
            _pairs_append_sempre(pr, 'Matrícula', dbp.get('matricula'))
            _pairs_append_sempre(
                pr,
                'Senha bancária',
                'Cadastrada (omitida)' if dbp.get('senha_cadastrada') else '—',
            )
            _pairs_append_sempre(pr, 'Seguro', 'Sim' if dbp.get('incluir_seguro') else 'Não')
            add_kv_grid(pr)

    def _bloco_proposta_completo():
        _bloco_proposta()
        _bloco_portado_refin()
        _bloco_bancario_proposta()

    def _bloco_pessoais():
        add_section_banner('Dados pessoais')
        pr = []
        _pairs_append_sempre(pr, 'Nome', dp.get('nome_completo'))
        _pairs_append_sempre(pr, 'CPF', dp.get('cpf'))
        _pairs_append_sempre(pr, 'Sexo', dp.get('sexo'))
        _pairs_append_sempre(pr, 'Data de nascimento', dp.get('data_nascimento'))
        _pairs_append_sempre(pr, 'Naturalidade', dp.get('naturalidade'))
        _pairs_append_sempre(pr, 'País de origem', dp.get('pais_origem'))
        _pairs_append_sempre(pr, 'RG', dp.get('numero_rg'))
        _pairs_append_sempre(pr, 'Órgão emissor RG', dp.get('orgao_emissor_rg'))
        _pairs_append_sempre(pr, 'UF emissão RG', dp.get('uf_emissao_rg'))
        _pairs_append_sempre(pr, 'Data emissão RG', dp.get('data_emissao_rg'))
        _pairs_append_sempre(pr, 'Nome do pai', dp.get('nome_pai'))
        _pairs_append_sempre(pr, 'Nome da mãe', dp.get('nome_mae'))
        add_kv_grid(pr)

    def _bloco_contato():
        add_section_banner('Contato')
        pr = []
        emails_vistos = set()
        n_email = 0
        for em in (dp.get('email'), dp.get('email_secundario')):
            em_s = (em or '').strip()
            if not em_s or em_s in emails_vistos:
                continue
            emails_vistos.add(em_s)
            n_email += 1
            rot = 'E-mail' if n_email == 1 else 'E-mail (' + str(n_email) + ')'
            _pairs_append_sempre(pr, rot, em_s)
        n_cel = 0
        for c in dp.get('contatos_dinamicos') or []:
            t = (c.get('tipo') or '').upper()
            v = (c.get('valor') or '').strip()
            if not v:
                continue
            if t == 'EMAIL':
                if v in emails_vistos:
                    continue
                emails_vistos.add(v)
                n_email += 1
                rot = c.get('tipo_label') or 'E-mail'
                if n_email > 1:
                    rot = rot + ' (' + str(n_email) + ')'
                _pairs_append_sempre(pr, rot, v)
            elif t in ('CELULAR', 'TELEFONE_FIXO'):
                n_cel += 1
                rot = c.get('tipo_label') or ('Celular' if t == 'CELULAR' else 'Telefone')
                if n_cel > 1:
                    rot = rot + ' (' + str(n_cel) + ')'
                _pairs_append_sempre(pr, rot, v)
        if n_cel == 0:
            for tel, rot_base in ((dp.get('telefone'), 'Telefone'), (dp.get('telefone_residencial'), 'Telefone residencial')):
                tel_s = (tel or '').strip()
                if not tel_s:
                    continue
                n_cel += 1
                rot = rot_base if n_cel == 1 else rot_base + ' (' + str(n_cel) + ')'
                _pairs_append_sempre(pr, rot, tel_s)
        if not pr:
            _pairs_append_sempre(pr, 'E-mail', '')
            _pairs_append_sempre(pr, 'Telefone / celular', '')
        add_kv_grid(pr)

    def _bloco_bancario_cliente():
        add_section_banner('Dados bancários do cliente')
        db = dp.get('dados_bancarios') if dp.get('dados_bancarios') is not None else _bancario_ficha_dict_vazio()
        pr = []
        _pairs_append_sempre(pr, 'Banco', db.get('banco'))
        _pairs_append_sempre(pr, 'Agência', db.get('agencia'))
        _pairs_append_sempre(pr, 'DV agência', db.get('dv_agencia'))
        _pairs_append_sempre(pr, 'Conta', db.get('conta'))
        _pairs_append_sempre(pr, 'DV conta', db.get('dv_conta'))
        _pairs_append_sempre(pr, 'Tipo de conta', db.get('tipo_conta'))
        _pairs_append_sempre(pr, 'Tipo de pagamento', db.get('tipo_pagamento'))
        _pairs_append_sempre(pr, 'Matrícula', db.get('matricula'))
        _pairs_append_sempre(
            pr,
            'Senha bancária',
            'Cadastrada (omitida)' if db.get('senha_cadastrada') else '—',
        )
        _pairs_append_sempre(pr, 'Seguro', 'Sim' if db.get('incluir_seguro') else 'Não')
        add_kv_grid(pr)

    def _bloco_outros():
        add_section_banner('Outros')
        pr = []
        _pairs_append_sempre(pr, 'Data criação cadastro', dp.get('data_criacao'))
        _pairs_append_sempre(pr, 'Última atualização cadastro', dp.get('data_atualizacao'))
        data_ctr = ''
        if ctr and ctr.get('data_criacao'):
            data_ctr = ctr.get('data_criacao')
        _pairs_append_sempre(pr, 'Data criação contrato', data_ctr)
        add_kv_grid(pr)

    def _bloco_representante():
        reps = dp.get('representantes') or []
        if not reps:
            return
        add_section_banner('Representante')
        pr = []
        for i, r in enumerate(reps):
            suf = ' (' + str(i + 1) + ')' if len(reps) > 1 else ''
            _pairs_append_sempre(pr, 'Nome' + suf, r.get('nome_representante'))
            _pairs_append_sempre(pr, 'CPF' + suf, r.get('cpf_representante'))
        add_kv_grid(pr)

    # Ordem: com contrato executado, contrato vem primeiro e proposta após dados bancários.
    if tem_contrato_ficha:
        _bloco_contrato()
        _bloco_pessoais()
        _bloco_contato()
        _bloco_bancario_cliente()
        _bloco_proposta_completo()
        _bloco_outros()
        _bloco_representante()
    else:
        _bloco_proposta_completo()
        _bloco_pessoais()
        _bloco_contato()
        _bloco_bancario_cliente()
        _bloco_outros()
        _bloco_contrato()
        _bloco_representante()

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()


@login_required
@require_GET
def api_get_ficha(request):
    """Dados completos (dados pessoais + proposta/contrato + histórico) para o modal Visualizar Ficha.

    Query params:
        - tipo: tipo da ficha (simulacao/proposta/contrato).
        - id:   pk do objeto.
        - with_historico (opcional): '0'/'false'/'no' para OMITIR o campo
          ``historico`` do payload. Qualquer outro valor (ou ausência) mantém
          o comportamento legado (inclui histórico). Essa opção existe para
          reduzir o payload quando o consumidor abre o modal de ficha sem
          precisar da linha do tempo embutida (critério 10 da validação [6]).
    """
    from apps.contratos_v2.apis.carteira_contrato_permissoes import pode_visualizar_contrato_ficha_ou_midia

    tipo = request.GET.get('tipo')
    pk = request.GET.get('id')
    if not tipo or not pk:
        return JsonResponse({'ok': False, 'erro': 'tipo e id obrigatórios.'}, status=400)
    try:
        pk = int(pk)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'erro': 'id inválido.'}, status=400)
    # Envelopa o restante para garantir resposta JSON mesmo quando o banco ainda não tem a migração 0050 aplicada.
    try:
        if tipo != 'contrato' and not _acesso_crm_operacional_ou_supervisao_siape(request.user):
            # Vendedor: ficha da solicitação de digitação em pendência de correção (pré-contrato), mesma carteira.
            if tipo == 'solicitacao_dig':
                from apps.contratos_v2.fluxo_constants import EstadoSolicitacaoDigitacao as _ESD

                sol_chk = (
                    _solicitacao_digitacao_queryset_schema_seguro()
                    .filter(pk=pk)
                    .select_related('carteira_clientes')
                    .first()
                )
                if not sol_chk:
                    return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
                cart = sol_chk.carteira_clientes
                # Mesmo critério da carteira na consulta cliente: responsável ou repasse (SIAPE).
                pode_vendedor = (
                    sol_chk.estado == _ESD.PENDENTE_CORRECAO
                    and cart is not None
                    and (
                        cart.user_responsavel_id == request.user.id
                        or cart.user_repasse_id == request.user.id
                    )
                )
                if not pode_vendedor:
                    return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
            else:
                return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
        if tipo == 'contrato':
            ce_chk = (
                ContratoExecucao.objects.filter(pk=pk, status=True)
                .select_related('solicitacao_digitacao', 'proposta_dados__solicitacao_origem')
                .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
                .first()
            )
            if not ce_chk:
                return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
            if not pode_visualizar_contrato_ficha_ou_midia(request.user, ce_chk):
                return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
        try:
            resultado = _ficha_montar_payload(tipo, pk)
        except FichaPayloadError as e:
            return JsonResponse({'ok': False, 'erro': e.message}, status=e.status)
    except DatabaseError as exc:
        # Schema desatualizado: provavelmente a migração de SolicitacaoDigitacao não foi aplicada.
        logger.exception('api_get_ficha (DatabaseError) tipo=%s id=%s: %s', tipo, pk, exc)
        return JsonResponse(
            {
                'ok': False,
                'erro': (
                    'Schema do banco desatualizado para esta tela. '
                    'Solicite ao administrador que execute as migrações pendentes.'
                ),
            },
            status=500,
        )
    except Exception as exc:
        # Loga traceback completo (django_errors.log) e devolve JSON para o frontend tratar.
        logger.exception('api_get_ficha falhou (tipo=%s, id=%s): %s', tipo, pk, exc)
        return JsonResponse(
            {'ok': False, 'erro': 'Erro interno ao montar a ficha. Verifique o log do servidor.'},
            status=500,
        )

    # Opt-out: quando with_historico=0/false/no, removemos 'historico' do payload.
    with_hist_raw = (request.GET.get('with_historico') or '').strip().lower()
    if with_hist_raw in ('0', 'false', 'no', 'nao', 'não'):
        resultado.pop('historico', None)

    return JsonResponse({'ok': True, 'tipo': tipo, **resultado})


@login_required
@require_GET
def api_get_ficha_pdf(request):
    """PDF da ficha (sem linha do tempo) — não disponível para tipo simulacao."""
    from apps.contratos_v2.apis.carteira_contrato_permissoes import (
        pode_visualizar_contrato_ficha_ou_midia,
        vendedor_pode_acesso_pendencia_contrato,
    )

    tipo = request.GET.get('tipo')
    pk = request.GET.get('id')
    if not tipo or not pk:
        return JsonResponse({'ok': False, 'erro': 'tipo e id obrigatórios.'}, status=400)
    try:
        pk = int(pk)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'erro': 'id inválido.'}, status=400)
    if tipo != 'contrato' and not _acesso_crm_operacional_ou_supervisao_siape(request.user):
        if tipo == 'solicitacao_dig':
            from apps.contratos_v2.fluxo_constants import EstadoSolicitacaoDigitacao as _ESD

            sol_chk = (
                _solicitacao_digitacao_queryset_schema_seguro()
                .filter(pk=pk)
                .select_related('carteira_clientes')
                .first()
            )
            if not sol_chk:
                return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
            cart = sol_chk.carteira_clientes
            # Mesmo critério da carteira na consulta cliente: responsável ou repasse (SIAPE).
            pode_vendedor = (
                sol_chk.estado == _ESD.PENDENTE_CORRECAO
                and cart is not None
                and (
                    cart.user_responsavel_id == request.user.id
                    or cart.user_repasse_id == request.user.id
                )
            )
            if not pode_vendedor:
                return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
        else:
            return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
    if tipo == 'contrato':
        ce_chk = (
            ContratoExecucao.objects.filter(pk=pk, status=True)
            .select_related('solicitacao_digitacao', 'proposta_dados__solicitacao_origem')
            .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
            .first()
        )
        if not ce_chk:
            return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
        if not pode_visualizar_contrato_ficha_ou_midia(request.user, ce_chk):
            return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
    try:
        resultado = _ficha_montar_payload(tipo, pk)
    except FichaPayloadError as e:
        return JsonResponse({'ok': False, 'erro': e.message}, status=e.status)
    if tipo == 'simulacao' and not (resultado.get('propostas') or []):
        return JsonResponse({'ok': False, 'erro': 'PDF indisponível: solicitação sem proposta registrada.'}, status=400)
    resultado.pop('historico', None)
    pdf_bytes = _ficha_pdf_reportlab(resultado, tipo)
    nome = 'ficha-registro-{}-{}.pdf'.format(tipo, pk)
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="{}"'.format(nome)
    return resp


def _fmt_data_hist(dt, fmt='%d/%m/%Y %H:%M'):
    return dt.strftime(fmt) if dt else ''


def _historico_contrato_list(ce, data_fmt='%d/%m/%Y %H:%M'):
    """Serializa HistoricoTransicaoContrato (ordem cronológica)."""
    historico_qs = (
        HistoricoTransicaoContrato.objects.filter(contrato_execucao=ce)
        .select_related('usuario')
        .order_by('data')
    )
    _sub_labels = dict(SubStatusOperacional.CHOICES)
    _eta_labels = dict(EtapaOperacional.CHOICES)
    return [
        {
            'etapa_anterior': h.etapa_anterior,
            'etapa_anterior_label': _eta_labels.get(h.etapa_anterior, h.etapa_anterior),
            'sub_anterior': h.sub_anterior,
            'sub_anterior_label': _sub_labels.get(h.sub_anterior, h.sub_anterior),
            'etapa_nova': h.etapa_nova,
            'etapa_nova_label': _eta_labels.get(h.etapa_nova, h.etapa_nova),
            'sub_nova': h.sub_nova,
            'sub_nova_label': _sub_labels.get(h.sub_nova, h.sub_nova),
            'usuario': (h.usuario.get_full_name() or h.usuario.username) if h.usuario else '—',
            'observacao': h.observacao or '',
            'data': _fmt_data_hist(h.data, data_fmt),
        }
        for h in historico_qs
    ]


def _historico_simulacao_list(sol, data_fmt='%d/%m/%Y %H:%M'):
    """Serializa HistoricoEventoSimulacao para exibição na linha do tempo."""
    _labels = dict(EstadoSolicitacaoProposta.CHOICES)
    return [
        {
            'estado_anterior': h.estado_anterior,
            'estado_anterior_label': _labels.get(h.estado_anterior, h.estado_anterior),
            'estado_novo': h.estado_novo,
            'estado_novo_label': _labels.get(h.estado_novo, h.estado_novo),
            'usuario': (h.usuario.get_full_name() or h.usuario.username) if h.usuario else '—',
            'observacao': h.observacao or '',
            'data': _fmt_data_hist(h.data, data_fmt),
        }
        for h in sol.historico_eventos.select_related('usuario').order_by('data')
    ]


def _historico_digitacao_list(sol, data_fmt='%d/%m/%Y %H:%M'):
    """Serializa HistoricoEventoDigitacao para exibição na linha do tempo."""
    _labels = dict(EstadoSolicitacaoDigitacao.CHOICES)
    return [
        {
            'estado_anterior': h.estado_anterior,
            'estado_anterior_label': _labels.get(h.estado_anterior, h.estado_anterior),
            'estado_novo': h.estado_novo,
            'estado_novo_label': _labels.get(h.estado_novo, h.estado_novo),
            'usuario': (h.usuario.get_full_name() or h.usuario.username) if h.usuario else '—',
            'observacao': h.observacao or '',
            'data': _fmt_data_hist(h.data, data_fmt),
        }
        for h in sol.historico_eventos.select_related('usuario').order_by('data')
    ]


@login_required
@require_GET
@controle_acess_multiplos(COD_SS_ESTEIRA, COD_SIAPE_CRM_SUPERVISAO)
def api_get_auditoria_fluxo(request):
    """Histórico de transições (timeline) para o modal de auditoria no CRM — payload enxuto."""
    tipo = request.GET.get('tipo')
    pk_raw = request.GET.get('id')
    if not tipo or not pk_raw:
        return JsonResponse({'ok': False, 'erro': 'tipo e id obrigatórios.'}, status=400)
    try:
        pk = int(pk_raw)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'erro': 'id inválido.'}, status=400)

    fmt = '%d/%m/%Y %H:%M:%S'

    if tipo == 'simulacao':
        try:
            sol = SolicitacaoPropostaCliente.objects.select_related(
                'cliente_dados_pessoais', 'criado_por'
            ).get(pk=pk)
        except SolicitacaoPropostaCliente.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
        prop = PropostaDados.objects.filter(solicitacao_origem=sol).first()
        historico = _historico_simulacao_list(sol, data_fmt=fmt)
        meta = {
            'nome_cliente': sol.cliente_dados_pessoais.nome_completo if sol.cliente_dados_pessoais_id else '',
            'proposta_codigo': prop.codigo if prop else '',
            'contrato_codigo': '',
            'solicitante': (sol.criado_por.get_full_name() or sol.criado_por.username) if sol.criado_por else '',
        }
    elif tipo == 'solicitacao_dig':
        try:
            sol = (
                _solicitacao_digitacao_queryset_schema_seguro()
                .select_related(
                    'proposta_dados__cliente_dados_pessoais',
                    'criado_por',
                )
                .get(pk=pk)
            )
        except SolicitacaoDigitacao.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
        pd = sol.proposta_dados
        historico = _historico_digitacao_list(sol, data_fmt=fmt)
        meta = {
            'nome_cliente': (
                pd.cliente_dados_pessoais.nome_completo if pd and pd.cliente_dados_pessoais_id else ''
            ),
            'proposta_codigo': pd.codigo if pd else '',
            'contrato_codigo': '',
            'solicitante': (sol.criado_por.get_full_name() or sol.criado_por.username) if sol.criado_por else '',
        }
    elif tipo == 'contrato':
        try:
            ce = (
                ContratoExecucao.objects.select_related(
                    'cliente_dados_pessoais',
                    'proposta_dados',
                    'solicitacao_digitacao__criado_por',
                )
                .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
                .get(pk=pk, status=True)
            )
        except ContratoExecucao.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
        historico = _historico_contrato_list(ce, data_fmt=fmt)
        sol_criado = ''
        if ce.solicitacao_digitacao_id and ce.solicitacao_digitacao.criado_por:
            u = ce.solicitacao_digitacao.criado_por
            sol_criado = u.get_full_name() or u.username
        meta = {
            'nome_cliente': (
                ce.cliente_dados_pessoais.nome_completo if ce.cliente_dados_pessoais_id else ''
            ),
            'proposta_codigo': ce.proposta_dados.codigo if ce.proposta_dados_id else '',
            'contrato_codigo': ce.codigo or '',
            'solicitante': sol_criado,
        }
    else:
        return JsonResponse({'ok': False, 'erro': 'tipo inválido.'}, status=400)

    return JsonResponse({'ok': True, 'tipo': tipo, 'historico': historico, 'meta': meta})


@login_required
@require_GET
@controle_acess_multiplos(COD_SS_ESTEIRA, 'SCT147', COD_SIAPE_CONSULTA_CLIENTE, COD_CX_NOVO_CONTRATO)
def api_get_transicoes_disponiveis(request):
    """Retorna as transições disponíveis para avançar o registro (nunca retrocedem)."""
    tipo = request.GET.get('tipo')
    pk = request.GET.get('id')
    if not tipo or not pk:
        return JsonResponse({'ok': False, 'erro': 'tipo e id obrigatórios.'}, status=400)
    try:
        pk = int(pk)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'erro': 'id inválido.'}, status=400)

    if tipo == 'simulacao':
        try:
            sol_sim = SolicitacaoPropostaCliente.objects.get(pk=pk)
        except (ValueError, SolicitacaoPropostaCliente.DoesNotExist):
            return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
        return JsonResponse({
            'ok': True,
            'tipo': tipo,
            'transicoes': transicoes_disponiveis_simulacao(sol_sim.estado),
        })

    if tipo == 'solicitacao_dig':
        try:
            sol = (
                _solicitacao_digitacao_queryset_schema_seguro()
                .select_related('proposta_dados')
                .get(pk=pk)
            )
        except SolicitacaoDigitacao.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Não encontrado.'}, status=404)
        return JsonResponse({
            'ok': True,
            'tipo': tipo,
            'solicitacao_digitacao_id': sol.id,
            'transicoes': _transicoes_disponiveis_solicitacao_digitacao(sol),
        })

    if tipo == 'contrato':
        try:
            ce = ContratoExecucao.objects.select_related(
                'dados_operacionais', 'dados_operacionais__tabela_cms'
            ).get(pk=pk, status=True)
        except ContratoExecucao.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)

        modo_livre = contrato_permite_evolucao_livre(ce)
        if modo_livre:
            trans = transicoes_catalogo_livre_contrato()
        else:
            trans = transicoes_disponiveis_contrato_execucao(ce)
            trans = _filtrar_transicoes_por_permissao(request.user, trans, ce=ce)
        out = {
            'ok': True,
            'tipo': tipo,
            'transicoes': trans,
            'modo_livre': modo_livre,
        }
        ptc = _montar_pago_tc_modal_defaults(ce)
        if ptc:
            out['pago_tc_modal'] = ptc
        try:
            from apps.contratos_v2.services.port_refin import montar_defaults_refin_port

            rpd = montar_defaults_refin_port(ce)
            if rpd:
                out['refin_port_defaults'] = rpd
        except Exception:
            pass
        if ce.sub_status_operacional == SubStatusOperacional.PG_AGUARDANDO_CMS:
            pcm = _montar_pago_cms_modal_defaults(ce)
            if pcm:
                out['pago_cms_modal'] = pcm
        return JsonResponse(out)

    return JsonResponse({'ok': False, 'erro': 'tipo inválido.'}, status=400)


@login_required
@require_POST
@controle_acess_multiplos(COD_SS_ESTEIRA, 'SCT147', 'SCT16', 'SCT201', COD_CX_NOVO_CONTRATO)
def api_post_evoluir(request):
    """Aplica a transição selecionada no modal Evoluir."""
    data = _json_body(request)
    tipo = data.get('tipo')
    pk = data.get('id')
    acao = data.get('acao')
    observacao = (data.get('observacao') or '').strip()

    if not tipo or pk is None or not acao:
        return JsonResponse({'ok': False, 'erro': 'tipo, id e acao são obrigatórios.'}, status=400)
    try:
        pk = int(pk)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'erro': 'id inválido.'}, status=400)

    # Simulação
    if tipo == 'simulacao':
        try:
            sol = SolicitacaoPropostaCliente.objects.select_related('carteira_clientes').get(pk=pk)
        except SolicitacaoPropostaCliente.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Solicitação não encontrada.'}, status=404)
        permitidas_sim = {t['acao'] for t in transicoes_disponiveis_simulacao(sol.estado)}
        if acao not in permitidas_sim:
            return JsonResponse({'ok': False, 'erro': 'Transição não permitida para o estado atual.'}, status=400)
        if acao == 'sim_propostas':
            return JsonResponse(
                {'ok': False, 'erro': 'Para registrar ou editar propostas, use o fluxo do modal (formulário dedicado).'},
                status=400,
            )
        if acao == 'sim_inelegivel':
            cart = sol.carteira_clientes
            with transaction.atomic():
                estado_anterior = sol.estado
                sol.estado = EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL
                sol.respondido_por = request.user
                sol.data_resposta = timezone.now()
                sol.save(update_fields=['estado', 'respondido_por', 'data_resposta'])
                HistoricoEventoSimulacao.objects.create(
                    solicitacao=sol,
                    estado_anterior=estado_anterior,
                    estado_novo=EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL,
                    usuario=request.user,
                    observacao=observacao or None,
                )
                cart.status_comercial = 'INELEGIVEL'
                cart.tag_proposta_container = 'INELEGIVEL'
                cart.save(update_fields=['status_comercial', 'tag_proposta_container'])
                _registrar_tabulacao(cart, request.user, 'INELEGIVEL')
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'erro': 'Ação inválida para simulação.'}, status=400)

    # Solicitação de digitação (pré-contrato: gerar, pendência vendedor, cancelar, reabrir)
    if tipo == 'solicitacao_dig':
        try:
            sol = (
                _solicitacao_digitacao_queryset_schema_seguro()
                .select_related('proposta_dados', 'carteira_clientes')
                .get(pk=pk)
            )
        except (ValueError, SolicitacaoDigitacao.DoesNotExist):
            return JsonResponse({'ok': False, 'erro': 'Registro não encontrado.'}, status=404)
        permitidas = {t['acao'] for t in _transicoes_disponiveis_solicitacao_digitacao(sol)}
        if acao not in permitidas:
            return JsonResponse({'ok': False, 'erro': 'Transição não permitida para o estado atual.'}, status=400)

        if acao in (
            'operacional_solicitacao_marcar_pendencia',
            'operacional_solicitacao_cancelar',
            'operacional_solicitacao_reabrir',
        ):
            if not user_has_access(request.user, COD_SS_ESTEIRA):
                return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)

        if acao in ('operacional_solicitacao_marcar_pendencia', 'operacional_solicitacao_cancelar'):
            if not observacao:
                return JsonResponse({'ok': False, 'erro': 'Observação obrigatória para esta ação.'}, status=400)

        if acao == 'operacional_solicitacao_marcar_pendencia':
            cart = sol.carteira_clientes
            with transaction.atomic():
                ant = sol.estado
                sol.estado = EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO
                sol.save(update_fields=['estado'])
                HistoricoEventoDigitacao.objects.create(
                    solicitacao=sol,
                    estado_anterior=ant,
                    estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO,
                    usuario=request.user,
                    observacao=observacao,
                )
                if cart:
                    cart.tag_status_operacional = 'AGUARDANDO_PROPOSTA'
                    cart.save(update_fields=['tag_status_operacional'])
                    TagStatusOperacional.objects.create(
                        carteira_clientes=cart,
                        tag='AGUARDANDO_PROPOSTA',
                        criado_por=request.user,
                    )
                    _sincronizar_agregado_operacional(cart)
            return JsonResponse({'ok': True, 'solicitacao_digitacao_id': sol.id, 'estado': sol.estado})

        if acao == 'operacional_solicitacao_cancelar':
            cart = sol.carteira_clientes
            with transaction.atomic():
                ant = sol.estado
                sol.estado = EstadoSolicitacaoDigitacao.CANCELADA
                sol.save(update_fields=['estado'])
                HistoricoEventoDigitacao.objects.create(
                    solicitacao=sol,
                    estado_anterior=ant,
                    estado_novo=EstadoSolicitacaoDigitacao.CANCELADA,
                    usuario=request.user,
                    observacao=observacao,
                )
                if cart:
                    cart.status_comercial = 'INELEGIVEL'
                    cart.tag_proposta_container = 'INELEGIVEL'
                    cart.save(update_fields=['status_comercial', 'tag_proposta_container'])
                    _registrar_tabulacao(cart, request.user, 'INELEGIVEL', observacao=observacao)
                    _sincronizar_agregado_operacional(cart)
            return JsonResponse({'ok': True, 'solicitacao_digitacao_id': sol.id, 'estado': sol.estado})

        if acao == 'operacional_solicitacao_reabrir':
            cart = sol.carteira_clientes
            with transaction.atomic():
                ant = sol.estado
                sol.estado = EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL
                sol.save(update_fields=['estado'])
                HistoricoEventoDigitacao.objects.create(
                    solicitacao=sol,
                    estado_anterior=ant,
                    estado_novo=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
                    usuario=request.user,
                    observacao=observacao or None,
                )
                if cart:
                    cart.tag_status_operacional = 'AGUARDANDO_DIGITACAO'
                    cart.save(update_fields=['tag_status_operacional'])
                    TagStatusOperacional.objects.create(
                        carteira_clientes=cart,
                        tag='AGUARDANDO_DIGITACAO',
                        criado_por=request.user,
                    )
                    _sincronizar_agregado_operacional(cart)
            return JsonResponse({'ok': True, 'solicitacao_digitacao_id': sol.id, 'estado': sol.estado})

        # gerar_contrato
        tid = data.get('tabela_cms_id')
        cc, erro_cc = _validar_contrato_codigo(data)
        if erro_cc:
            return JsonResponse({'ok': False, 'erro': erro_cc}, status=400)
        if not _solicitacao_digitacao_permite_gerar_contrato(sol.estado):
            return JsonResponse(
                {
                    'ok': False,
                    'erro': (
                        'Esta solicitação não permite gerar contrato (cancelada, pendente de correção '
                        'ou já gerada). Recarregue a esteira.'
                    ),
                },
                status=400,
            )
        # Se o operacional não escolher manualmente, usa a tabela já informada pelo vendedor.
        if not tid and sol.proposta_dados and sol.proposta_dados.tabela_cms_id:
            tid = sol.proposta_dados.tabela_cms_id
        if not tid:
            return JsonResponse(
                {'ok': False, 'erro': 'Selecione uma tabela CMS para gerar contrato.'},
                status=400,
            )
        try:
            tab = TabelaCms.objects.select_related('banco', 'convenio', 'produto').get(pk=int(tid))
        except (ValueError, TabelaCms.DoesNotExist):
            return JsonResponse({'ok': False, 'erro': 'Tabela CMS inválida.'}, status=404)
        if sol.estado == EstadoSolicitacaoDigitacao.CONTRATO_GERADO:
            ce = ContratoExecucao.objects.filter(solicitacao_digitacao=sol).first()
            if ce:
                return JsonResponse({'ok': True, 'contrato_id': ce.id, 'codigo': ce.codigo, 'ja_existia': True})
        pd = sol.proposta_dados
        _persistir_numero_contrato_banco_pre(sol, cc)
        from apps.contratos_v2.services.repasse_carteira import kwargs_snapshot_repasse_contrato

        cart_snap = sol.carteira_clientes if sol.carteira_clientes_id else None
        snap_kw = kwargs_snapshot_repasse_contrato(cart_snap)
        with transaction.atomic():
            estado_anterior_dig = sol.estado
            ce = ContratoExecucao.objects.create(
                codigo=cc,
                proposta_dados=pd,
                cliente_dados_pessoais=pd.cliente_dados_pessoais,
                solicitacao_digitacao=sol,
                fase=FaseContratoExecucao.DIGITACAO_AGUARDANDO,
                etapa_operacional=EtapaOperacional.DIGITACAO,
                sub_status_operacional=SubStatusOperacional.DIG_AGUARDANDO,
                **snap_kw,
            )
            ContratoDadosOperacionais.objects.create(
                contrato_execucao=ce,
                banco=tab.banco,
                convenio=tab.convenio,
                produto=tab.produto,
                tabela_cms=tab,
                valor_parcela=pd.valor_parcela,
                prazo=pd.prazo,
                valor_af=pd.valor_af,
                valor_tc=pd.valor_tc,
                valor_liberado=pd.valor_liberado,
            )
            sol.estado = EstadoSolicitacaoDigitacao.CONTRATO_GERADO
            sol.save(update_fields=['estado'])
            HistoricoEventoDigitacao.objects.create(
                solicitacao=sol,
                estado_anterior=estado_anterior_dig,
                estado_novo=EstadoSolicitacaoDigitacao.CONTRATO_GERADO,
                usuario=request.user,
                observacao=observacao or None,
            )
        return JsonResponse({'ok': True, 'contrato_id': ce.id, 'codigo': ce.codigo})

    # Contrato
    if tipo == 'contrato':
        try:
            ce = ContratoExecucao.objects.select_related(
                'dados_operacionais',
                'dados_operacionais__tabela_cms',
                'dados_operacionais__produto',
                'proposta_dados__produto',
            ).get(pk=pk, status=True)
        except ContratoExecucao.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)

        if not _evoluir_contrato_acao_permitida(ce, acao, data):
            return JsonResponse({'ok': False, 'erro': 'Transição não permitida para o estado atual.'}, status=400)

        if acao == 'operacional_definir_status':
            if not contrato_permite_evolucao_livre(ce):
                return JsonResponse({'ok': False, 'erro': 'Modo livre indisponível para este contrato.'}, status=400)
            if not user_has_access(request.user, COD_SS_ESTEIRA):
                return JsonResponse({'ok': False, 'erro': 'Sem permissão operacional.'}, status=403)
            etapa_dest = (data.get('etapa') or '').strip()
            sub_dest = (data.get('sub') or data.get('sub_status') or '').strip()
            if not etapa_dest or not sub_dest:
                return JsonResponse({'ok': False, 'erro': 'Informe etapa e status de destino.'}, status=400)
            if etapa_dest == EtapaOperacional.PAGAMENTO:
                if not par_etapa_sub_valido(etapa_dest, sub_dest):
                    return JsonResponse({
                        'ok': False,
                        'erro': 'Status de Pagamento inválido para a etapa selecionada.',
                    }, status=400)
                if contrato_exige_video_conscientizacao_para_pagamento(ce) and not ce.flag_video_enviado:
                    return JsonResponse({
                        'ok': False,
                        'erro': (
                            'Envio do vídeo de conscientização obrigatório antes de ir para Pagamento.'
                        ),
                    }, status=400)
            if sub_dest == SubStatusOperacional.FORM_LINK_DISPONIVEL:
                link = (data.get('link_formalizacao') or '').strip()
                if not link:
                    return JsonResponse({'ok': False, 'erro': 'link_formalizacao obrigatório.'}, status=400)
                ce.link_formalizacao = link
                ce.destaque_vendedor = True
                ce.save(update_fields=['link_formalizacao', 'destaque_vendedor', 'data_ultima_atualizacao'])
            if sub_dest == SubStatusOperacional.PG_PAGO_CLIENTE:
                extras_pago = _extras_operacional_pago_cliente(data)
                ok_pc, msg_pc = transicao_por_acao(
                    ce,
                    request.user,
                    PAPEL_OPERACIONAL,
                    'operacional_pago_cliente',
                    observacao=observacao,
                    extras=extras_pago,
                )
                if not ok_pc:
                    return JsonResponse({'ok': False, 'erro': msg_pc}, status=400)
                ce.refresh_from_db()
                resp_ctr = {
                    'id': ce.id,
                    'codigo': ce.codigo,
                    'etapa_operacional': ce.etapa_operacional,
                    'sub_status_operacional': ce.sub_status_operacional,
                }
                try:
                    from apps.contratos_v2.services.port_refin import vinculo_port_refin_dict

                    filho = (
                        ContratoExecucao.objects.filter(
                            contrato_vinculo_port_id=ce.id, status=True
                        )
                        .order_by('-id')
                        .first()
                    )
                    if filho:
                        resp_ctr['contrato_refin_id'] = filho.id
                        resp_ctr['contrato_refin_codigo'] = filho.codigo or ''
                    resp_ctr['vinculo_port_refin'] = vinculo_port_refin_dict(ce)
                except Exception:
                    pass
                return JsonResponse({'ok': True, 'contrato': resp_ctr})
            ok_dir, msg_dir = aplicar_etapa_sub(
                ce, etapa_dest, sub_dest, request.user, observacao=observacao
            )
            if not ok_dir:
                return JsonResponse({'ok': False, 'erro': msg_dir}, status=400)
            ce.refresh_from_db()
            return JsonResponse({
                'ok': True,
                'contrato': {
                    'id': ce.id,
                    'codigo': ce.codigo,
                    'etapa_operacional': ce.etapa_operacional,
                    'sub_status_operacional': ce.sub_status_operacional,
                },
            })

        # Ação especial: informar link + transição DIG_LINK_DISPONIBILIZADO
        if acao == 'operacional_link_disponibilizado':
            link = (data.get('link_formalizacao') or '').strip()
            if not link:
                return JsonResponse({'ok': False, 'erro': 'link_formalizacao obrigatório.'}, status=400)
            ce.link_formalizacao = link
            ce.destaque_vendedor = True
            ce.save(update_fields=['link_formalizacao', 'destaque_vendedor', 'data_ultima_atualizacao'])

        codigo_perm, papel = _codigo_acesso_para_acao(acao)
        if not codigo_perm or not papel:
            return JsonResponse({'ok': False, 'erro': 'Ação inválida.'}, status=400)
        if not _usuario_pode_executar_acao_transicao(request.user, acao, ce):
            return JsonResponse({'ok': False, 'erro': 'Sem permissão para esta ação.'}, status=403)

        extras = None
        if acao in ('supervisor_pago_tc', 'operacional_pago_tc'):
            rm_dict, err_rm = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
            if err_rm:
                return JsonResponse({'ok': False, 'erro': err_rm}, status=400)
            if rm_dict is not None:
                extras = {'registermoney': rm_dict}
                novo_tc_ev = rm_dict.get('valor_est')
                if novo_tc_ev is not None and novo_tc_ev > 0:
                    soma_ev = _soma_comprovantes_tc_ativos(ce)
                    atual_ev = valor_tc_efetivo_para_fluxo(ce)
                    if atual_ev.quantize(Decimal('0.01')) != novo_tc_ev.quantize(Decimal('0.01')):
                        ok_pe, err_pe = persistir_tc_modal_em_contrato_e_rm(ce, novo_tc_ev, soma_ev)
                        if not ok_pe:
                            return JsonResponse({'ok': False, 'erro': err_pe}, status=400)
                        ce.refresh_from_db()
                        if ContratoDadosOperacionais.objects.filter(contrato_execucao_id=ce.pk).exists():
                            ce.dados_operacionais.refresh_from_db()
                        if ce.proposta_dados_id:
                            ce.proposta_dados.refresh_from_db()
                elif novo_tc_ev is not None and novo_tc_ev <= 0 and valor_tc_efetivo_para_fluxo(ce) > 0:
                    ok_z, err_z = zerar_tc_modal_em_contrato(ce)
                    if not ok_z:
                        return JsonResponse({'ok': False, 'erro': err_z}, status=400)
                    ce.refresh_from_db()
                    if ContratoDadosOperacionais.objects.filter(contrato_execucao_id=ce.pk).exists():
                        ce.dados_operacionais.refresh_from_db()
                    if ce.proposta_dados_id:
                        ce.proposta_dados.refresh_from_db()
        elif acao in ('supervisor_checado', 'vendedor_checado_formalizacao'):
            extras = {
                'nivel_risco_checagem': (data.get('nivel_risco') or data.get('nivel_risco_checagem') or '').strip(),
            }
        elif acao == 'operacional_pago_cliente':
            extras = _extras_operacional_pago_cliente(data)

        if acao == 'financeiro_pago_cms':
            err_cms = _aplicar_taxas_snapshot_financeiro_pago_cms(ce, request.user, data)
            if err_cms:
                return JsonResponse({'ok': False, 'erro': err_cms}, status=400)
            ce = ContratoExecucao.objects.select_related(
                'dados_operacionais', 'dados_operacionais__tabela_cms'
            ).get(pk=ce.pk)

        ok, msg = transicao_por_acao(ce, request.user, papel, acao, observacao=observacao, extras=extras)
        if not ok:
            return JsonResponse({'ok': False, 'erro': msg}, status=400)

        ce.refresh_from_db()
        try:
            sol2 = ce.solicitacao_digitacao
            cart = sol2.carteira_clientes if sol2 and sol2.carteira_clientes_id else None
            if cart and cart.status == 'ATIVO':
                deve_finalizar = (
                    ce.etapa_operacional == EtapaOperacional.CANCELADO
                    or ce.tag_financeira == TagFinanceiraContrato.PAGO_TC
                )
                if deve_finalizar:
                    TabulacaoVendedor.objects.create(
                        carteira_clientes=cart,
                        user=request.user,
                        tipo='FINALIZADA',
                        observacao='Finalizado automaticamente via contratos.',
                    )
                    cart.status_comercial = 'FINALIZADA'
                    cart.save(update_fields=['status_comercial'])
                    _sincronizar_agregado_operacional(cart)
        except Exception:
            pass

        resp_ctr = {
            'id': ce.id,
            'codigo': ce.codigo,
            'etapa_operacional': ce.etapa_operacional,
            'sub_status_operacional': ce.sub_status_operacional,
            'flag_video_enviado': bool(ce.flag_video_enviado),
            'exige_video_conscientizacao': bool(contrato_exige_video_conscientizacao_para_pagamento(ce)),
        }
        if acao == 'operacional_pago_cliente' and (
            data.get('refin_port') or data.get('valor_saldo') is not None
        ):
            try:
                from apps.contratos_v2.services.port_refin import vinculo_port_refin_dict

                filho = (
                    ContratoExecucao.objects.filter(contrato_vinculo_port_id=ce.id, status=True)
                    .order_by('-id')
                    .first()
                )
                if filho:
                    resp_ctr['contrato_refin_id'] = filho.id
                    resp_ctr['contrato_refin_codigo'] = filho.codigo or ''
                resp_ctr['vinculo_port_refin'] = vinculo_port_refin_dict(ce)
            except Exception:
                pass
        return JsonResponse({'ok': True, 'contrato': resp_ctr})

    return JsonResponse({'ok': False, 'erro': 'tipo inválido.'}, status=400)


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_get_refin_port_defaults(request, contrato_id):
    """Defaults do modal REFIN (Port + Refin) para contrato em PG_AGUARDANDO_CLIENTE."""
    try:
        ce = ContratoExecucao.objects.select_related(
            'dados_operacionais__banco',
            'dados_operacionais__convenio',
            'dados_operacionais__produto',
            'proposta_dados__banco',
            'proposta_dados__convenio',
            'proposta_dados__produto',
        ).get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    from apps.contratos_v2.services.port_refin import montar_defaults_refin_port

    defaults = montar_defaults_refin_port(ce)
    if not defaults:
        return JsonResponse({'ok': False, 'erro': 'Contrato não exige REFIN neste momento.'}, status=400)
    return JsonResponse({'ok': True, **defaults})


# ---------------------------------------------------------------------------
# Ranking supervisor (pré-lança RegisterMoney sem evoluir contrato)
# ---------------------------------------------------------------------------

def _fmt_dec_br(v):
    if v is None:
        return ''
    try:
        return f'{Decimal(v):.2f}'.replace('.', ',')
    except Exception:
        return str(v)


@login_required
@require_GET
@controle_acess('SCT201')
def api_get_ranking_supervisor_context(request, contrato_id):
    """Dados para modal Enviar Ranking (supervisor CRM SIAPE)."""
    try:
        ce = ContratoExecucao.objects.select_related(
            'cliente_dados_pessoais',
            'dados_operacionais',
            'dados_operacionais__tabela_cms',
            'proposta_dados',
            'solicitacao_digitacao__criado_por',
            'solicitacao_digitacao__carteira_clientes__user_responsavel',
        ).get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)

    d = getattr(ce, 'dados_operacionais', None)
    pd = ce.proposta_dados
    af = d.valor_af if d else (pd.valor_af if pd else None)
    tc = d.valor_tc if d else (pd.valor_tc if pd else None)
    liberado = d.valor_liberado if d else (pd.valor_liberado if pd else None)
    if liberado is None and af is not None and tc is not None:
        try:
            liberado = Decimal(str(af)) - Decimal(str(tc))
        except Exception:
            liberado = None

    tr = _taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido') if d else None
    tp = _taxa_snapshot_ou_tabela(d, 'taxa_repasse_snapshot', 'taxa_repasse') if d else None

    solicitante = ''
    if ce.solicitacao_digitacao_id:
        cart = ce.solicitacao_digitacao.carteira_clientes
        ur = cart.user_responsavel if cart else None
        if ur:
            solicitante = (ur.get_full_name() or ur.username or '').strip()
        if not solicitante and ce.solicitacao_digitacao.criado_por:
            u = ce.solicitacao_digitacao.criado_por
            solicitante = (u.get_full_name() or u.username or '').strip()

    def cms_val(taxa):
        if taxa is None or not af:
            return None
        try:
            return (Decimal(str(af)) * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01'))
        except Exception:
            return None

    v_rec = cms_val(tr)
    v_rep = cms_val(tp)
    ja_rm = RegisterMoney.objects.filter(contrato_execucao=ce, status=True).exists()

    ptc = _montar_pago_tc_modal_defaults(ce) or {}

    return JsonResponse({
        'ok': True,
        'contrato_id': ce.id,
        'cliente_nome': getattr(ce.cliente_dados_pessoais, 'nome_completo', '') or '',
        'cliente_cpf': getattr(ce.cliente_dados_pessoais, 'cpf', '') or '',
        'solicitante': solicitante,
        'valor_af': _fmt_dec_br(af),
        'valor_tc': _fmt_dec_br(tc),
        'valor_liberado': _fmt_dec_br(liberado),
        'taxa_recebido_pct': str(tr) if tr is not None else '',
        'taxa_repasse_pct': str(tp) if tp is not None else '',
        'valor_cms_recebido': _fmt_dec_br(v_rec),
        'valor_cms_repassado': _fmt_dec_br(v_rep),
        'registermoney_ja_existe': ja_rm,
        'classificacoes': ptc.get('classificadores', ptc.get('classificacoes', [])),
        'classificadores': ptc.get('classificadores', ptc.get('classificacoes', [])),
        'lojas_elegiveis': ptc.get('lojas_elegiveis', []),
    })


@login_required
@require_POST
@controle_acess('SCT201')
def api_post_ranking_supervisor(request, contrato_id):
    """Cria RegisterMoney antecipado pelo supervisor; não altera proposta/contrato."""
    data = _json_body(request)
    try:
        ce = ContratoExecucao.objects.select_related(
            'dados_operacionais',
            'dados_operacionais__tabela_cms',
            'cliente_dados_pessoais',
            'solicitacao_digitacao__carteira_clientes',
        ).get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)

    rm_dict, err_rm = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
    if err_rm:
        return JsonResponse({'ok': False, 'erro': err_rm}, status=400)

    # Recalcula CMS a partir dos percentuais enviados (supervisor edita só %)
    try:
        d = ce.dados_operacionais
    except Exception:
        d = None
    if d:
        af_base = d.valor_af or Decimal('0')
        for key_snap, key_body, key_rm in (
            ('taxa_recebido_snapshot', 'taxa_recebido_pct', 'valor_cms_recebido'),
            ('taxa_repasse_snapshot', 'taxa_repasse_pct', 'valor_cms_repassado'),
        ):
            pct = _dec_flex(data.get(key_body))
            if pct is not None:
                setattr(d, key_snap, pct)
                if rm_dict is not None and af_base > 0:
                    rm_dict[key_rm] = (af_base * pct / Decimal('100')).quantize(Decimal('0.01'))
        d.save(update_fields=['taxa_recebido_snapshot', 'taxa_repasse_snapshot'])

    if rm_dict is None:
        rm_dict = {'valor_est': Decimal('0'), 'af': d.valor_af if d else None}

    ok, msg = criar_registermoney_ranking_supervisor(ce, request.user, rm_dict)
    if not ok:
        return JsonResponse({'ok': False, 'erro': msg}, status=409 if 'Já existe' in msg else 400)
    return JsonResponse({'ok': True, 'message': 'Ranking registrado com sucesso.'})


# ---------------------------------------------------------------------------
# Snapshot CMS no contrato (edição manual + auditoria)
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['PATCH'])
@controle_acess(COD_SS_ESTEIRA)
def api_patch_contrato_dados_cms_snapshot(request, contrato_id):
    """Atualiza título/taxas snapshot em dados operacionais; preenche data_att_cms e user_att_cms."""
    data = _json_body(request)
    try:
        ce = ContratoExecucao.objects.get(pk=int(contrato_id), status=True)
    except (ValueError, ContratoExecucao.DoesNotExist):
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    d = ContratoDadosOperacionais.objects.filter(contrato_execucao=ce).first()
    if not d:
        return JsonResponse({'ok': False, 'erro': 'Sem dados operacionais.'}, status=400)

    if 'tabela_cms_titulo_snapshot' in data:
        v = data.get('tabela_cms_titulo_snapshot')
        d.tabela_cms_titulo_snapshot = (str(v) if v is not None else '')[:200]

    for fld in ('taxa_recebido_snapshot', 'taxa_repasse_snapshot', 'taxa_plastico_snapshot'):
        if fld not in data:
            continue
        val = data.get(fld)
        if val in (None, ''):
            setattr(d, fld, None)
        else:
            setattr(d, fld, _dec_flex(val))

    d.data_att_cms = timezone.now()
    d.user_att_cms = request.user
    d.save()
    _recalcular_cms_register_money_contrato(ce)
    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# Exclusão definitiva (apenas superusuários)
# ---------------------------------------------------------------------------

@login_required
@controle_acess(COD_SS_ESTEIRA)
@require_http_methods(['DELETE'])
def api_delete_solicitacao(request, pk):
    """Exclui SolicitacaoPropostaCliente definitivamente — apenas superusuários."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'erro': 'Permissão negada. Apenas superusuários podem excluir definitivamente.'}, status=403)
    sol = get_object_or_404(SolicitacaoPropostaCliente, pk=pk)
    try:
        sol.delete()
    except ProtectedError:
        return JsonResponse({'ok': False, 'erro': 'Solicitação possui vínculos e não pode ser excluída.'}, status=400)
    return JsonResponse({'ok': True})


@login_required
@controle_acess(COD_SS_ESTEIRA)
@require_http_methods(['DELETE'])
def api_delete_contrato(request, pk):
    """Exclui ContratoExecucao definitivamente — apenas superusuários."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'erro': 'Permissão negada. Apenas superusuários podem excluir definitivamente.'}, status=403)
    ce = get_object_or_404(ContratoExecucao, pk=pk)
    try:
        ce.delete()
    except ProtectedError:
        return JsonResponse({'ok': False, 'erro': 'Contrato possui vínculos e não pode ser excluído.'}, status=400)
    return JsonResponse({'ok': True})
