# -*- coding: utf-8 -*-
"""Transições validadas ContratoExecucao (nexos): etapa + sub-status, histórico, fase legada, RegisterMoney."""
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.contratos_v2.fluxo_constants import (
    EstadoSolicitacaoProposta,
    EtapaOperacional,
    FaseContratoExecucao,
    SubStatusOperacional,
    TagFinanceiraContrato,
)
from apps.contratos_v2.models import ComprovanteTC, ContratoExecucao, HistoricoTransicaoContrato
from apps.vendas.siape.models import CarteiraClientes, RegisterMoney

# Papéis para validação de API (strings estáveis)
PAPEL_OPERACIONAL = 'operacional'
PAPEL_SUPERVISOR = 'supervisor'
PAPEL_VENDEDOR = 'vendedor'
PAPEL_FINANCEIRO = 'financeiro'


def _usuario_e_responsavel_carteira_do_contrato(usuario, ce):
    """
    True se o contrato estiver vinculado à carteira do usuário como responsável.
    Mesma regra que a API (carteira + solicitação + cliente operacional) para evitar 403 liberado e 400 na transição.
    """
    try:
        from apps.contratos_v2.apis.carteira_contrato_permissoes import contrato_vinculado_carteiras_responsavel

        return contrato_vinculado_carteiras_responsavel(usuario, ce)
    except Exception:
        return False


def _produto_requer_cip_refin(ce):
    """
    Regra de negócio: CIP/REFIN só fazem sentido para produtos de portabilidade
    ou refinanciamento. Olhamos o TÍTULO do produto (snapshot de dados
    operacionais ou da proposta) e procuramos 'PORT' ou 'REFIN' (case-insensitive).
    """
    titulos = []
    try:
        d = getattr(ce, 'dados_operacionais', None)
        if d and getattr(d, 'produto', None):
            titulos.append(d.produto.titulo or '')
    except Exception:
        pass
    try:
        pd = getattr(ce, 'proposta_dados', None)
        if pd and getattr(pd, 'produto', None):
            titulos.append(pd.produto.titulo or '')
    except Exception:
        pass
    for t in titulos:
        u = (t or '').upper()
        if 'PORT' in u or 'REFIN' in u:
            return True
    return False


def titulo_produto_indica_limpa_nome(titulo):
    """True se o título do cadastro de produto for Limpa Nome (variantes com/sem espaço)."""
    if not titulo:
        return False
    u = ' '.join((titulo or '').strip().upper().split())
    return u in ('LIMPA NOME', 'LIMPANOME')


def _produto_eh_limpa_nome(ce):
    """Mesma origem de título que _produto_requer_cip_refin (dados operacionais ou proposta)."""
    titulos = []
    try:
        d = getattr(ce, 'dados_operacionais', None)
        if d and getattr(d, 'produto', None):
            titulos.append(d.produto.titulo or '')
    except Exception:
        pass
    try:
        pd = getattr(ce, 'proposta_dados', None)
        if pd and getattr(pd, 'produto', None):
            titulos.append(pd.produto.titulo or '')
    except Exception:
        pass
    return any(titulo_produto_indica_limpa_nome(t) for t in titulos)


def contrato_exige_video_conscientizacao_para_pagamento(ce):
    """
    Para Pago Cliente / Pago TC: exige flag_video_enviado salvo quando True.
    Produto Limpa Nome dispensa o vídeo de conscientização nessas transições.
    """
    return not _produto_eh_limpa_nome(ce)


def contrato_exibe_botao_enviar_video_vendedor(ce):
    """
    Exibe botão Enviar vídeo na loja INSS / consulta SIAPE: link já disponibilizado
    e vídeo ainda pendente, independente de tabulação ou etapa posterior.
    """
    if not ce:
        return False
    if getattr(ce, 'etapa_operacional', None) == EtapaOperacional.CANCELADO:
        return False
    if not contrato_exige_video_conscientizacao_para_pagamento(ce):
        return False
    if not (getattr(ce, 'link_formalizacao', None) or '').strip():
        return False
    if getattr(ce, 'flag_video_enviado', False):
        return False
    try:
        vc = getattr(ce, 'video_cliente', None)
        if vc and getattr(vc, 'name', None):
            return False
    except Exception:
        pass
    return True


_SUBS_POR_ETAPA = {
    EtapaOperacional.DIGITACAO: {
        SubStatusOperacional.DIG_AGUARDANDO,
        SubStatusOperacional.DIG_DIGITADO,
        # legado (migração/histórico): aceitos em consultas, não gerados no fluxo novo
        SubStatusOperacional.DIG_LINK_DISPONIBILIZADO,
        SubStatusOperacional.DIG_CHECADO,
        SubStatusOperacional.DIG_FORMALIZADO,
    },
    EtapaOperacional.FORMALIZACAO: {
        SubStatusOperacional.FORM_LINK_DISPONIVEL,
        SubStatusOperacional.FORM_CHECADO,
        SubStatusOperacional.FORM_FORMALIZADO,
    },
    EtapaOperacional.ANALISE: {SubStatusOperacional.ANL_AGUARDANDO, SubStatusOperacional.ANL_SUCESSO},
    EtapaOperacional.CIP: {SubStatusOperacional.CIP_AGUARDANDO, SubStatusOperacional.CIP_SUCESSO},
    EtapaOperacional.REFIN: {SubStatusOperacional.REFIN_AGUARDANDO, SubStatusOperacional.REFIN_SUCESSO},
    EtapaOperacional.ANUENCIA: {SubStatusOperacional.ANU_AGUARDANDO, SubStatusOperacional.ANU_AVERBADO},
    EtapaOperacional.PAGAMENTO: {
        SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
        SubStatusOperacional.PG_PAGO_CLIENTE,
        SubStatusOperacional.PG_AGUARDANDO_TC,
        SubStatusOperacional.PG_PAGO_TC,  # legado
        SubStatusOperacional.PG_PAGO_TC_PARCIAL,
        SubStatusOperacional.PG_PAGO_TC_TOTAL,
        SubStatusOperacional.PG_AGUARDANDO_CMS,
        SubStatusOperacional.PG_PAGO_CMS,
        SubStatusOperacional.PG_PAGO_CMS_EMPRESA,
    },
    EtapaOperacional.PENDENCIAS: {SubStatusOperacional.PEND_AGUARDANDO, SubStatusOperacional.PEND_CORRIGIDO},
    EtapaOperacional.CANCELADO: {
        SubStatusOperacional.CAN_ENCERRADO,
        SubStatusOperacional.CAN_CLIENTE,
        SubStatusOperacional.CAN_CORRETOR,
        SubStatusOperacional.CAN_BANCO,
        SubStatusOperacional.CAN_REEMBOLSO,
    },
}


def par_etapa_sub_valido(etapa, sub):
    return etapa in _SUBS_POR_ETAPA and sub in _SUBS_POR_ETAPA[etapa]


def sincronizar_fase_legada(ce):
    """Atualiza ce.fase a partir de etapa_operacional + sub_status_operacional."""
    e = ce.etapa_operacional
    s = ce.sub_status_operacional
    fase = FaseContratoExecucao.DIGITACAO_AGUARDANDO
    if e == EtapaOperacional.CANCELADO:
        fase = FaseContratoExecucao.CANCELADO
    elif e == EtapaOperacional.DIGITACAO:
        if s == SubStatusOperacional.DIG_AGUARDANDO:
            fase = FaseContratoExecucao.DIGITACAO_AGUARDANDO
        else:
            fase = FaseContratoExecucao.AGUARDANDO_FORMALIZACAO
    elif e == EtapaOperacional.FORMALIZACAO:
        # Nova etapa; compartilha a fase legada "aguardando formalização" até Análise.
        fase = FaseContratoExecucao.AGUARDANDO_FORMALIZACAO
    elif e == EtapaOperacional.ANALISE:
        fase = FaseContratoExecucao.EM_ANALISE
    elif e == EtapaOperacional.CIP or e == EtapaOperacional.REFIN:
        fase = FaseContratoExecucao.EM_ANALISE
    elif e == EtapaOperacional.ANUENCIA:
        fase = FaseContratoExecucao.AGUARDANDO_ANUENCIA
    elif e == EtapaOperacional.PAGAMENTO:
        if s in (SubStatusOperacional.PG_AGUARDANDO_CLIENTE,):
            fase = FaseContratoExecucao.AGUARDANDO_PAGAMENTO_CLIENTE
        elif s == SubStatusOperacional.PG_PAGO_CLIENTE:
            fase = FaseContratoExecucao.CLIENTE_PAGO
        elif s in (
            SubStatusOperacional.PG_AGUARDANDO_TC,
            SubStatusOperacional.PG_PAGO_TC,
            SubStatusOperacional.PG_PAGO_TC_PARCIAL,
            SubStatusOperacional.PG_PAGO_TC_TOTAL,
            SubStatusOperacional.PG_AGUARDANDO_CMS,
            SubStatusOperacional.PG_PAGO_CMS,
            SubStatusOperacional.PG_PAGO_CMS_EMPRESA,
        ):
            fase = FaseContratoExecucao.AGUARDANDO_PAGAMENTO_TC
    elif e == EtapaOperacional.PENDENCIAS:
        fase = ce.fase  # mantém última fase “útil” visualmente; filas usam etapa
    ce.fase = fase


def _registrar_historico(ce, etapa_ant, sub_ant, etapa_nov, sub_nov, user, observacao=''):
    HistoricoTransicaoContrato.objects.create(
        contrato_execucao=ce,
        etapa_anterior=etapa_ant or '',
        sub_anterior=sub_ant or '',
        etapa_nova=etapa_nov,
        sub_nova=sub_nov,
        usuario=user,
        observacao=(observacao or '')[:500] or None,
    )


def valor_tc_efetivo_para_fluxo(ce):
    """
    TC usado em Pago TC, comprovantes e `requer_extra`: prioriza o snapshot
    (`ContratoDadosOperacionais`); se nulo ou <= 0, usa `PropostaDados`
    (ex.: TC preenchido só pela edição operacional antes de espelhar o DO).
    """
    v_do = Decimal('0')
    try:
        d = ce.dados_operacionais
        if d is not None and d.valor_tc is not None:
            v_do = Decimal(str(d.valor_tc))
    except Exception:
        pass
    if v_do > 0:
        return v_do
    try:
        pd = getattr(ce, 'proposta_dados', None)
        if pd is not None and pd.valor_tc is not None:
            v_pd = Decimal(str(pd.valor_tc))
            if v_pd > 0:
                return v_pd
    except Exception:
        pass
    return Decimal('0')


def _valor_tc_contrato(ce):
    return valor_tc_efetivo_para_fluxo(ce)


def _decimal_quant_2(v: Decimal) -> Decimal:
    return v.quantize(Decimal('0.01'))


