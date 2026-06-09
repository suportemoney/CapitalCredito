# -*- coding: utf-8 -*-
"""Serviço de histórico técnico de transações (simulação → proposta → contrato)."""
import logging
import uuid

from django.db.models import Max

from apps.contratos_v2.fluxo_constants import EtapaOperacional
from apps.contratos_v2.models import (
    ContratoExecucao,
    HistoricoEventoDigitacao,
    HistoricoEventoSimulacao,
    HistoricoTransacaoContrato,
    HistoricoTransacaoProposta,
    HistoricoTransacaoSimulacao,
    HistoricoTransicaoContrato,
    Pendencia,
    PropostaDados,
    SolicitacaoPropostaCliente,
)

logger = logging.getLogger(__name__)


def _nova_correlacao():
    return uuid.uuid4()


def _correlacao_simulacao(solicitacao_id):
    ultimo = (
        HistoricoTransacaoSimulacao.objects.filter(solicitacao_id=solicitacao_id)
        .aggregate(Max('correlacao_id'))
        .get('correlacao_id__max')
    )
    return ultimo or _nova_correlacao()


def _correlacao_proposta(proposta):
    if proposta.solicitacao_origem_id:
        return _correlacao_simulacao(proposta.solicitacao_origem_id)
    ultimo = (
        HistoricoTransacaoProposta.objects.filter(proposta_id=proposta.id)
        .aggregate(Max('correlacao_id'))
        .get('correlacao_id__max')
    )
    return ultimo or _nova_correlacao()


def _correlacao_contrato(contrato):
    if contrato.proposta_dados_id:
        return _correlacao_proposta(contrato.proposta_dados)
    ultimo = (
        HistoricoTransacaoContrato.objects.filter(contrato_id=contrato.id)
        .aggregate(Max('correlacao_id'))
        .get('correlacao_id__max')
    )
    return ultimo or _nova_correlacao()


def _carteira_simulacao(solicitacao):
    return getattr(solicitacao, 'carteira_clientes', None)


def _carteira_proposta(proposta):
    try:
        cart = proposta.carteiras_siape_propostas.first()
        if cart:
            return cart
    except Exception:
        pass
    if proposta.solicitacao_origem_id:
        return _carteira_simulacao(proposta.solicitacao_origem)
    return None


def _carteira_contrato(contrato):
    if contrato.carteira_clientes_snapshot_id:
        return contrato.carteira_clientes_snapshot
    pd = getattr(contrato, 'proposta_dados', None)
    if pd:
        return _carteira_proposta(pd)
    return None


def registrar_transacao_simulacao(
    solicitacao,
    acao,
    *,
    usuario=None,
    estado_anterior='',
    estado_novo='',
    proposta_vinculada=None,
    payload=None,
    observacao='',
    historico_evento=None,
    correlacao_id=None,
):
    try:
        HistoricoTransacaoSimulacao.objects.create(
            correlacao_id=correlacao_id or _correlacao_simulacao(solicitacao.id),
            solicitacao=solicitacao,
            carteira_clientes=_carteira_simulacao(solicitacao),
            acao=acao,
            estado_anterior=estado_anterior or '',
            estado_novo=estado_novo or '',
            payload=payload or {},
            proposta_vinculada=proposta_vinculada,
            historico_evento=historico_evento,
            usuario=usuario,
            observacao=(observacao or '')[:2000] or None,
        )
    except Exception:
        logger.exception('Falha ao registrar histórico técnico simulação (solicitação=%s)', solicitacao.id)


def registrar_transacao_proposta(
    proposta,
    acao,
    *,
    usuario=None,
    payload=None,
    observacao='',
    contrato_vinculado=None,
    historico_digitacao=None,
    correlacao_id=None,
):
    try:
        HistoricoTransacaoProposta.objects.create(
            correlacao_id=correlacao_id or _correlacao_proposta(proposta),
            proposta=proposta,
            solicitacao_origem=getattr(proposta, 'solicitacao_origem', None),
            carteira_clientes=_carteira_proposta(proposta),
            acao=acao,
            payload=payload or {},
            contrato_vinculado=contrato_vinculado,
            historico_digitacao=historico_digitacao,
            usuario=usuario,
            observacao=(observacao or '')[:2000] or None,
        )
    except Exception:
        logger.exception('Falha ao registrar histórico técnico proposta (proposta=%s)', proposta.id)


def registrar_transacao_contrato(
    contrato,
    acao,
    *,
    usuario=None,
    etapa_anterior='',
    sub_anterior='',
    etapa_nova='',
    sub_nova='',
    payload=None,
    observacao='',
    pendencia=None,
    historico_transicao=None,
    correlacao_id=None,
):
    try:
        sd = getattr(contrato, 'solicitacao_digitacao', None)
        HistoricoTransacaoContrato.objects.create(
            correlacao_id=correlacao_id or _correlacao_contrato(contrato),
            contrato=contrato,
            proposta_origem=getattr(contrato, 'proposta_dados', None),
            solicitacao_digitacao=sd,
            carteira_clientes=_carteira_contrato(contrato),
            acao=acao,
            etapa_anterior=etapa_anterior or '',
            sub_anterior=sub_anterior or '',
            etapa_nova=etapa_nova or '',
            sub_nova=sub_nova or '',
            payload=payload or {},
            pendencia=pendencia,
            historico_transicao=historico_transicao,
            usuario=usuario,
            observacao=(observacao or '')[:2000] or None,
        )
    except Exception:
        logger.exception('Falha ao registrar histórico técnico contrato (contrato=%s)', contrato.id)


