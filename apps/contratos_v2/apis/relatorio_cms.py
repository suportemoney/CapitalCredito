# -*- coding: utf-8 -*-
"""APIs do Relatório CMS (Financeiro — Jaci).

Lista contratos na esteira de pagamento (TC parcial/total, legado e fases CMS),
permite marcar "Pago CMS Empresa" com snapshots de taxas, AF base e classificador.
"""
import json
import logging
import os
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.contratos_v2.cms_financeiro_base import base_af_para_cms, classificador_banco_efetivo
from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
from apps.contratos_v2.fluxo_transicoes import aplicar_etapa_sub, _registrar_historico
from apps.contratos_v2.models import (
    Banco,
    ComprovanteTC,
    Convenio,
    ContratoExecucao,
    ContratoDadosOperacionais,
    Produto,
)
from apps.rh.admin.models import Loja
from apps.vendas.siape.models import RegisterMoney

logger = logging.getLogger(__name__)


def _loja_nome_contrato_relatorio(ce):
    """Loja do RegisterMoney ativo do contrato; fallback primeira loja INSS do consultor."""
    for rm in ce.registros_financeiros_tc.all():
        if rm.loja_id and rm.loja:
            return rm.loja.nome or ''
    try:
        sol = ce.solicitacao_digitacao
        cart = sol.carteira_clientes if sol and sol.carteira_clientes_id else None
        ur = cart.user_responsavel if cart else None
        if not ur and ce.proposta_dados and ce.proposta_dados.criado_por_id:
            ur = ce.proposta_dados.criado_por
        if ur and hasattr(ur, 'funcionario_profile'):
            loja = ur.funcionario_profile.lojas.filter(status=True).order_by('nome').first()
            if loja:
                return loja.nome or ''
    except Exception:
        pass
    return ''

# Permissão SS36 — OPERACIONAL | CONTRATOS | RELATÓRIO CMS
COD_ACESSO_RELATORIO_CMS = 'SS36'

# Sub-status exibidos no relatório: TC (parcial/total/legado) e trâmite CMS até empresa.
RELATORIO_CMS_SUB_STATUS = (
    SubStatusOperacional.PG_PAGO_TC,
    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
    SubStatusOperacional.PG_PAGO_TC_TOTAL,
    SubStatusOperacional.PG_AGUARDANDO_CMS,
    SubStatusOperacional.PG_PAGO_CMS,
    SubStatusOperacional.PG_PAGO_CMS_EMPRESA,
)

# Estados em que o financeiro pode solicitar "Pago CMS Empresa" (já quitado TC ou fluxo CMS).
_SUBS_PODE_MARCAR_CMS_EMPRESA = (
    SubStatusOperacional.PG_PAGO_TC,
    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
    SubStatusOperacional.PG_PAGO_TC_TOTAL,
    SubStatusOperacional.PG_AGUARDANDO_CMS,
    SubStatusOperacional.PG_PAGO_CMS,
)