def persistir_tc_modal_em_contrato_e_rm(ce, novo_tc: Decimal, soma_comprovantes: Decimal):
    """
    Persiste o TC informado no modal: snapshot operacional, proposta e fatias valor_est nos RegisterMoney.

    Observação: ``ContratoExecucao`` não possui coluna ``valor_tc`` — o TC do contrato na esteira fica em
    ``ContratoDadosOperacionais.valor_tc`` (OneToOne com o CE). ``PropostaDados.valor_tc`` é espelhado.

    Linhas ``RegisterMoney`` com ``status`` nulo ou True são tratadas como ativas (legado).

    soma_comprovantes deve incluir todos os comprovantes já gravados (ex.: após criar o atual no mesmo atomic).

    Retorna (True, None) ou (False, mensagem de erro).
    """
    novo_tc = _decimal_quant_2(Decimal(str(novo_tc)))
    soma_comprovantes = _decimal_quant_2(Decimal(str(soma_comprovantes)))
    if novo_tc <= 0:
        return False, 'Valor TC deve ser maior que zero.'
    if novo_tc < soma_comprovantes:
        return False, (
            'O valor TC não pode ser menor que a soma dos comprovantes já registrados '
            f'(mínimo R$ {soma_comprovantes}).'
        )
    try:
        d = ce.dados_operacionais
    except Exception:
        d = None
    if not d:
        return False, 'Contrato sem dados operacionais.'
    try:
        d.valor_tc = novo_tc
        d.save(update_fields=['valor_tc'])
    except Exception as exc:
        logger.exception(
            'persistir_tc_modal_em_contrato_e_rm: ContratoDadosOperacionais ce=%s',
            ce.pk,
        )
        return False, f'Erro ao salvar valor TC nos dados operacionais: {exc}'
    pd = getattr(ce, 'proposta_dados', None)
    if pd is not None:
        try:
            pd.valor_tc = novo_tc
            pd.save(update_fields=['valor_tc'])
        except Exception as exc:
            logger.exception(
                'persistir_tc_modal_em_contrato_e_rm: PropostaDados ce=%s',
                ce.pk,
            )
            return False, f'Erro ao salvar valor TC na proposta: {exc}'

    rms = list(
        RegisterMoney.objects.filter(contrato_execucao=ce)
        .filter(Q(status=True) | Q(status__isnull=True))
        .order_by('id')
    )
    if not rms:
        return True, None

    if len(rms) == 2 and all(getattr(r, 'flag_repasse', False) for r in rms):
        metade = (novo_tc / Decimal('2')).quantize(Decimal('0.01'))
        try:
            for r in rms:
                r.valor_est = metade
                r.save(update_fields=['valor_est'])
        except Exception as exc:
            logger.exception(
                'persistir_tc_modal_em_contrato_e_rm: RegisterMoney repasse ce=%s',
                ce.pk,
            )
            return False, f'Erro ao atualizar valor_est no RegisterMoney (repasse): {exc}'
        return True, None

    if len(rms) == 1:
        try:
            rms[0].valor_est = novo_tc
            rms[0].save(update_fields=['valor_est'])
        except Exception as exc:
            logger.exception(
                'persistir_tc_modal_em_contrato_e_rm: RegisterMoney único ce=%s',
                ce.pk,
            )
            return False, f'Erro ao atualizar valor_est no RegisterMoney: {exc}'
        return True, None

    # Cenário atípico (várias linhas sem repasse padrão): concentra no primeiro RM ativo.
    logger.warning(
        'persistir_tc_modal_em_contrato_e_rm: contrato %s com %s linhas RegisterMoney; atualizando apenas a primeira.',
        ce.pk,
        len(rms),
    )
    try:
        rms[0].valor_est = novo_tc
        rms[0].save(update_fields=['valor_est'])
        for r in rms[1:]:
            if r.valor_est and r.valor_est != Decimal('0'):
                r.valor_est = Decimal('0')
                r.save(update_fields=['valor_est'])
    except Exception as exc:
        logger.exception(
            'persistir_tc_modal_em_contrato_e_rm: RegisterMoney múltiplos ce=%s',
            ce.pk,
        )
        return False, f'Erro ao atualizar valor_est no RegisterMoney (múltiplas linhas): {exc}'
    return True, None


def zerar_tc_modal_em_contrato(ce):
    """
    Zera o Valor TC no snapshot operacional e na proposta (DO e PD).
    Bloqueia se ainda existir ComprovanteTC ativo.
    Ajusta valor_est dos RegisterMoney existentes para zero.
    Retorna (True, None) ou (False, mensagem de erro).
    """
    valor_tc_antes = _valor_tc_contrato(ce)
    if valor_tc_antes <= 0:
        return False, 'O contrato já está sem Valor TC.'

    if ComprovanteTC.objects.filter(contrato_execucao=ce, status=True).exists():
        return False, 'Exclua os comprovantes TC antes de zerar o Valor TC.'

    try:
        d = ce.dados_operacionais
    except Exception:
        d = None
    if not d:
        return False, 'Contrato sem dados operacionais.'

    zero = Decimal('0')
    try:
        d.valor_tc = zero
        d.save(update_fields=['valor_tc'])
    except Exception as exc:
        logger.exception('zerar_tc_modal_em_contrato: ContratoDadosOperacionais ce=%s', ce.pk)
        return False, f'Erro ao zerar valor TC nos dados operacionais: {exc}'

    pd = getattr(ce, 'proposta_dados', None)
    if pd is not None:
        try:
            pd.valor_tc = zero
            pd.save(update_fields=['valor_tc'])
        except Exception as exc:
            logger.exception('zerar_tc_modal_em_contrato: PropostaDados ce=%s', ce.pk)
            return False, f'Erro ao zerar valor TC na proposta: {exc}'

    rms = list(
        RegisterMoney.objects.filter(contrato_execucao=ce)
        .filter(Q(status=True) | Q(status__isnull=True))
        .order_by('id')
    )
    if not rms:
        return True, None

    try:
        if len(rms) == 2 and all(getattr(r, 'flag_repasse', False) for r in rms):
            for r in rms:
                r.valor_est = zero
                r.save(update_fields=['valor_est'])
        elif len(rms) == 1:
            rms[0].valor_est = zero
            rms[0].save(update_fields=['valor_est'])
        else:
            rms[0].valor_est = zero
            rms[0].save(update_fields=['valor_est'])
            for r in rms[1:]:
                if r.valor_est and r.valor_est != zero:
                    r.valor_est = zero
                    r.save(update_fields=['valor_est'])
    except Exception as exc:
        logger.exception('zerar_tc_modal_em_contrato: RegisterMoney ce=%s', ce.pk)
        return False, f'Erro ao zerar valor_est no RegisterMoney: {exc}'

    return True, None


def sincronizar_register_money_dados_modal_pago_tc(ce, rm_payload):
    """
    Atualiza linhas RegisterMoney já existentes com classificador, AF, loja e CMS do modal.
    Retorna (True, None) ou (False, mensagem).
    """
    if not rm_payload:
        return True, None
    from apps.vendas.siape.models import RegisterMoney

    rms = list(
        RegisterMoney.objects.filter(contrato_execucao=ce).filter(
            Q(status=True) | Q(status__isnull=True)
        )
    )
    if not rms:
        return True, None
    try:
        loja = resolve_loja_register_money_de_rm_payload(ce, rm_payload)
    except ValueError as exc:
        return False, str(exc)
    from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
        resolver_classificacao_valor_de_rm_payload,
    )

    cv = resolver_classificacao_valor_de_rm_payload(rm_payload)
    cv_id = cv.id if cv else rm_payload.get('classificacao_valor_id')
    af = rm_payload.get('af')
    for r in rms:
        upd = []
        if cv_id:
            r.classificacao_valor_id = cv_id
            upd.append('classificacao_valor_id')
        if af is not None:
            r.af = af
            upd.append('af')
        if 'venda_associada_loja' in rm_payload:
            r.loja = loja
            upd.append('loja')
        for fld in ('valor_cms_recebido', 'valor_cms_repassado', 'valor_cms_plastico'):
            if rm_payload.get(fld) is not None:
                setattr(r, fld, rm_payload[fld])
                upd.append(fld)
        if 'flag_cms_pago' in rm_payload:
            r.flag_cms_pago = bool(rm_payload.get('flag_cms_pago'))
            upd.append('flag_cms_pago')
        if upd:
            r.save(update_fields=upd)
    return True, None


def _parse_dec_rm(val):
    """Decimal a partir de número, string ou Decimal (aceita pt-BR: 2.920,00)."""
    if val is None or val == '':
        return None
    if isinstance(val, Decimal):
        return val
    s = str(val).strip()
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


def _siape_produto_id_por_contratos_produto(produto_contratos):
    """
    Mapeia ``contratos.Produto`` -> ``siape.Produto`` por título (case-insensitive),
    pois RegisterMoney.produto referencia ``siape.Produto`` e não pode receber o
    PK do catálogo de contratos (FKs são tabelas distintas e coexistem).
    Retorna o id do ``siape.Produto`` correspondente ou ``None`` se não houver match.
    """
    if not produto_contratos:
        return None
    titulo = (getattr(produto_contratos, 'titulo', '') or '').strip()
    if not titulo:
        return None
    try:
        from apps.vendas.siape.models import Produto as SiapeProduto

        sp = (
            SiapeProduto.objects.filter(nome__iexact=titulo).first()
            or SiapeProduto.objects.filter(nome__icontains=titulo).first()
        )
        if not sp:
            # Se não houver correspondência no catálogo SIAPE, cria o produto
            # automaticamente para não bloquear a criação do RegisterMoney.
            sp = SiapeProduto.objects.create(nome=titulo)
        return sp.id if sp else None
    except Exception:
        return None


def _loja_from_contrato(ce):
    """CapitalCredito: loja não vem de presença INSS; retorna None (escolha manual no Pago TC)."""
    return None


def _lojas_m2m_dicts_por_usuario(user):
    """Lojas ativas (M2M) do Funcionario vinculado ao User; lista de dicts id/nome ordenada."""
    if not user:
        return []
    try:
        from apps.rh.funcionarios.models import Funcionario

        f0 = (
            Funcionario.objects.filter(usuario=user, status=True)
            .prefetch_related('dados_profissionais__lojas')
            .first()
        )
        if not f0:
            f0 = (
                Funcionario.objects.filter(usuario=user)
                .prefetch_related('dados_profissionais__lojas')
                .order_by('-id')
                .first()
            )
        if not f0:
            return []
        dp = getattr(f0, 'dados_profissionais', None)
        if not dp:
            return []
        return list(dp.lojas.filter(status=True).values('id', 'nome').order_by('nome'))
    except Exception:
        return []


def lojas_elegiveis_m2m_destinatarios_register_money_ce(ce):
    """
    Lojas elegíveis para o modal Pago TC: M2M dos funcionários dos mesmos users
    que recebem RegisterMoney (responsável + repasse ou solicitante).
    Com repasse: interseção por id de loja.
    """
    from apps.contratos_v2.services.repasse_carteira import resolver_contexto_repasse_contrato

    users = []
    try:
        ctx = resolver_contexto_repasse_contrato(ce)
        if ctx.get('user_responsavel'):
            users.append(ctx['user_responsavel'])
        elif ctx.get('user_responsavel_id'):
            from django.contrib.auth.models import User

            u = User.objects.filter(pk=ctx['user_responsavel_id']).first()
            if u:
                users.append(u)
        if ctx.get('user_repasse'):
            users.append(ctx['user_repasse'])
        elif ctx.get('user_repasse_id'):
            from django.contrib.auth.models import User

            u = User.objects.filter(pk=ctx['user_repasse_id']).first()
            if u:
                users.append(u)
        if not users:
            sol = ce.solicitacao_digitacao if ce.solicitacao_digitacao_id else None
            if sol and sol.criado_por_id:
                users.append(sol.criado_por)
    except Exception:
        pass
    if not users:
        return []
    listas = [_lojas_m2m_dicts_por_usuario(u) for u in users]
    if len(listas) == 1:
        return listas[0]
    conjuntos = [{row['id'] for row in lst} for lst in listas if lst]
    if not conjuntos:
        return []
    ids_comuns = set.intersection(*conjuntos)
    primeira = listas[0]
    return [row for row in primeira if row['id'] in ids_comuns]