def espelhar_evento_simulacao(evento: HistoricoEventoSimulacao):
    """Espelha evento da linha do tempo para log técnico."""
    if HistoricoTransacaoSimulacao.objects.filter(historico_evento_id=evento.id).exists():
        return
    acao = HistoricoTransacaoSimulacao.ACAO_TRANSICAO
    if evento.estado_anterior == '' and evento.estado_novo:
        acao = HistoricoTransacaoSimulacao.ACAO_CRIACAO
    registrar_transacao_simulacao(
        evento.solicitacao,
        acao,
        usuario=evento.usuario,
        estado_anterior=evento.estado_anterior,
        estado_novo=evento.estado_novo,
        observacao=evento.observacao or '',
        historico_evento=evento,
    )


def espelhar_evento_digitacao(evento: HistoricoEventoDigitacao):
    """Espelha evento de digitação vinculado à proposta."""
    if HistoricoTransacaoProposta.objects.filter(historico_digitacao_id=evento.id).exists():
        return
    sd = evento.solicitacao
    proposta = sd.proposta_dados if sd else None
    if not proposta:
        return
    acao = HistoricoTransacaoProposta.ACAO_ENVIO_DIGITACAO
    if 'CORRECAO' in (evento.estado_novo or '').upper():
        acao = HistoricoTransacaoProposta.ACAO_EDICAO
    registrar_transacao_proposta(
        proposta,
        acao,
        usuario=evento.usuario,
        payload={'estado_anterior': evento.estado_anterior, 'estado_novo': evento.estado_novo},
        observacao=evento.observacao or '',
        historico_digitacao=evento,
    )


def espelhar_transicao_contrato(transicao: HistoricoTransicaoContrato):
    """Espelha transição da linha do tempo para log técnico."""
    if HistoricoTransacaoContrato.objects.filter(historico_transicao_id=transicao.id).exists():
        return
    acao = HistoricoTransacaoContrato.ACAO_TRANSICAO
    if transicao.etapa_nova == EtapaOperacional.PENDENCIAS and transicao.etapa_anterior != EtapaOperacional.PENDENCIAS:
        acao = HistoricoTransacaoContrato.ACAO_ENTRADA_PENDENCIAS
    registrar_transacao_contrato(
        transicao.contrato_execucao,
        acao,
        usuario=transicao.usuario,
        etapa_anterior=transicao.etapa_anterior,
        sub_anterior=transicao.sub_anterior,
        etapa_nova=transicao.etapa_nova,
        sub_nova=transicao.sub_nova,
        observacao=transicao.observacao or '',
        historico_transicao=transicao,
    )


def registrar_criacao_proposta(proposta: PropostaDados, usuario=None, payload=None):
    registrar_transacao_proposta(
        proposta,
        HistoricoTransacaoProposta.ACAO_CRIACAO,
        usuario=usuario,
        payload=payload or {'codigo': proposta.codigo},
    )


def registrar_edicao_proposta(proposta: PropostaDados, usuario=None, payload=None):
    registrar_transacao_proposta(
        proposta,
        HistoricoTransacaoProposta.ACAO_EDICAO,
        usuario=usuario,
        payload=payload or {},
    )


def registrar_criacao_contrato(contrato: ContratoExecucao, usuario=None, payload=None):
    registrar_transacao_contrato(
        contrato,
        HistoricoTransacaoContrato.ACAO_CRIACAO,
        usuario=usuario,
        etapa_nova=contrato.etapa_operacional or '',
        sub_nova=contrato.sub_status_operacional or '',
        payload=payload or {'codigo': contrato.codigo},
    )


def registrar_pendencia_aberta(pendencia: Pendencia, usuario=None):
    registrar_transacao_contrato(
        pendencia.contrato_execucao,
        HistoricoTransacaoContrato.ACAO_PENDENCIA_ABERTA,
        usuario=usuario or pendencia.criado_por,
        pendencia=pendencia,
        payload={'tipo': pendencia.tipo, 'observacao': pendencia.observacao[:500]},
        observacao=f'Pendência aberta: {pendencia.get_tipo_display()}',
    )


def registrar_pendencia_resolvida(pendencia: Pendencia, usuario=None):
    registrar_transacao_contrato(
        pendencia.contrato_execucao,
        HistoricoTransacaoContrato.ACAO_PENDENCIA_RESOLVIDA,
        usuario=usuario or pendencia.resolvido_por,
        pendencia=pendencia,
        payload={'tipo': pendencia.tipo},
        observacao=f'Pendência resolvida: {pendencia.get_tipo_display()}',
    )