def _json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _dec(v):
    if v is None or v == '':
        return None
    try:
        return Decimal(str(v).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _taxa_snapshot_ou_tabela(d, attr_snap, attr_tab):
    """Mesma lógica de fluxo: snapshot da digitação ou tabela CMS vinculada."""
    if not d:
        return None
    v = getattr(d, attr_snap, None)
    if v is not None:
        return v
    if d.tabela_cms_id:
        return getattr(d.tabela_cms, attr_tab, None)
    return None


def _json_ok(**extra):
    """Resposta unificada: `ok` e `success` espelhados para o frontend."""
    body = {'ok': True, 'success': True}
    body.update(extra)
    return JsonResponse(body)


def _json_erro(msg, status=400):
    return JsonResponse({'ok': False, 'success': False, 'erro': msg, 'error': msg}, status=status)


def _contrato_id_from_payload(data):
    return data.get('contrato_id') or data.get('contrato_execucao_id')


def _percentual_from_payload(data):
    if 'percentual' in data:
        v = _dec(data.get('percentual'))
        if v is not None:
            return v
    return _dec(data.get('percentual_af'))


def _label_status_cms_financeiro(sub):
    """Rótulo auxiliar para tabulação financeira (critério 5)."""
    if sub == SubStatusOperacional.PG_PAGO_CMS_EMPRESA:
        return 'Pago CMS Empresa'
    if sub in (SubStatusOperacional.PG_AGUARDANDO_CMS, SubStatusOperacional.PG_PAGO_CMS):
        return 'Pendente CMS'
    return ''


@login_required
@controle_acess(COD_ACESSO_RELATORIO_CMS)
@require_GET
def api_get_relatorio_cms_lista(request):
    """Lista contratos (esteira PAGAMENTO) com TC/CMS. Filtros: banco_id, convenio_id, produto_id,
    status (sub_status), status_cms_financeiro (pendente|pago_empresa), data_ini, data_fim,
    busca (CPF/nome/código), funcionario_id (user responsável ou criador da proposta),
    classificador (M1/M2/M3).
    """
    qs = (
        ContratoExecucao.objects.filter(
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional__in=RELATORIO_CMS_SUB_STATUS,
        )
        .select_related(
            'cliente_dados_pessoais',
            'dados_operacionais',
            'dados_operacionais__banco',
            'dados_operacionais__convenio',
            'dados_operacionais__produto',
            'dados_operacionais__tabela_cms',
            'proposta_dados',
            'proposta_dados__banco',
            'proposta_dados__convenio',
            'proposta_dados__produto',
            'proposta_dados__tabela_cms',
            'proposta_dados__criado_por',
            'solicitacao_digitacao',
            'solicitacao_digitacao__carteira_clientes',
            'solicitacao_digitacao__carteira_clientes__user_responsavel',
        )
        .defer(
            'solicitacao_digitacao__numero_contrato_banco_pre',
            'solicitacao_digitacao__link_formalizacao_pre',
        )
        .prefetch_related(
            Prefetch(
                'comprovantes_tc',
                queryset=ComprovanteTC.objects.filter(status=True).select_related('criado_por'),
            ),
            Prefetch(
                'registros_financeiros_tc',
                queryset=RegisterMoney.objects.filter(status=True).select_related('loja'),
            ),
        )
        .order_by('-data_ultima_atualizacao')
    )

    banco_id = request.GET.get('banco_id')
    convenio_id = request.GET.get('convenio_id')
    produto_id = request.GET.get('produto_id')
    status_sub = request.GET.get('status')
    status_cms_fin = (request.GET.get('status_cms_financeiro') or '').strip().lower()
    data_ini = request.GET.get('data_ini')
    data_fim = request.GET.get('data_fim')
    busca = (request.GET.get('busca') or '').strip()
    funcionario_id = request.GET.get('funcionario_id')
    classificador = (request.GET.get('classificador') or '').strip().upper()
    loja_id = request.GET.get('loja_id')

    if banco_id:
        qs = qs.filter(
            Q(dados_operacionais__banco_id=banco_id)
            | Q(proposta_dados__banco_id=banco_id)
        )
    if convenio_id:
        qs = qs.filter(
            Q(dados_operacionais__convenio_id=convenio_id)
            | Q(proposta_dados__convenio_id=convenio_id)
        )
    if produto_id:
        qs = qs.filter(
            Q(dados_operacionais__produto_id=produto_id)
            | Q(proposta_dados__produto_id=produto_id)
        )
    if status_sub:
        qs = qs.filter(sub_status_operacional=status_sub)
    if status_cms_fin == 'pendente':
        qs = qs.filter(
            sub_status_operacional__in=(
                SubStatusOperacional.PG_AGUARDANDO_CMS,
                SubStatusOperacional.PG_PAGO_CMS,
            )
        )
    elif status_cms_fin == 'pago_empresa':
        qs = qs.filter(sub_status_operacional=SubStatusOperacional.PG_PAGO_CMS_EMPRESA)
    if data_ini:
        qs = qs.filter(data_ultima_atualizacao__date__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_ultima_atualizacao__date__lte=data_fim)
    if busca:
        qn = Q(cliente_dados_pessoais__nome_completo__icontains=busca)
        qc = Q(cliente_dados_pessoais__cpf__icontains=busca.replace('.', '').replace('-', ''))
        qcod = Q(codigo__icontains=busca) | Q(proposta_dados__codigo__icontains=busca)
        qs = qs.filter(qn | qc | qcod)
    if funcionario_id:
        qs = qs.filter(
            Q(solicitacao_digitacao__carteira_clientes__user_responsavel_id=funcionario_id)
            | Q(proposta_dados__criado_por_id=funcionario_id)
        )
    if classificador in ('M1', 'M2', 'M3'):
        qs = qs.filter(
            Q(dados_operacionais__tabela_cms__classificador_banco=classificador)
            | Q(dados_operacionais__classificador_banco_operacional=classificador)
        )
    if loja_id:
        try:
            qs = qs.filter(
                registros_financeiros_tc__loja_id=int(loja_id),
                registros_financeiros_tc__status=True,
            )
        except (ValueError, TypeError):
            pass

    qs = qs.distinct()

    itens = []
    try:
        for ce in qs[:500]:
            d = getattr(ce, 'dados_operacionais', None)
            pd = getattr(ce, 'proposta_dados', None)
            banco_t = (d.banco.titulo if d and d.banco_id else (pd.banco.titulo if pd and pd.banco_id else ''))
            conv_t = (d.convenio.titulo if d and d.convenio_id else (pd.convenio.titulo if pd and pd.convenio_id else ''))
            prod_t = (d.produto.titulo if d and d.produto_id else (pd.produto.titulo if pd and pd.produto_id else ''))
            af = d.valor_af if d else (pd.valor_af if pd else None)
            tc = d.valor_tc if d else (pd.valor_tc if pd else None)
            pct_manual = d.percentual_af_manual if d else None

            tabela_titulo = ''
            classif = ''
            if d and d.tabela_cms_id:
                tabela_titulo = (d.tabela_cms_titulo_snapshot or d.tabela_cms.titulo or '').strip()
                classif = classificador_banco_efetivo(d) or ''
            elif pd and pd.tabela_cms_id:
                tabela_titulo = (pd.tabela_cms.titulo or '').strip()
                classif = (pd.tabela_cms.classificador_banco or '').upper()

            consultor_nome = ''
            try:
                sol = ce.solicitacao_digitacao
                cart = sol.carteira_clientes if sol and sol.carteira_clientes_id else None
                ur = cart.user_responsavel if cart else None
                if ur:
                    consultor_nome = (ur.get_full_name() or ur.username or '').strip()
            except Exception:
                pass
            if not consultor_nome and pd and pd.criado_por_id:
                u = pd.criado_por
                consultor_nome = (u.get_full_name() or u.username or '').strip()

            comps = list(ce.comprovantes_tc.all())

            comprovantes_payload = []
            for c in comps:
                arq = c.arquivo
                nome_arquivo = os.path.basename(arq.name) if (arq and arq.name) else None
                comprovantes_payload.append({
                    'id': c.id,
                    'valor': str(c.valor),
                    'arquivo_url': c.arquivo.url if c.arquivo else None,
                    'nome_arquivo': nome_arquivo,
                    'criado_em': c.criado_em.isoformat() if c.criado_em else None,
                    'criado_por': c.criado_por.username if c.criado_por_id else '',
                })

            af_dec = Decimal(str(af)) if af is not None else Decimal('0')
            if d:
                base_af = base_af_para_cms(d)
            else:
                base_af = af_dec

            tr = _taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido') if d else None
            tp = _taxa_snapshot_ou_tabela(d, 'taxa_repasse_snapshot', 'taxa_repasse') if d else None
            tpl = _taxa_snapshot_ou_tabela(d, 'taxa_plastico_snapshot', 'taxa_plastico') if d else None

            def cms_val(taxa):
                if taxa is None or base_af <= 0:
                    return None
                try:
                    return (base_af * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01'))
                except Exception:
                    return None

            cms_rec = cms_val(tr)
            cms_rep = cms_val(tp)
            cms_pla = cms_val(tpl)

            # Pago TC e data: a partir dos RegisterMoney do contrato (valor_pago_acumulado + data_pago).
            soma_rm = Decimal('0')
            pago_tc_rm = Decimal('0')
            ultima_data_pago_tc = None
            ultima_data_rm = None
            for rm in ce.registros_financeiros_tc.all():
                if rm.valor_est:
                    soma_rm += Decimal(str(rm.valor_est))
                if rm.valor_pago_acumulado:
                    pago_tc_rm += Decimal(str(rm.valor_pago_acumulado))
                if rm.data_pago and (ultima_data_pago_tc is None or rm.data_pago > ultima_data_pago_tc):
                    ultima_data_pago_tc = rm.data_pago
                if rm.data and (ultima_data_rm is None or rm.data > ultima_data_rm):
                    ultima_data_rm = rm.data
            data_ref_pago_tc = ultima_data_pago_tc
            if data_ref_pago_tc is None and pago_tc_rm > 0 and ultima_data_rm is not None:
                # Legado / inconsistência: acumulado preenchido sem data_pago
                data_ref_pago_tc = ultima_data_rm

            sub = ce.sub_status_operacional
            pode_marcar = sub in _SUBS_PODE_MARCAR_CMS_EMPRESA

            numero_proposta = (ce.codigo or '') or (pd.codigo if pd else '') or ''

            itens.append({
                'contrato_id': ce.id,
                'contrato_execucao_id': ce.id,
                'numero_proposta': numero_proposta,
                'cliente_nome': getattr(ce.cliente_dados_pessoais, 'nome_completo', '') or '',
                'cliente_cpf': getattr(ce.cliente_dados_pessoais, 'cpf', '') or '',
                'consultor_nome': consultor_nome,
                'loja_nome': _loja_nome_contrato_relatorio(ce),
                'banco': banco_t,
                'convenio': conv_t,
                'produto': prod_t,
                'tabela_cms': tabela_titulo,
                'classificador_banco': classif,
                'valor_af': str(af) if af is not None else None,
                'valor_tc': str(tc) if tc is not None else None,
                'valor_pago_tc': str(pago_tc_rm),
                'soma_register_money': str(soma_rm),
                'percentual_af': str(pct_manual) if pct_manual is not None else None,
                'valor_af_base_cms': str(d.valor_af_base_cms) if d and d.valor_af_base_cms is not None else None,
                'base_af_cms': str(base_af) if base_af and base_af > 0 else None,
                'cms_recebido': str(cms_rec) if cms_rec is not None else None,
                'cms_repassado': str(cms_rep) if cms_rep is not None else None,
                'cms_plastico': str(cms_pla) if cms_pla is not None else None,
                'taxa_recebido_pct': str(tr) if tr is not None else None,
                'taxa_repasse_pct': str(tp) if tp is not None else None,
                'taxa_plastico_pct': str(tpl) if tpl is not None else None,
                'sub_status': sub,
                'sub_status_label': ce.get_sub_status_operacional_display(),
                'status_tc_pagamento': ce.get_sub_status_operacional_display()
                if sub
                in (
                    SubStatusOperacional.PG_PAGO_TC,
                    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
                    SubStatusOperacional.PG_PAGO_TC_TOTAL,
                )
                else '',
                'status_cms_financeiro': _label_status_cms_financeiro(sub),
                'data_pagamento_tc': data_ref_pago_tc.isoformat() if data_ref_pago_tc else None,
                'atualizado_em': ce.data_ultima_atualizacao.isoformat() if ce.data_ultima_atualizacao else None,
                'comprovantes_tc': comprovantes_payload,
                'pode_marcar_pago_cms_empresa': pode_marcar,
            })
    except DatabaseError as exc:
        # MySQL: OperationalError 1054 "Unknown column ..."; SQLite: "no such column"; PostgreSQL: "does not exist"
        err = str(exc).lower()
        if (
            'valor_af_base_cms' in err
            or 'classificador_banco_operacional' in err
            or 'unknown column' in err
            or 'no such column' in err
            or ('does not exist' in err and 'valor_af_base' in err)
            or ('does not exist' in err and 'classificador_banco_operacional' in err)
        ):
            return _json_erro(
                'Banco de dados sem as colunas novas do relatório CMS. Execute: python manage.py migrate contratos',
                status=503,
            )
        logger.exception('api_get_relatorio_cms_lista (DatabaseError)')
        return JsonResponse(
            {'ok': False, 'success': False, 'erro': str(exc), 'error': str(exc)},
            status=500,
        )
    except Exception as exc:
        logger.exception('api_get_relatorio_cms_lista')
        return JsonResponse(
            {
                'ok': False,
                'success': False,
                'erro': str(exc),
                'error': str(exc),
            },
            status=500,
        )

    return _json_ok(itens=itens, items=itens, total=len(itens))


_CLASSIF_BANCO = ('M1', 'M2', 'M3')


class _PagoCmsEmpresaTransicaoError(Exception):
    """Falha em aplicar_etapa_sub dentro do atomic — força rollback."""


@login_required
@controle_acess(COD_ACESSO_RELATORIO_CMS)
@require_POST
def api_post_marcar_pago_cms_empresa(request):
    """Persiste taxas/AF base/classificador, recalcula RegisterMoney e marca PG_PAGO_CMS_EMPRESA."""
    from apps.contratos_v2.apis.fluxo import _recalcular_cms_register_money_contrato

    data = _json(request)
    contrato_id = _contrato_id_from_payload(data)
    observacao = (data.get('observacao') or '').strip()
    if not contrato_id:
        return _json_erro('contrato_id obrigatório.')

    for key in ('taxa_recebido_snapshot', 'taxa_repasse_snapshot', 'taxa_plastico_snapshot'):
        if key not in data or data.get(key) in (None, ''):
            return _json_erro('Informe os três percentuais (recebido, repasse e plástico).')

    cls_raw = (data.get('classificador_banco_operacional') or data.get('classificador_banco') or '').strip().upper()
    if cls_raw not in _CLASSIF_BANCO:
        return _json_erro('Classificador banco inválido (informe M1, M2 ou M3).')

    raw_base = data.get('valor_af_base_cms')
    if raw_base not in (None, ''):
        dec_base = _dec(raw_base)
        if dec_base is None or dec_base <= 0:
            return _json_erro('AF base para CMS deve ser um valor positivo.')
    else:
        dec_base = None

    tr = _dec(data.get('taxa_recebido_snapshot'))
    tp = _dec(data.get('taxa_repasse_snapshot'))
    tpl = _dec(data.get('taxa_plastico_snapshot'))
    if tr is None or tp is None or tpl is None:
        return _json_erro('Percentuais inválidos.')

    ce_refresh = None
    try:
        with transaction.atomic():
            ce = (
                ContratoExecucao.objects.select_for_update()
                .select_related('dados_operacionais', 'dados_operacionais__tabela_cms')
                .filter(pk=int(contrato_id))
                .first()
            )
            if not ce:
                return _json_erro('Contrato não encontrado.', status=404)
            if ce.sub_status_operacional not in _SUBS_PODE_MARCAR_CMS_EMPRESA:
                return _json_erro('Sub-status atual não permite marcar Pago CMS Empresa.', status=409)
            try:
                d = ce.dados_operacionais
            except ContratoDadosOperacionais.DoesNotExist:
                return _json_erro('Sem dados operacionais no contrato.')

            d.taxa_recebido_snapshot = tr
            d.taxa_repasse_snapshot = tp
            d.taxa_plastico_snapshot = tpl
            d.classificador_banco_operacional = cls_raw
            d.valor_af_base_cms = dec_base
            d.data_att_cms = timezone.now()
            d.user_att_cms = request.user
            d.save(
                update_fields=[
                    'taxa_recebido_snapshot',
                    'taxa_repasse_snapshot',
                    'taxa_plastico_snapshot',
                    'classificador_banco_operacional',
                    'valor_af_base_cms',
                    'data_att_cms',
                    'user_att_cms',
                ]
            )

            ce_refresh = ContratoExecucao.objects.select_related(
                'dados_operacionais', 'dados_operacionais__tabela_cms'
            ).get(pk=ce.pk)
            _recalcular_cms_register_money_contrato(ce_refresh)

            ok, msg = aplicar_etapa_sub(
                ce_refresh,
                EtapaOperacional.PAGAMENTO,
                SubStatusOperacional.PG_PAGO_CMS_EMPRESA,
                request.user,
                observacao=observacao or 'Pago CMS Empresa (financeiro).',
                inner_atomic=False,
            )
            if not ok:
                raise _PagoCmsEmpresaTransicaoError(msg or 'Falha na transição.')
    except _PagoCmsEmpresaTransicaoError as ex:
        return _json_erro(str(ex), status=400)

    ce_refresh.refresh_from_db()
    return _json_ok(
        contrato_id=ce_refresh.id,
        contrato_execucao_id=ce_refresh.id,
        sub_status=ce_refresh.sub_status_operacional,
    )


@login_required
@controle_acess(COD_ACESSO_RELATORIO_CMS)
@require_POST
def api_post_ajustar_percentual_af(request):
    """Persiste percentual_af_manual em dados operacionais e auditoria na timeline."""
    data = _json(request)
    contrato_id = _contrato_id_from_payload(data)
    percentual = _percentual_from_payload(data)
    if not contrato_id or percentual is None:
        return _json_erro('contrato_id e percentual obrigatórios.')
    if percentual < 0 or percentual > 100:
        return _json_erro('Percentual fora do intervalo 0-100.')
    ce = get_object_or_404(ContratoExecucao, pk=int(contrato_id))
    try:
        d = ce.dados_operacionais
    except ContratoDadosOperacionais.DoesNotExist:
        return _json_erro('Sem dados operacionais no contrato.')
    anterior = d.percentual_af_manual
    d.percentual_af_manual = percentual
    d.save(update_fields=['percentual_af_manual'])
    obs = (
        f'Relatório CMS: ajuste % sobre AF. '
        f'Anterior={anterior if anterior is not None else "—"}; novo={percentual}%.'
    )
    _registrar_historico(
        ce, ce.etapa_operacional, ce.sub_status_operacional,
        ce.etapa_operacional, ce.sub_status_operacional,
        request.user, obs[:500],
    )
    return _json_ok(percentual=str(percentual), percentual_af=str(percentual))


@login_required
@controle_acess(COD_ACESSO_RELATORIO_CMS)
@require_GET
def api_get_relatorio_cms_meta(request):
    """Opções para filtros do relatório (catálogos + consultores presentes na fila CMS)."""
    from django.contrib.auth import get_user_model

    U = get_user_model()
    bancos = list(Banco.objects.filter(status=True).order_by('titulo').values('id', 'titulo'))
    convenios = list(Convenio.objects.filter(status=True).order_by('titulo').values('id', 'titulo'))
    produtos = list(Produto.objects.filter(status=True).order_by('titulo').values('id', 'titulo'))
    uids = set()
    for a, b in (
        ContratoExecucao.objects.filter(
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional__in=RELATORIO_CMS_SUB_STATUS,
        )
        .values_list(
            'solicitacao_digitacao__carteira_clientes__user_responsavel_id',
            'proposta_dados__criado_por_id',
        )
        .distinct()[:800]
    ):
        if a:
            uids.add(a)
        if b:
            uids.add(b)
    funcionarios = []
    for u in U.objects.filter(id__in=uids).order_by('first_name', 'last_name', 'username'):
        funcionarios.append({
            'id': u.id,
            'nome': (u.get_full_name() or u.username or str(u.id)).strip(),
        })
    classificadores = [
        {'id': '', 'titulo': 'Todos'},
        {'id': 'M1', 'titulo': 'M1 (100%)'},
        {'id': 'M2', 'titulo': 'M2 (50%)'},
        {'id': 'M3', 'titulo': 'M3 (0%)'},
    ]
    status_cms_opts = [
        {'id': '', 'titulo': 'Todos'},
        {'id': 'pendente', 'titulo': 'Pendente CMS'},
        {'id': 'pago_empresa', 'titulo': 'Pago CMS Empresa'},
    ]
    loja_ids = (
        RegisterMoney.objects.filter(
            contrato_execucao__etapa_operacional=EtapaOperacional.PAGAMENTO,
            contrato_execucao__sub_status_operacional__in=RELATORIO_CMS_SUB_STATUS,
            loja__isnull=False,
            status=True,
        )
        .values_list('loja_id', flat=True)
        .distinct()
    )
    lojas = list(
        Loja.objects.filter(id__in=loja_ids, status=True).order_by('nome').values('id', 'nome')
    )

    return _json_ok(
        bancos=bancos,
        convenios=convenios,
        produtos=produtos,
        classificadores=classificadores,
        funcionarios=funcionarios,
        lojas=lojas,
        status_cms_financeiro=status_cms_opts,
    )