def resolve_loja_register_money_de_rm_payload(ce, rm_payload):
    """
    Loja a persistir no RegisterMoney conforme escolha do Pago TC.
    Sem chave venda_associada_loja: mantém _loja_from_contrato(ce).
    False: sem loja (None).
    True: loja_id obrigatório e deve estar em lojas_elegiveis_m2m_destinatarios_register_money_ce.
    """
    if rm_payload is None:
        rm_payload = {}
    if 'venda_associada_loja' not in rm_payload:
        return _loja_from_contrato(ce)
    raw = rm_payload.get('venda_associada_loja')
    if raw in (None, False, 'false', '0', 0, 'False', ''):
        return None
    if raw in (True, 'true', '1', 1, 'True'):
        lid = rm_payload.get('loja_id')
        try:
            lid = int(lid) if lid not in (None, '') else None
        except (TypeError, ValueError):
            lid = None
        if lid is None:
            raise ValueError('Venda associada a loja: selecione uma loja válida.')
        permitidos = {row['id'] for row in lojas_elegiveis_m2m_destinatarios_register_money_ce(ce)}
        if lid not in permitidos:
            raise ValueError('Loja selecionada não é elegível para os destinatários deste contrato.')
        from apps.rh.admin.models import Loja

        loja = Loja.objects.filter(pk=lid, status=True).first()
        if not loja:
            raise ValueError('Loja inválida ou inativa.')
        return loja
    return _loja_from_contrato(ce)


def _org_funcionario_por_user(user):
    """
    Empresa, departamento, setor e equipe do Funcionario vinculado ao User (ativo; senão o mais recente).
    Usado ao criar RegisterMoney para espelhar o vínculo organizacional de cada destinatário.
    """
    if not user:
        return {}
    try:
        from apps.rh.funcionarios.models import Funcionario

        f0 = (
            Funcionario.objects.filter(usuario=user, status=True)
            .select_related(
                'dados_profissionais__empresa',
                'dados_profissionais__departamento',
                'dados_profissionais__setor',
                'dados_profissionais__equipe',
            )
            .first()
        )
        if not f0:
            f0 = (
                Funcionario.objects.filter(usuario=user)
                .select_related(
                    'dados_profissionais__empresa',
                    'dados_profissionais__departamento',
                    'dados_profissionais__setor',
                    'dados_profissionais__equipe',
                )
                .order_by('-id')
                .first()
            )
        if not f0:
            return {}
        dp = getattr(f0, 'dados_profissionais', None)
        if not dp:
            return {}
        return {
            'empresa': dp.empresa,
            'departamento': dp.departamento,
            'setor': dp.setor,
            'equipe': dp.equipe,
        }
    except Exception:
        return {}


def _soma_comprovantes_tc_ativos(ce):
    """Soma valores de comprovantes TC ativos do contrato."""
    total = Decimal('0')
    for c in ComprovanteTC.objects.filter(contrato_execucao=ce, status=True).only('valor'):
        if c.valor is not None:
            total += Decimal(str(c.valor))
    return total


def _sincronizar_valor_pago_tc_acumulado_rm(ce, sub_atual):
    """
    valor_est = TC estipulado na linha do RM; valor_pago_acumulado = TC já pago (comprovado ou quitado).

    - Há comprovantes: distribui a soma (mesma regra de acoes_crm._incrementar_acumulado_rm).
    - TC total ou Pago TC legado sem comprovante: considera a fatia valor_est já quitada no CRM.
    """
    soma_comp = _soma_comprovantes_tc_ativos(ce)
    if soma_comp > 0:
        from apps.contratos_v2.apis.acoes_crm import _incrementar_acumulado_rm

        _incrementar_acumulado_rm(ce, soma_comp)
        return
    if sub_atual in (
        SubStatusOperacional.PG_PAGO_TC_TOTAL,
        SubStatusOperacional.PG_PAGO_TC,
    ):
        for rm in RegisterMoney.objects.filter(contrato_execucao=ce, status=True):
            fatia = rm.valor_est or Decimal('0')
            if fatia > 0:
                rm.valor_pago_acumulado = fatia
                rm.save(update_fields=['valor_pago_acumulado'])


def _carteira_clientes_para_contrato_execucao(ce):
    """Carteira SIAPE ligada ao contrato: solicitação de digitação ou vínculos M2M."""
    sol = ce.solicitacao_digitacao if ce.solicitacao_digitacao_id else None
    if sol and sol.carteira_clientes_id:
        return sol.carteira_clientes
    cart = CarteiraClientes.objects.filter(contratos_operacionais=ce).first()
    if cart:
        return cart
    if ce.proposta_dados_id:
        return CarteiraClientes.objects.filter(propostas_operacionais=ce.proposta_dados_id).first()
    return None


def _proposta_siape_id_para_contrato_execucao(ce, produto_siape_id=None):
    """CapitalCredito não usa modelo comercial Proposta (siape legado); RM via contrato_execucao."""
    return None


def _disparar_registermoney_se_necessario(ce, rm_payload=None):
    """
    RegisterMoney: após Pago TC (com TC, payload do modal); ou sem TC após Pago CMS (legado).
    Com repasse na carteira: dois RM (metade do TC cada), AF/CMS só no responsável.
    """
    if RegisterMoney.objects.filter(contrato_execucao=ce).exists():
        return
    sub = ce.sub_status_operacional
    sem_tc = _valor_tc_contrato(ce) <= 0
    # Aceita Pago TC (legado), Parcial e Total como gatilho do primeiro RegisterMoney.
    subs_tc = (
        SubStatusOperacional.PG_PAGO_TC,
        SubStatusOperacional.PG_PAGO_TC_PARCIAL,
        SubStatusOperacional.PG_PAGO_TC_TOTAL,
    )
    dispara = False
    if sub in subs_tc:
        dispara = True
    if sub == SubStatusOperacional.PG_PAGO_CMS and sem_tc:
        dispara = True
    if not dispara:
        return

    cpf = (ce.cliente_dados_pessoais.cpf or '').strip()
    produto_id = None
    try:
        d = ce.dados_operacionais
        # Atenção: ContratoDadosOperacionais.produto -> contratos.Produto;
        # RegisterMoney.produto -> siape.Produto. São catálogos distintos,
        # então mapeamos por título (case-insensitive). Sem match -> None.
        produto_id = _siape_produto_id_por_contratos_produto(d.produto)
    except Exception:
        d = None

    from apps.contratos_v2.services.repasse_carteira import resolver_contexto_repasse_contrato

    sol = ce.solicitacao_digitacao if ce.solicitacao_digitacao_id else None
    ctx_rep = resolver_contexto_repasse_contrato(ce)
    cart = _carteira_clientes_para_contrato_execucao(ce)
    loja_final = resolve_loja_register_money_de_rm_payload(ce, rm_payload)
    # Proposta SIAPE (esteira) correspondente ao contrato — evita RM só com contrato_execucao
    proposta_siape_id = _proposta_siape_id_para_contrato_execucao(ce, produto_id)

    if sub in subs_tc:
        if sem_tc:
            af = None
            valor_cms_rec = None
            valor_cms_rep = None
            valor_cms_pla = None
            flag_cms = False
            cv_id = None
            if d:
                af = d.valor_af
                tr = getattr(d, 'taxa_recebido_snapshot', None)
                if tr is None and getattr(d, 'tabela_cms_id', None):
                    tr = getattr(d.tabela_cms, 'taxa_recebido', None)
                tp = getattr(d, 'taxa_repasse_snapshot', None)
                if tp is None and getattr(d, 'tabela_cms_id', None):
                    tp = getattr(d.tabela_cms, 'taxa_repasse', None)
                tpl = getattr(d, 'taxa_plastico_snapshot', None)
                if tpl is None and getattr(d, 'tabela_cms_id', None):
                    tpl = getattr(d.tabela_cms, 'taxa_plastico', None)

                af_base = af or Decimal('0')

                def _cms_calc(taxa):
                    if taxa is None or not af_base:
                        return None
                    try:
                        return (af_base * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01'))
                    except Exception:
                        return None

                valor_cms_rec = _cms_calc(tr)
                valor_cms_rep = _cms_calc(tp)
                valor_cms_pla = _cms_calc(tpl)
            if rm_payload:
                af = _parse_dec_rm(rm_payload.get('af')) if rm_payload.get('af') not in (None, '') else af
                valor_cms_rec = (
                    _parse_dec_rm(rm_payload.get('valor_cms_recebido'))
                    if rm_payload.get('valor_cms_recebido') not in (None, '')
                    else valor_cms_rec
                )
                valor_cms_rep = (
                    _parse_dec_rm(rm_payload.get('valor_cms_repassado'))
                    if rm_payload.get('valor_cms_repassado') not in (None, '')
                    else valor_cms_rep
                )
                valor_cms_pla = (
                    _parse_dec_rm(rm_payload.get('valor_cms_plastico'))
                    if rm_payload.get('valor_cms_plastico') not in (None, '')
                    else valor_cms_pla
                )
                flag_cms = bool(rm_payload.get('flag_cms_pago'))
                from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
                    resolver_classificacao_valor_de_rm_payload,
                )

                cv = resolver_classificacao_valor_de_rm_payload(rm_payload)
                cv_id = cv.id if cv else None
                if cv_id is None:
                    cv_raw = rm_payload.get('classificacao_valor_id')
                    try:
                        cv_id = int(cv_raw) if cv_raw not in (None, '') else None
                    except (TypeError, ValueError):
                        cv_id = None
            agora = timezone.now()
            user_rm = ctx_rep.get('user_responsavel')
            if not user_rm and ctx_rep.get('user_responsavel_id'):
                from django.contrib.auth.models import User

                user_rm = User.objects.filter(pk=ctx_rep['user_responsavel_id']).first()
            if not user_rm and sol:
                user_rm = sol.criado_por
            if not user_rm:
                raise ValueError(
                    'Pago TC (sem TC): nenhum usuário responsável encontrado '
                    '(cart.user_responsavel e sol.criado_por ausentes).'
                )
            org_rm = _org_funcionario_por_user(user_rm)
            rm = RegisterMoney.objects.create(
                user=user_rm,
                loja=loja_final,
                cpf_cliente=cpf or None,
                produto_id=produto_id,
                valor_est=Decimal('0'),
                valor_pago_acumulado=Decimal('0'),
                af=af,
                valor_cms_recebido=valor_cms_rec,
                valor_cms_repassado=valor_cms_rep,
                valor_cms_plastico=valor_cms_pla,
                flag_cms_pago=flag_cms,
                classificacao_valor_id=cv_id,
                contrato_execucao=ce,
                flag_repasse=False,
                data=agora,
                data_pago=agora,
                **org_rm,
            )
            rm.save(update_fields=['valor_pago_acumulado'])
            return

        if not rm_payload:
            # Sem payload do modal: aborta a criação. Erro será propagado para
            # rollback da transação atômica em aplicar_etapa_sub.
            raise ValueError(
                'Pago TC sem dados do registro financeiro (rm_payload ausente).'
            )
        # Parsing de valores: erros aqui devem subir para invalidar a transição.
        valor_tc_total = _parse_dec_rm(
            rm_payload.get('valor_est') or rm_payload.get('valor_est_tc')
        )
        if valor_tc_total is None or valor_tc_total <= 0:
            valor_tc_total = _valor_tc_contrato(ce)
        af = _parse_dec_rm(rm_payload.get('af'))
        if af is None and d:
            af = d.valor_af
        valor_cms_rec = _parse_dec_rm(rm_payload.get('valor_cms_recebido'))
        valor_cms_rep = _parse_dec_rm(rm_payload.get('valor_cms_repassado'))
        valor_cms_pla = _parse_dec_rm(rm_payload.get('valor_cms_plastico'))
        flag_cms = bool(rm_payload.get('flag_cms_pago'))
        from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
            resolver_classificacao_valor_de_rm_payload,
        )

        cv = resolver_classificacao_valor_de_rm_payload(rm_payload)
        cv_id = cv.id if cv else None
        if cv_id is None:
            cv_raw = rm_payload.get('classificacao_valor_id')
            try:
                cv_id = int(cv_raw) if cv_raw not in (None, '') else None
            except (TypeError, ValueError):
                cv_id = None
        if valor_tc_total is None or valor_tc_total <= 0:
            raise ValueError(
                'Pago TC: valor_est (Valor TC) inválido ou <= 0 em rm_payload.'
            )

        # Classificador automático (M1 novo / M2 retrabalho em 90 dias) ou
        # exceção manual (M3) definida no modal.
        from apps.vendas.siape.apis.classificador import classificar_tc_automatico
        forcar_m3 = bool(rm_payload.get('forcar_m3'))
        classificador_rm = None
        tipo_classificacao_rm = None
        # Escolhe o usuário-base para a regra de 90 dias (responsável comercial).
        _user_para_classificar = ctx_rep.get('user_responsavel')
        if not _user_para_classificar and ctx_rep.get('user_responsavel_id'):
            from django.contrib.auth.models import User

            _user_para_classificar = User.objects.filter(pk=ctx_rep['user_responsavel_id']).first()
        if not _user_para_classificar and sol:
            _user_para_classificar = sol.criado_por
        if forcar_m3:
            classificador_rm = 'M3'
            tipo_classificacao_rm = 'MANUAL'
        elif _user_para_classificar and cpf:
            classificador_rm, tipo_classificacao_rm = classificar_tc_automatico(
                cpf, _user_para_classificar
            )

        agora = timezone.now()

        if ctx_rep.get('tem_repasse') and ctx_rep.get('user_responsavel_id') and ctx_rep.get('user_repasse_id'):
            metade = (valor_tc_total / Decimal('2')).quantize(Decimal('0.01'))
            ur = ctx_rep.get('user_responsavel')
            ux = ctx_rep.get('user_repasse')
            org_resp = _org_funcionario_por_user(ur)
            org_rep = _org_funcionario_por_user(ux)
            RegisterMoney.objects.create(
                user_id=ctx_rep['user_responsavel_id'],
                loja=loja_final,
                cpf_cliente=cpf or None,
                produto_id=produto_id,
                valor_est=metade,
                af=af,
                valor_cms_recebido=valor_cms_rec,
                valor_cms_repassado=valor_cms_rep,
                valor_cms_plastico=valor_cms_pla,
                flag_cms_pago=flag_cms,
                classificacao_valor_id=cv_id,
                classificador_auto=classificador_rm,
                tipo_classificacao=tipo_classificacao_rm,
                contrato_execucao=ce,
                flag_repasse=True,
                data=agora,
                data_pago=agora,
                **org_resp,
            )
            RegisterMoney.objects.create(
                user_id=ctx_rep['user_repasse_id'],
                loja=loja_final,
                cpf_cliente=cpf or None,
                produto_id=produto_id,
                valor_est=metade,
                af=None,
                valor_cms_recebido=None,
                valor_cms_repassado=None,
                valor_cms_plastico=None,
                flag_cms_pago=flag_cms,
                classificacao_valor_id=cv_id,
                classificador_auto=classificador_rm,
                tipo_classificacao=tipo_classificacao_rm,
                contrato_execucao=ce,
                flag_repasse=True,
                data=agora,
                data_pago=agora,
                **org_rep,
            )
            _sincronizar_valor_pago_tc_acumulado_rm(ce, sub)
            return

        user_rm = ctx_rep.get('user_responsavel')
        if not user_rm and ctx_rep.get('user_responsavel_id'):
            from django.contrib.auth.models import User

            user_rm = User.objects.filter(pk=ctx_rep['user_responsavel_id']).first()
        if not user_rm and sol:
            user_rm = sol.criado_por
        if not user_rm:
            # Sem usuário destinatário não há como criar o RegisterMoney.
            raise ValueError(
                'Pago TC: nenhum usuário responsável encontrado '
                '(cart.user_responsavel e sol.criado_por ausentes).'
            )
        org_rm = _org_funcionario_por_user(user_rm)
        RegisterMoney.objects.create(
            user=user_rm,
            loja=loja_final,
            cpf_cliente=cpf or None,
            produto_id=produto_id,
            valor_est=valor_tc_total if valor_tc_total > 0 else None,
            af=af,
            valor_cms_recebido=valor_cms_rec,
            valor_cms_repassado=valor_cms_rep,
            valor_cms_plastico=valor_cms_pla,
            flag_cms_pago=flag_cms,
            classificacao_valor_id=cv_id,
            classificador_auto=classificador_rm,
            tipo_classificacao=tipo_classificacao_rm,
            contrato_execucao=ce,
            flag_repasse=False,
            data=agora,
            data_pago=agora,
            **org_rm,
        )
        _sincronizar_valor_pago_tc_acumulado_rm(ce, sub)
        return

    # Sem TC: um RM após Pago CMS (legado)
    user_rm = None
    if sol:
        user_rm = sol.criado_por
    if not user_rm:
        return
    try:
        valor_est = d.valor_liberado or d.valor_af or Decimal('0') if d else Decimal('0')
        af = d.valor_af if d else None
    except Exception:
        valor_est = Decimal('0')
        af = None

    agora_cms = timezone.now()
    org_rm = _org_funcionario_por_user(user_rm)
    RegisterMoney.objects.create(
        user=user_rm,
        loja=loja_final,
        cpf_cliente=cpf or None,
        produto_id=produto_id,
        valor_est=valor_est if valor_est > 0 else None,
        af=af,
        contrato_execucao=ce,
        proposta_id=proposta_siape_id,
        flag_repasse=False,
        data=agora_cms,
        data_pago=agora_cms,
        **org_rm,
    )


def _executar_corpo_aplicar_etapa_sub(
    ce,
    etapa_ant,
    sub_ant,
    etapa_nova,
    sub_nova,
    user,
    observacao,
    sincronizar_legado,
    rm_payload,
):
    """Save do ContratoExecucao + histórico + gatilhos RM; deve rodar dentro de uma transação ativa."""
    ce.etapa_operacional = etapa_nova
    ce.sub_status_operacional = sub_nova
    if etapa_nova == EtapaOperacional.PAGAMENTO:
        if sub_nova == SubStatusOperacional.PG_PAGO_CLIENTE:
            ce.tag_financeira = TagFinanceiraContrato.PAGO_CLIENTE
        elif sub_nova in (
            SubStatusOperacional.PG_PAGO_TC,
            SubStatusOperacional.PG_PAGO_TC_PARCIAL,
            SubStatusOperacional.PG_PAGO_TC_TOTAL,
        ):
            ce.tag_financeira = TagFinanceiraContrato.PAGO_TC
        elif sub_nova == SubStatusOperacional.PG_AGUARDANDO_CMS:
            ce.tag_financeira = TagFinanceiraContrato.AGUARDANDO_PAGAMENTO_EMPRESA
        elif sub_nova in (
            SubStatusOperacional.PG_PAGO_CMS,
            SubStatusOperacional.PG_PAGO_CMS_EMPRESA,
        ):
            ce.tag_financeira = TagFinanceiraContrato.PAGO_CMS
    if sincronizar_legado:
        sincronizar_fase_legada(ce)
    ce.save()
    _registrar_historico(ce, etapa_ant, sub_ant, etapa_nova, sub_nova, user, observacao)
    _disparar_registermoney_se_necessario(ce, rm_payload=rm_payload)
    if sub_nova == SubStatusOperacional.PG_PAGO_CMS:
        RegisterMoney.objects.filter(contrato_execucao=ce).update(flag_cms_pago=True)
    if sub_nova == SubStatusOperacional.CAN_REEMBOLSO:
        RegisterMoney.objects.filter(contrato_execucao=ce, status=True).update(status=False)


def aplicar_etapa_sub(
    ce,
    etapa_nova,
    sub_nova,
    user,
    observacao='',
    sincronizar_legado=True,
    rm_payload=None,
    inner_atomic=True,
):
    """Persiste etapa/sub, histórico, fase legada e tag financeira derivada.

    Quando ``inner_atomic`` é True (padrão), abre ``transaction.atomic()`` aqui.
    Use ``inner_atomic=False`` se o chamador já envolveu a operação em
    ``transaction.atomic()`` — evita savepoint aninhado (causa de 500 em alguns fluxos).
    """
    if ce.etapa_operacional == etapa_nova and ce.sub_status_operacional == sub_nova:
        return True, ''
    if not par_etapa_sub_valido(etapa_nova, sub_nova):
        return False, 'Combinação etapa/sub-status inválida.'
    etapa_ant = ce.etapa_operacional
    sub_ant = ce.sub_status_operacional
    try:
        if inner_atomic:
            with transaction.atomic():
                _executar_corpo_aplicar_etapa_sub(
                    ce,
                    etapa_ant,
                    sub_ant,
                    etapa_nova,
                    sub_nova,
                    user,
                    observacao,
                    sincronizar_legado,
                    rm_payload,
                )
        else:
            _executar_corpo_aplicar_etapa_sub(
                ce,
                etapa_ant,
                sub_ant,
                etapa_nova,
                sub_nova,
                user,
                observacao,
                sincronizar_legado,
                rm_payload,
            )
    except ValueError as exc:
        # Erros de validação previsíveis (ex.: rm_payload incompleto) — mensagem amigável.
        logger.warning(
            'aplicar_etapa_sub: rollback por validação (ce=%s, %s→%s): %s',
            ce.pk, sub_ant, sub_nova, exc,
        )
        return False, str(exc)
    except Exception as exc:
        # Erros inesperados: log com stacktrace e devolve mensagem genérica para o usuário.
        logger.exception(
            'aplicar_etapa_sub: rollback por exceção (ce=%s, %s→%s)',
            ce.pk, sub_ant, sub_nova,
        )
        return False, f'Falha ao registrar transição/registro financeiro: {exc}'
    return True, ''


def transicao_por_acao(ce, user, papel, acao, observacao='', extras=None):
    """
    Ações nomeadas (nexos). Retorna (ok, mensagem).
    extras: ex. {'registermoney': {...}} para supervisor_pago_tc com TC > 0.
    """
    e = ce.etapa_operacional
    s = ce.sub_status_operacional

    if acao == 'pendencia_entrar':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e == EtapaOperacional.CANCELADO:
            return False, 'Contrato cancelado.'
        ce.pendencia_etapa_origem = e
        ce.pendencia_sub_origem = s
        ce.save(update_fields=['pendencia_etapa_origem', 'pendencia_sub_origem', 'data_ultima_atualizacao'])
        return aplicar_etapa_sub(ce, EtapaOperacional.PENDENCIAS, SubStatusOperacional.PEND_AGUARDANDO, user, observacao)

    if acao == 'pendencia_corrigido':
        # Operacional/supervisor (via CRM) ou vendedor (após correções na carteira).
        if papel not in (PAPEL_OPERACIONAL, PAPEL_SUPERVISOR, PAPEL_VENDEDOR):
            return False, 'Sem permissão para concluir retorno de pendência.'
        orig_e = ce.pendencia_etapa_origem
        orig_s = ce.pendencia_sub_origem
        if not orig_e or not orig_s:
            return False, 'Sem etapa de origem da pendência.'
        ce.pendencia_etapa_origem = None
        ce.pendencia_sub_origem = None
        ce.save(update_fields=['pendencia_etapa_origem', 'pendencia_sub_origem'])
        if not par_etapa_sub_valido(orig_e, orig_s):
            return False, 'Origem inválida.'
        return aplicar_etapa_sub(ce, orig_e, orig_s, user, observacao or 'Retorno pós-pendência')

    # Operacional marca "Digitado" (pré-estado antes de liberar link) — etapa Digitação.
    if acao == 'operacional_digitado':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.DIGITACAO or s not in (
            SubStatusOperacional.DIG_AGUARDANDO,
            SubStatusOperacional.DIG_DIGITADO,
        ):
            return False, 'Contrato não está em digitação válida.'
        return aplicar_etapa_sub(ce, EtapaOperacional.DIGITACAO, SubStatusOperacional.DIG_DIGITADO, user, observacao)

    if acao == 'operacional_link_disponibilizado':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        # Aceita tanto fluxo novo (Digitação: Aguardando/Digitado) quanto legado.
        if not (
            (e == EtapaOperacional.DIGITACAO and s in (
                SubStatusOperacional.DIG_AGUARDANDO,
                SubStatusOperacional.DIG_DIGITADO,
                SubStatusOperacional.DIG_LINK_DISPONIBILIZADO,
            ))
            or (e == EtapaOperacional.FORMALIZACAO and s == SubStatusOperacional.FORM_LINK_DISPONIVEL)
        ):
            return False, 'Contrato não está em digitação válida.'
        return aplicar_etapa_sub(
            ce, EtapaOperacional.FORMALIZACAO, SubStatusOperacional.FORM_LINK_DISPONIVEL, user, observacao
        )

    if acao in ('supervisor_checado', 'vendedor_checado_formalizacao'):
        if acao == 'supervisor_checado':
            if papel != PAPEL_SUPERVISOR:
                return False, 'Apenas supervisor.'
        else:
            if papel != PAPEL_VENDEDOR:
                return False, 'Apenas consultor/vendedor.'
            if not _usuario_e_responsavel_carteira_do_contrato(user, ce):
                return False, 'Apenas o responsável pela carteira deste contrato pode registrar a checagem.'
        # Aceita fluxo novo (FORMALIZACAO) e legado (DIGITACAO com subs antigos).
        permitido = (
            (e == EtapaOperacional.FORMALIZACAO and s in (
                SubStatusOperacional.FORM_LINK_DISPONIVEL,
                SubStatusOperacional.FORM_CHECADO,
            ))
            or (e == EtapaOperacional.DIGITACAO and s in (
                SubStatusOperacional.DIG_LINK_DISPONIBILIZADO,
                SubStatusOperacional.DIG_CHECADO,
            ))
        )
        if not permitido:
            return False, 'Disponível após link de formalização.'
        ext = extras or {}
        nr_raw = (ext.get('nivel_risco_checagem') or '').strip().upper()
        if nr_raw not in ('BAIXO', 'ALTO'):
            return False, 'Informe o nível de risco: Baixo ou Alto.'
        ce.nivel_risco_checagem_supervisor = nr_raw
        risco_txt = (
            'Risco checagem: Baixo (alta probabilidade de fechamento do contrato).'
            if nr_raw == 'BAIXO'
            else 'Risco checagem: Alto (alto risco de desistência ou cancelamento).'
        )
        obs_base = (observacao or '').strip()
        obs_augmented = (obs_base + ' | ' + risco_txt) if obs_base else risco_txt
        # Já em Checado: só persiste risco + histórico (transição idempotente não salvaria o campo).
        if s in (SubStatusOperacional.FORM_CHECADO, SubStatusOperacional.DIG_CHECADO):
            ce.save(update_fields=['nivel_risco_checagem_supervisor', 'data_ultima_atualizacao'])
            _registrar_historico(ce, e, s, e, s, user, obs_augmented)
            return True, ''
        return aplicar_etapa_sub(
            ce, EtapaOperacional.FORMALIZACAO, SubStatusOperacional.FORM_CHECADO, user, obs_augmented
        )

    if acao in ('supervisor_formalizado', 'vendedor_formalizado_desde_link'):
        if acao == 'supervisor_formalizado':
            if papel != PAPEL_SUPERVISOR:
                return False, 'Apenas supervisor.'
        else:
            if papel != PAPEL_VENDEDOR:
                return False, 'Apenas consultor/vendedor.'
            if not _usuario_e_responsavel_carteira_do_contrato(user, ce):
                return False, 'Apenas o responsável pela carteira deste contrato pode formalizar neste estágio.'
        permitido = (
            (e == EtapaOperacional.FORMALIZACAO and s in (
                SubStatusOperacional.FORM_LINK_DISPONIVEL,
                SubStatusOperacional.FORM_CHECADO,
            ))
            or (e == EtapaOperacional.DIGITACAO and s in (
                SubStatusOperacional.DIG_LINK_DISPONIBILIZADO,
                SubStatusOperacional.DIG_CHECADO,
            ))
        )
        if not permitido:
            return False, 'Formalização exige link (e opcionalmente checagem).'
        return aplicar_etapa_sub(
            ce, EtapaOperacional.FORMALIZACAO, SubStatusOperacional.FORM_FORMALIZADO, user, observacao
        )

    # Vendedor/supervisor confirma que o cliente acessou e completou o link de formalização
    if acao == 'vendedor_formalizado':
        if papel not in (PAPEL_VENDEDOR, PAPEL_SUPERVISOR):
            return False, 'Sem permissão para formalizar.'
        permitido = (
            (e == EtapaOperacional.FORMALIZACAO and s == SubStatusOperacional.FORM_CHECADO)
            or (e == EtapaOperacional.DIGITACAO and s == SubStatusOperacional.DIG_CHECADO)
        )
        if not permitido:
            return False, 'Formalização exige contrato com status Checado.'
        return aplicar_etapa_sub(
            ce, EtapaOperacional.FORMALIZACAO, SubStatusOperacional.FORM_FORMALIZADO, user, observacao
        )

    def _cancelar_por_sub(sub_destino, papeis_permitidos, msg_permissao):
        if papel not in papeis_permitidos:
            return False, msg_permissao
        if e == EtapaOperacional.CANCELADO:
            return False, 'Já cancelado.'
        return aplicar_etapa_sub(ce, EtapaOperacional.CANCELADO, sub_destino, user, observacao)

    # Legado: integrações antigas podem ainda enviar esta ação
    if acao == 'supervisor_cancelar_contrato':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_ENCERRADO,
            (PAPEL_SUPERVISOR,),
            'Apenas supervisor.',
        )

    if acao == 'supervisor_cancelar_cliente':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_CLIENTE,
            (PAPEL_SUPERVISOR,),
            'Apenas supervisor.',
        )

    if acao == 'supervisor_cancelar_corretor':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_CORRETOR,
            (PAPEL_SUPERVISOR,),
            'Apenas supervisor.',
        )

    if acao == 'supervisor_cancelar_banco':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_BANCO,
            (PAPEL_SUPERVISOR,),
            'Apenas supervisor.',
        )

    if acao == 'supervisor_cancelar_reembolso':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_REEMBOLSO,
            (PAPEL_SUPERVISOR,),
            'Apenas supervisor.',
        )

    if acao == 'operacional_cancelar_cliente':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_CLIENTE,
            (PAPEL_OPERACIONAL,),
            'Apenas operacional.',
        )

    if acao == 'operacional_cancelar_corretor':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_CORRETOR,
            (PAPEL_OPERACIONAL,),
            'Apenas operacional.',
        )

    if acao == 'operacional_cancelar_banco':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_BANCO,
            (PAPEL_OPERACIONAL,),
            'Apenas operacional.',
        )

    if acao == 'operacional_cancelar_reembolso':
        return _cancelar_por_sub(
            SubStatusOperacional.CAN_REEMBOLSO,
            (PAPEL_OPERACIONAL,),
            'Apenas operacional.',
        )

    if acao == 'operacional_para_analise':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        permitido = (
            (e == EtapaOperacional.FORMALIZACAO and s == SubStatusOperacional.FORM_FORMALIZADO)
            or (e == EtapaOperacional.DIGITACAO and s == SubStatusOperacional.DIG_FORMALIZADO)
        )
        if not permitido:
            return False, 'Exige formalizado pelo supervisor.'
        return aplicar_etapa_sub(ce, EtapaOperacional.ANALISE, SubStatusOperacional.ANL_AGUARDANDO, user, observacao)

    if acao == 'vendedor_video_enviado':
        if papel != PAPEL_VENDEDOR:
            return False, 'Apenas vendedor.'
        if e == EtapaOperacional.ANALISE and s == SubStatusOperacional.ANL_AGUARDANDO:
            return True, ''
        permitido = (
            (e == EtapaOperacional.FORMALIZACAO and s == SubStatusOperacional.FORM_FORMALIZADO)
            or (e == EtapaOperacional.DIGITACAO and s == SubStatusOperacional.DIG_FORMALIZADO)
        )
        if permitido:
            return aplicar_etapa_sub(ce, EtapaOperacional.ANALISE, SubStatusOperacional.ANL_AGUARDANDO, user, observacao)
        return False, 'Fluxo inválido para envio de vídeo.'

    if acao == 'operacional_analise_sucesso':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.ANALISE:
            return False, 'Contrato não está em análise.'
        return aplicar_etapa_sub(ce, EtapaOperacional.ANALISE, SubStatusOperacional.ANL_SUCESSO, user, observacao)

    if acao == 'operacional_marcar_portabilidade':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        ce.portabilidade = True
        ce.save(update_fields=['portabilidade', 'data_ultima_atualizacao'])
        return True, ''

    if acao == 'operacional_para_cip':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        # Regra: só permite avançar para CIP se o produto for PORT/REFIN.
        if not _produto_requer_cip_refin(ce):
            return False, 'Produto atual não exige CIP (apenas PORT/REFIN).'
        if e != EtapaOperacional.ANALISE or s != SubStatusOperacional.ANL_SUCESSO:
            return False, 'Exige análise com sucesso.'
        return aplicar_etapa_sub(ce, EtapaOperacional.CIP, SubStatusOperacional.CIP_AGUARDANDO, user, observacao)

    if acao == 'operacional_cip_sucesso':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.CIP:
            return False, 'Não está em CIP.'
        return aplicar_etapa_sub(ce, EtapaOperacional.CIP, SubStatusOperacional.CIP_SUCESSO, user, observacao)

    if acao == 'operacional_para_refin':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.CIP or s != SubStatusOperacional.CIP_SUCESSO:
            return False, 'Exige CIP sucesso.'
        return aplicar_etapa_sub(ce, EtapaOperacional.REFIN, SubStatusOperacional.REFIN_AGUARDANDO, user, observacao)

    if acao == 'operacional_refin_sucesso':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.REFIN:
            return False, 'Não está em Refin.'
        return aplicar_etapa_sub(ce, EtapaOperacional.REFIN, SubStatusOperacional.REFIN_SUCESSO, user, observacao)

    if acao == 'operacional_para_anuencia':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        # Regra: produtos PORT/REFIN precisam passar por CIP/REFIN antes;
        # demais produtos vão direto de Análise aprovada → Anuência.
        if _produto_requer_cip_refin(ce):
            if e != EtapaOperacional.REFIN or s != SubStatusOperacional.REFIN_SUCESSO:
                return False, 'PORT/REFIN: exige Refin sucesso.'
        else:
            if e != EtapaOperacional.ANALISE or s != SubStatusOperacional.ANL_SUCESSO:
                return False, 'Exige análise com sucesso.'
        return aplicar_etapa_sub(ce, EtapaOperacional.ANUENCIA, SubStatusOperacional.ANU_AGUARDANDO, user, observacao)

    if acao == 'operacional_anuencia_averbado':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.ANUENCIA or s != SubStatusOperacional.ANU_AGUARDANDO:
            return False, 'Apenas com anuência aguardando.'
        return aplicar_etapa_sub(ce, EtapaOperacional.ANUENCIA, SubStatusOperacional.ANU_AVERBADO, user, observacao)

    if acao == 'operacional_abrir_pagamento':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.ANUENCIA or s != SubStatusOperacional.ANU_AVERBADO:
            return False, 'Exige contrato averbado em anuência.'
        if contrato_exige_video_conscientizacao_para_pagamento(ce) and not ce.flag_video_enviado:
            return False, 'Envio do vídeo de conscientização obrigatório antes de abrir Pagamento.'
        return aplicar_etapa_sub(
            ce, EtapaOperacional.PAGAMENTO, SubStatusOperacional.PG_AGUARDANDO_CLIENTE, user, observacao or 'Abertura pagamento'
        )

    if acao == 'operacional_pago_cliente':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        from apps.contratos_v2.services.port_refin import (
            ce_exige_fluxo_port_refin_pago_cliente,
            persistir_valor_saldo_contrato,
            processar_pago_cliente_port_refin_se_necessario,
            validar_valor_saldo_obrigatorio,
        )

        if e != EtapaOperacional.PAGAMENTO and not ce_exige_fluxo_port_refin_pago_cliente(ce):
            return False, 'Não está em pagamento.'
        if contrato_exige_video_conscientizacao_para_pagamento(ce) and not ce.flag_video_enviado:
            return False, 'Envio do vídeo de conscientização obrigatório antes do Pago Cliente.'

        try:
            valor_saldo = validar_valor_saldo_obrigatorio(extras, ce)
        except ValueError as exc:
            return False, str(exc)

        try:
            if processar_pago_cliente_port_refin_se_necessario(
                ce, user, observacao=observacao, extras=extras
            ):
                return True, ''
        except ValueError as exc:
            return False, str(exc)

        if valor_saldo is not None:
            persistir_valor_saldo_contrato(ce, valor_saldo)
        return aplicar_etapa_sub(ce, EtapaOperacional.PAGAMENTO, SubStatusOperacional.PG_PAGO_CLIENTE, user, observacao)

    if acao == 'operacional_aguardando_tc':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.PAGAMENTO or s != SubStatusOperacional.PG_PAGO_CLIENTE:
            return False, 'Exige pago cliente antes de aguardar TC.'
        return aplicar_etapa_sub(
            ce,
            EtapaOperacional.PAGAMENTO,
            SubStatusOperacional.PG_AGUARDANDO_TC,
            user,
            observacao or 'Aguardando Pagamento TC',
        )

    if acao in ('supervisor_pago_tc', 'operacional_pago_tc'):
        if acao == 'supervisor_pago_tc':
            if papel != PAPEL_SUPERVISOR:
                return False, 'Apenas supervisor.'
        else:
            if papel != PAPEL_OPERACIONAL:
                return False, 'Apenas operacional.'
        ja_tem_rm = RegisterMoney.objects.filter(contrato_execucao=ce).exists()
        # Com RM já criado, novos boletos só via comprovante-tc (não POST evoluir).
        if s == SubStatusOperacional.PG_PAGO_TC_PARCIAL and _valor_tc_contrato(ce) > 0:
            if ja_tem_rm:
                return False, (
                    'Para registrar novo pagamento TC, envie o comprovante no modal Pago TC '
                    '(Evoluir → Pago TC / comprovantes).'
                )
        subs_pago_tc = (
            SubStatusOperacional.PG_PAGO_CLIENTE,
            SubStatusOperacional.PG_AGUARDANDO_TC,
            SubStatusOperacional.PG_PAGO_TC_PARCIAL,
            SubStatusOperacional.PG_PAGO_TC_TOTAL,
        )
        if e != EtapaOperacional.PAGAMENTO or s not in subs_pago_tc:
            return False, 'Exige etapa Pagamento e sub-status compatível com confirmação de Pago TC.'
        sem_tc = _valor_tc_contrato(ce) <= 0
        if contrato_exige_video_conscientizacao_para_pagamento(ce) and not ce.flag_video_enviado:
            return False, 'Envio do vídeo de conscientização obrigatório antes do Pago TC.'
        if sem_tc:
            return aplicar_etapa_sub(
                ce,
                EtapaOperacional.PAGAMENTO,
                SubStatusOperacional.PG_PAGO_TC,
                user,
                observacao,
                rm_payload=(extras or {}).get('registermoney') if extras else None,
            )
        if ja_tem_rm:
            return False, (
                'RegisterMoney já registrado. Para novos pagamentos parciais, '
                'envie comprovantes no modal Pago TC.'
            )
        soma_comp = _soma_comprovantes_tc_ativos(ce)
        if soma_comp <= 0:
            return False, 'Envie ao menos um comprovante de pagamento TC antes de confirmar.'
        valor_tc = _valor_tc_contrato(ce)
        novo_sub = (
            SubStatusOperacional.PG_PAGO_TC_TOTAL
            if soma_comp >= valor_tc
            else SubStatusOperacional.PG_PAGO_TC_PARCIAL
        )
        rm_extras = (extras or {}).get('registermoney') if extras else None
        if not rm_extras:
            return False, 'Informe os dados do registro financeiro (Pago TC).'
        ok, msg = aplicar_etapa_sub(
            ce,
            EtapaOperacional.PAGAMENTO,
            novo_sub,
            user,
            observacao,
            rm_payload=rm_extras,
        )
        return ok, msg

    # Após Pago TC, operacional avança para aguardar confirmação de CMS (não é mais automático no supervisor_pago_tc)
    if acao == 'operacional_aguardando_cms':
        if papel != PAPEL_OPERACIONAL:
            return False, 'Apenas operacional.'
        if e != EtapaOperacional.PAGAMENTO or s not in (
            SubStatusOperacional.PG_PAGO_TC,
            SubStatusOperacional.PG_PAGO_TC_TOTAL,
        ):
            return False, 'Exige Pago TC ou Pago TC Total antes de aguardar CMS.'
        if _valor_tc_contrato(ce) > 0 and not RegisterMoney.objects.filter(contrato_execucao=ce).exists():
            return False, 'Confirme o registro financeiro (Pago TC) antes de aguardar CMS.'
        return aplicar_etapa_sub(
            ce,
            EtapaOperacional.PAGAMENTO,
            SubStatusOperacional.PG_AGUARDANDO_CMS,
            user,
            observacao or 'Aguardando pagamento CMS',
        )

    if acao == 'financeiro_pago_cms':
        if papel != PAPEL_FINANCEIRO:
            return False, 'Apenas financeiro.'
        if e != EtapaOperacional.PAGAMENTO or s != SubStatusOperacional.PG_AGUARDANDO_CMS:
            return False, 'Exige sub-status aguardando CMS (após TC ou sem TC).'
        return aplicar_etapa_sub(ce, EtapaOperacional.PAGAMENTO, SubStatusOperacional.PG_PAGO_CMS, user, observacao)

    return False, 'Ação desconhecida.'


# ---------------------------------------------------------------------------
# Modal Evoluir (CRM operacional): mesma lista para GET e validação do POST
# ---------------------------------------------------------------------------

# Ordem lógica dos estados da solicitação de simulação (referência; filtro na lista).
ORDEM_ESTADO_SIMULACAO = {
    EstadoSolicitacaoProposta.ENVIADA: 0,
    EstadoSolicitacaoProposta.EM_ANALISE_OPERACIONAL: 1,
    EstadoSolicitacaoProposta.RESULTADO_PROPOSTAS: 2,
    EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL: 3,
}


def transicoes_disponiveis_simulacao(estado):
    """
    Transições exibidas no Evoluir para solicitação de simulação.
    Em inelegível não há evolução (estado terminal).
    """
    if estado == EstadoSolicitacaoProposta.RESULTADO_INELEGIVEL:
        return []
    label_propostas = (
        'Editar propostas'
        if estado == EstadoSolicitacaoProposta.RESULTADO_PROPOSTAS
        else 'Registrar propostas'
    )
    transicoes = [
        {
            'acao': 'sim_propostas',
            'etapa': 'SIMULACAO',
            'etapa_label': 'Simulação',
            'sub': 'RESULTADO_PROPOSTAS',
            'sub_label': label_propostas,
            'requer_extra': 'form_propostas',
        },
        {
            'acao': 'sim_inelegivel',
            'etapa': 'SIMULACAO',
            'etapa_label': 'Simulação',
            'sub': 'RESULTADO_INELEGIVEL',
            'sub_label': 'Inelegível',
            'requer_extra': None,
        },
    ]
    for i, t in enumerate(transicoes):
        t['ordem'] = i
    return transicoes


def _anexar_ordem(transicoes):
    for i, t in enumerate(transicoes):
        t['ordem'] = i
    return transicoes


def _transicoes_cancelamento_supervisor(_etl, _subl):
    """Motivos de cancelamento para operacional e supervisor no modal Evoluir."""
    el = _etl.get('CANCELADO', 'Cancelado')
    motivos = [
        ('CAN_CLIENTE', 'Cancelado pelo cliente'),
        ('CAN_CORRETOR', 'Cancelado pelo corretor'),
        ('CAN_BANCO', 'Cancelado pelo banco'),
        ('CAN_REEMBOLSO', 'Estorno'),
    ]
    out = []
    for prefixo in ('operacional', 'supervisor'):
        for sub, fallback in motivos:
            out.append(
                {
                    'acao': f'{prefixo}_cancelar_{sub.replace("CAN_", "").lower()}',
                    'etapa': 'CANCELADO',
                    'etapa_label': el,
                    'sub': sub,
                    'sub_label': _subl.get(sub, fallback),
                    'requer_extra': 'observacao',
                }
            )
    return out


def transicoes_disponiveis_contrato_execucao(ce):
    """
    Lista canônica de transições do modal Evoluir para ContratoExecucao.
    Portabilidade: após análise aprovada só segue para CIP (não mostra Anuência direta).
    Pendência/cancelamento são laterais; pendencia_corrigido retorna à origem (exceção intencional).
    """
    e = ce.etapa_operacional
    s = ce.sub_status_operacional
    _etl = dict(EtapaOperacional.CHOICES)
    _subl = dict(SubStatusOperacional.CHOICES)
    _PEND = {
        'acao': 'pendencia_entrar',
        'etapa': 'PENDENCIAS',
        'etapa_label': _etl.get('PENDENCIAS', 'Pendente'),
        'sub': 'PEND_AGUARDANDO',
        'sub_label': _subl.get('PEND_AGUARDANDO', 'Pendência em aberto'),
        'requer_extra': 'observacao',
    }
    transicoes = []

    if e == EtapaOperacional.CANCELADO:
        return _anexar_ordem([])

    if e == EtapaOperacional.DIGITACAO:
        if s == SubStatusOperacional.DIG_AGUARDANDO:
            transicoes = [
                {
                    'acao': 'operacional_digitado',
                    'etapa': 'DIGITACAO',
                    'etapa_label': _etl.get('DIGITACAO', 'Digitando'),
                    'sub': 'DIG_DIGITADO',
                    'sub_label': _subl.get('DIG_DIGITADO', 'Digitado'),
                    'requer_extra': None,
                },
                {
                    'acao': 'operacional_link_disponibilizado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_LINK_DISPONIVEL',
                    'sub_label': _subl.get('FORM_LINK_DISPONIVEL', 'Link disponível'),
                    'requer_extra': 'link_formalizacao',
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.DIG_DIGITADO:
            transicoes = [
                {
                    'acao': 'operacional_link_disponibilizado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_LINK_DISPONIVEL',
                    'sub_label': _subl.get('FORM_LINK_DISPONIVEL', 'Link disponível'),
                    'requer_extra': 'link_formalizacao',
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.DIG_LINK_DISPONIBILIZADO:
            # Compat legado — promove para FORMALIZACAO
            transicoes = [
                {
                    'acao': 'supervisor_checado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_CHECADO',
                    'sub_label': _subl.get('FORM_CHECADO', 'Checado'),
                    'requer_extra': None,
                },
                {
                    'acao': 'supervisor_formalizado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_FORMALIZADO',
                    'sub_label': _subl.get('FORM_FORMALIZADO', 'Formalizado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.DIG_CHECADO:
            transicoes = [
                {
                    'acao': 'supervisor_formalizado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_FORMALIZADO',
                    'sub_label': _subl.get('FORM_FORMALIZADO', 'Formalizado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.DIG_FORMALIZADO:
            transicoes = [
                {
                    'acao': 'operacional_para_analise',
                    'etapa': 'ANALISE',
                    'etapa_label': _etl.get('ANALISE', 'Analisando'),
                    'sub': 'ANL_AGUARDANDO',
                    'sub_label': _subl.get('ANL_AGUARDANDO', 'Aguardando análise'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.FORMALIZACAO:
        if s == SubStatusOperacional.FORM_LINK_DISPONIVEL:
            transicoes = [
                {
                    'acao': 'supervisor_checado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_CHECADO',
                    'sub_label': _subl.get('FORM_CHECADO', 'Checado'),
                    'requer_extra': None,
                },
                {
                    'acao': 'supervisor_formalizado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_FORMALIZADO',
                    'sub_label': _subl.get('FORM_FORMALIZADO', 'Formalizado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.FORM_CHECADO:
            transicoes = [
                {
                    'acao': 'supervisor_formalizado',
                    'etapa': 'FORMALIZACAO',
                    'etapa_label': _etl.get('FORMALIZACAO', 'Formalização'),
                    'sub': 'FORM_FORMALIZADO',
                    'sub_label': _subl.get('FORM_FORMALIZADO', 'Formalizado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.FORM_FORMALIZADO:
            transicoes = [
                {
                    'acao': 'operacional_para_analise',
                    'etapa': 'ANALISE',
                    'etapa_label': _etl.get('ANALISE', 'Analisando'),
                    'sub': 'ANL_AGUARDANDO',
                    'sub_label': _subl.get('ANL_AGUARDANDO', 'Aguardando análise'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.ANALISE:
        if s == SubStatusOperacional.ANL_AGUARDANDO:
            transicoes = [
                {
                    'acao': 'operacional_analise_sucesso',
                    'etapa': 'ANALISE',
                    'etapa_label': _etl.get('ANALISE', 'Analisando'),
                    'sub': 'ANL_SUCESSO',
                    'sub_label': _subl.get('ANL_SUCESSO', 'Análise aprovada'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.ANL_SUCESSO:
            transicoes = []
            # Regra: se o PRODUTO da proposta/dados_operacionais tiver
            # 'PORT' ou 'REFIN' no título, seguimos pelo fluxo CIP → REFIN →
            # Anuência. Caso contrário, Análise aprovada vai direto p/ Anuência.
            requer_cip_refin = _produto_requer_cip_refin(ce)
            if requer_cip_refin:
                transicoes.append(
                    {
                        'acao': 'operacional_para_cip',
                        'etapa': 'CIP',
                        'etapa_label': _etl.get('CIP', 'CIP'),
                        'sub': 'CIP_AGUARDANDO',
                        'sub_label': _subl.get('CIP_AGUARDANDO', 'Aguardando CIP'),
                        'requer_extra': None,
                    }
                )
            else:
                transicoes.append(
                    {
                        'acao': 'operacional_para_anuencia',
                        'etapa': 'ANUENCIA',
                        'etapa_label': _etl.get('ANUENCIA', 'Anuência'),
                        'sub': 'ANU_AGUARDANDO',
                        'sub_label': _subl.get('ANU_AGUARDANDO', 'Aguardando anuência'),
                        'requer_extra': None,
                    }
                )
            transicoes += [_PEND] + _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.CIP:
        if s == SubStatusOperacional.CIP_AGUARDANDO:
            transicoes = [
                {
                    'acao': 'operacional_cip_sucesso',
                    'etapa': 'CIP',
                    'etapa_label': _etl.get('CIP', 'CIP'),
                    'sub': 'CIP_SUCESSO',
                    'sub_label': _subl.get('CIP_SUCESSO', 'CIP aprovado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.CIP_SUCESSO:
            transicoes = [
                {
                    'acao': 'operacional_para_refin',
                    'etapa': 'REFIN',
                    'etapa_label': _etl.get('REFIN', 'REFIN'),
                    'sub': 'REFIN_AGUARDANDO',
                    'sub_label': _subl.get('REFIN_AGUARDANDO', 'Aguardando REFIN'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.REFIN:
        if s == SubStatusOperacional.REFIN_AGUARDANDO:
            transicoes = [
                {
                    'acao': 'operacional_refin_sucesso',
                    'etapa': 'REFIN',
                    'etapa_label': _etl.get('REFIN', 'REFIN'),
                    'sub': 'REFIN_SUCESSO',
                    'sub_label': _subl.get('REFIN_SUCESSO', 'REFIN aprovado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.REFIN_SUCESSO:
            transicoes = [
                {
                    'acao': 'operacional_para_anuencia',
                    'etapa': 'ANUENCIA',
                    'etapa_label': _etl.get('ANUENCIA', 'Anuência'),
                    'sub': 'ANU_AGUARDANDO',
                    'sub_label': _subl.get('ANU_AGUARDANDO', 'Aguardando anuência'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.ANUENCIA:
        if s == SubStatusOperacional.ANU_AGUARDANDO:
            transicoes = [
                {
                    'acao': 'operacional_anuencia_averbado',
                    'etapa': 'ANUENCIA',
                    'etapa_label': _etl.get('ANUENCIA', 'Anuência'),
                    'sub': 'ANU_AVERBADO',
                    'sub_label': _subl.get('ANU_AVERBADO', 'Averbado'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.ANU_AVERBADO:
            transicoes = [
                {
                    'acao': 'operacional_abrir_pagamento',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_AGUARDANDO_CLIENTE',
                    'sub_label': _subl.get('PG_AGUARDANDO_CLIENTE', 'Aguardando Pagamento Cliente'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.PAGAMENTO:
        re_tc = 'registermoney_tc' if _valor_tc_contrato(ce) > 0 else None
        if s == SubStatusOperacional.PG_AGUARDANDO_CLIENTE:
            requer_pago_cli = None
            from apps.contratos_v2.services.port_refin import (
                contrato_exige_valor_saldo_pago_cliente,
                contrato_port_ja_tem_refin,
                produto_exige_refin_no_pago_cliente,
            )

            exige_saldo_port = contrato_exige_valor_saldo_pago_cliente(ce)
            if produto_exige_refin_no_pago_cliente(ce) and not contrato_port_ja_tem_refin(ce):
                requer_pago_cli = 'refin_port'
            transicoes = [
                {
                    'acao': 'operacional_pago_cliente',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_PAGO_CLIENTE',
                    'sub_label': _subl.get('PG_PAGO_CLIENTE', 'Pago Cliente'),
                    'requer_extra': requer_pago_cli,
                    'exige_valor_saldo_port': exige_saldo_port,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_PAGO_CLIENTE:
            transicoes = [
                {
                    'acao': 'operacional_aguardando_tc',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_AGUARDANDO_TC',
                    'sub_label': _subl.get('PG_AGUARDANDO_TC', 'Aguardando Verificação de Valores'),
                    'requer_extra': None,
                },
                {
                    'acao': 'operacional_pago_tc',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_PAGO_TC',
                    'sub_label': _subl.get('PG_PAGO_TC', 'Pago TC'),
                    'requer_extra': 'registermoney_tc',
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_AGUARDANDO_TC:
            transicoes = [
                {
                    'acao': 'operacional_pago_tc',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_PAGO_TC',
                    'sub_label': _subl.get('PG_PAGO_TC', 'Pago TC'),
                    'requer_extra': re_tc,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_PAGO_TC_PARCIAL:
            transicoes = [
                {
                    'acao': 'operacional_pago_tc',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_PAGO_TC',
                    'sub_label': 'Pago TC (comprovantes)',
                    'requer_extra': re_tc,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_PAGO_TC:
            transicoes = [
                {
                    'acao': 'operacional_aguardando_cms',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_AGUARDANDO_CMS',
                    'sub_label': _subl.get('PG_AGUARDANDO_CMS', 'Aguardando pagamento CMS'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_PAGO_TC_TOTAL:
            transicoes = [
                {
                    'acao': 'operacional_pago_tc',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_PAGO_TC_TOTAL',
                    'sub_label': 'Confirmar registro financeiro (Pago TC)',
                    'requer_extra': re_tc,
                },
                {
                    'acao': 'operacional_aguardando_cms',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_AGUARDANDO_CMS',
                    'sub_label': _subl.get('PG_AGUARDANDO_CMS', 'Aguardando pagamento CMS'),
                    'requer_extra': None,
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_AGUARDANDO_CMS:
            transicoes = [
                {
                    'acao': 'financeiro_pago_cms',
                    'etapa': 'PAGAMENTO',
                    'etapa_label': _etl.get('PAGAMENTO', 'Pagamento'),
                    'sub': 'PG_PAGO_CMS',
                    'sub_label': _subl.get('PG_PAGO_CMS', 'Pago CMS'),
                    'requer_extra': 'pago_cms_taxas',
                },
                _PEND,
            ] + _transicoes_cancelamento_supervisor(_etl, _subl)
        elif s == SubStatusOperacional.PG_PAGO_CMS:
            transicoes = _transicoes_cancelamento_supervisor(_etl, _subl)

    elif e == EtapaOperacional.PENDENCIAS:
        transicoes = [
            {
                'acao': 'pendencia_corrigido',
                'etapa': ce.pendencia_etapa_origem or 'DIGITACAO',
                'etapa_label': _etl.get(ce.pendencia_etapa_origem or '', ''),
                'sub': ce.pendencia_sub_origem or '',
                'sub_label': 'Corrigido (retornar à etapa de origem)',
                'requer_extra': 'observacao',
            },
        ]

    return _anexar_ordem(transicoes)


def contrato_permite_evolucao_livre(ce):
    """
    Contrato já gerado: operacional pode definir etapa/sub direto.
    Desligado em Cancelado e em Pagamento (nesta etapa só fluxo restrito).
    """
    if not ce or ce.etapa_operacional == EtapaOperacional.CANCELADO:
        return False
    if ce.etapa_operacional == EtapaOperacional.PAGAMENTO:
        return False
    return bool(ce.solicitacao_digitacao_id or ce.proposta_dados_id)


def transicoes_catalogo_livre_contrato():
    """Catálogo completo etapa/sub para modal Evoluir em modo livre."""
    _etl = dict(EtapaOperacional.CHOICES)
    _subl = dict(SubStatusOperacional.CHOICES)
    out = []
    ordem = 0
    for etapa, subs in _SUBS_POR_ETAPA.items():
        if etapa == EtapaOperacional.PAGAMENTO:
            continue
        for sub in sorted(subs, key=lambda s: _subl.get(s, s)):
            requer = None
            if sub == SubStatusOperacional.FORM_LINK_DISPONIVEL:
                requer = 'link_formalizacao'
            out.append({
                'acao': 'operacional_definir_status',
                'etapa': etapa,
                'etapa_label': _etl.get(etapa, etapa),
                'sub': sub,
                'sub_label': _subl.get(sub, sub),
                'requer_extra': requer,
                'ordem': ordem,
            })
            ordem += 1
    for sub, sub_label, requer in (
        (
            SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
            _subl.get(SubStatusOperacional.PG_AGUARDANDO_CLIENTE, 'Aguardando Pagamento Cliente'),
            'video_pagamento',
        ),
        (
            SubStatusOperacional.PG_PAGO_CLIENTE,
            _subl.get(SubStatusOperacional.PG_PAGO_CLIENTE, 'Pago Cliente'),
            'video_pagamento',
        ),
    ):
        out.append({
            'acao': 'operacional_definir_status',
            'etapa': EtapaOperacional.PAGAMENTO,
            'etapa_label': _etl.get(EtapaOperacional.PAGAMENTO, 'Pagamento'),
            'sub': sub,
            'sub_label': sub_label,
            'requer_extra': requer,
            'ordem': ordem,
        })
        ordem += 1
    return out


def criar_registermoney_ranking_supervisor(ce, user, rm_payload):
    """
    Pré-lança RegisterMoney pelo supervisor (ranking) sem alterar etapa/sub do contrato.
    Impede duplicidade quando o operacional registrar Pago TC depois.
    """
    if RegisterMoney.objects.filter(contrato_execucao=ce, status=True).exists():
        return False, 'Já existe registro financeiro ativo para este contrato.'

    rm_payload = rm_payload or {}
    try:
        d = ce.dados_operacionais
    except Exception:
        return False, 'Dados operacionais não encontrados.'

    valor_est = _parse_dec_rm(rm_payload.get('valor_est') or rm_payload.get('valor_est_tc'))
    if valor_est is None or valor_est < 0:
        return False, 'Informe valor TC válido (zero ou positivo).'
    af = _parse_dec_rm(rm_payload.get('af'))
    if af is None:
        af = d.valor_af

    af_base = d.valor_af or Decimal('0')

    def _taxa_snap(attr_snap, attr_tab):
        v = getattr(d, attr_snap, None)
        if v is not None:
            return v
        if d.tabela_cms_id:
            return getattr(d.tabela_cms, attr_tab, None)
        return None

    tr = _taxa_snap('taxa_recebido_snapshot', 'taxa_recebido')
    tp = _taxa_snap('taxa_repasse_snapshot', 'taxa_repasse')
    tpl = _taxa_snap('taxa_plastico_snapshot', 'taxa_plastico')

    def _cms_calc(taxa):
        if taxa is None or not af_base:
            return None
        try:
            return (af_base * Decimal(str(taxa)) / Decimal('100')).quantize(Decimal('0.01'))
        except Exception:
            return None

    valor_cms_rec = _parse_dec_rm(rm_payload.get('valor_cms_recebido'))
    if valor_cms_rec is None:
        valor_cms_rec = _cms_calc(tr)
    valor_cms_rep = _parse_dec_rm(rm_payload.get('valor_cms_repassado'))
    if valor_cms_rep is None:
        valor_cms_rep = _cms_calc(tp)
    valor_cms_pla = _parse_dec_rm(rm_payload.get('valor_cms_plastico'))
    if valor_cms_pla is None:
        valor_cms_pla = _cms_calc(tpl)

    cv_id = rm_payload.get('classificacao_valor_id')
    cl_fin_id = rm_payload.get('classificador_id')
    if cl_fin_id not in (None, ''):
        from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
            resolver_classificacao_valor_por_classificador_id,
        )

        cv = resolver_classificacao_valor_por_classificador_id(cl_fin_id)
        if not cv:
            return False, 'Classificador inválido ou inativo.'
        cv_id = cv.id
        rm_payload = dict(rm_payload)
        rm_payload['classificacao_valor_id'] = cv_id
    elif cv_id not in (None, ''):
        try:
            from apps.vendas.siape.models import ClassificacaoValor

            cv_id = int(cv_id)
            ClassificacaoValor.objects.get(pk=cv_id)
        except Exception:
            return False, 'Classificador de valor inválido.'
    else:
        cv_id = None

    cpf = (ce.cliente_dados_pessoais.cpf or '').strip() if ce.cliente_dados_pessoais_id else ''
    produto_id = _siape_produto_id_por_contratos_produto(d.produto) if d and d.produto_id else None
    sol = ce.solicitacao_digitacao if ce.solicitacao_digitacao_id else None
    cart = sol.carteira_clientes if sol and sol.carteira_clientes_id else None
    try:
        loja_final = resolve_loja_register_money_de_rm_payload(ce, rm_payload)
    except ValueError as e:
        return False, str(e)
    proposta_siape_id = _proposta_siape_id_para_contrato_execucao(ce, produto_id)

    user_rm = None
    if cart:
        user_rm = cart.user_responsavel
    if not user_rm and sol:
        user_rm = sol.criado_por
    if not user_rm:
        return False, 'Vendedor/responsável não identificado para o registro financeiro.'

    from apps.siape.apis.classificador import classificar_tc_automatico
    classificador_rm = None
    tipo_classificacao_rm = None
    if bool(rm_payload.get('forcar_m3')):
        classificador_rm = 'M3'
        tipo_classificacao_rm = 'MANUAL'
    elif user_rm and cpf and valor_est > 0:
        classificador_rm, tipo_classificacao_rm = classificar_tc_automatico(cpf, user_rm)

    agora = timezone.now()
    org_rm = _org_funcionario_por_user(user_rm)

    with transaction.atomic():
        RegisterMoney.objects.create(
            user=user_rm,
            loja=loja_final,
            cpf_cliente=cpf or None,
            produto_id=produto_id,
            valor_est=valor_est if valor_est > 0 else None,
            valor_pago_acumulado=valor_est if valor_est > 0 else Decimal('0'),
            af=af,
            valor_cms_recebido=valor_cms_rec,
            valor_cms_repassado=valor_cms_rep,
            valor_cms_plastico=valor_cms_pla,
            flag_cms_pago=bool(rm_payload.get('flag_cms_pago')),
            classificacao_valor_id=cv_id,
            classificador_auto=classificador_rm,
            tipo_classificacao=tipo_classificacao_rm,
            contrato_execucao=ce,
            flag_repasse=False,
            data=agora,
            data_pago=agora,
            status=True,
            **org_rm,
        )
    return True, ''


def acoes_evoluir_contrato_permitidas(ce):
    """Conjunto de ações aceitas no POST evoluir/ para o estado atual do contrato."""
    base = {t['acao'] for t in transicoes_disponiveis_contrato_execucao(ce)}
    if contrato_permite_evolucao_livre(ce):
        base.add('operacional_definir_status')
    try:
        from apps.contratos_v2.services.port_refin import ce_exige_fluxo_port_refin_pago_cliente

        if ce_exige_fluxo_port_refin_pago_cliente(ce):
            base.add('operacional_pago_cliente')
    except Exception:
        pass
    # Paridade consultor (SCT16): mesmos estados do supervisor, com ações dedicadas no POST evoluir/.
    if 'supervisor_checado' in base:
        base.add('vendedor_checado_formalizacao')
    if 'supervisor_formalizado' in base:
        base.add('vendedor_formalizado_desde_link')
    return base


def inicializar_nexos_contrato(ce):
    """Garante etapa/sub coerentes com fase legada (pós-migração ou criação)."""
    m = {
        FaseContratoExecucao.DIGITACAO_AGUARDANDO: (
            EtapaOperacional.DIGITACAO,
            SubStatusOperacional.DIG_AGUARDANDO,
        ),
        FaseContratoExecucao.AGUARDANDO_FORMALIZACAO: (
            EtapaOperacional.FORMALIZACAO,
            SubStatusOperacional.FORM_LINK_DISPONIVEL,
        ),
        FaseContratoExecucao.EM_ANALISE: (EtapaOperacional.ANALISE, SubStatusOperacional.ANL_AGUARDANDO),
        FaseContratoExecucao.AGUARDANDO_ANUENCIA: (EtapaOperacional.ANUENCIA, SubStatusOperacional.ANU_AGUARDANDO),
        FaseContratoExecucao.AGUARDANDO_PAGAMENTO_CLIENTE: (
            EtapaOperacional.PAGAMENTO,
            SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
        ),
        FaseContratoExecucao.CLIENTE_PAGO: (EtapaOperacional.PAGAMENTO, SubStatusOperacional.PG_PAGO_CLIENTE),
        FaseContratoExecucao.AGUARDANDO_PAGAMENTO_TC: (
            EtapaOperacional.PAGAMENTO,
            SubStatusOperacional.PG_AGUARDANDO_TC,
        ),
        FaseContratoExecucao.CANCELADO: (EtapaOperacional.CANCELADO, SubStatusOperacional.CAN_ENCERRADO),
    }
    etapa, sub = m.get(ce.fase, (EtapaOperacional.DIGITACAO, SubStatusOperacional.DIG_AGUARDANDO))
    ce.etapa_operacional = etapa
    ce.sub_status_operacional = sub
    sincronizar_fase_legada(ce)
