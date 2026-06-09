# -*- coding: utf-8 -*-
"""Sinais do app `contratos`.

Validação [7] — defesa em profundidade contra arquivos órfãos:
    Quando uma instância de `ClienteArquivo` é removida (pelo endpoint
    `api_post_excluir_cliente_arquivo` OU via cascata/admin/shell),
    tentamos remover o arquivo físico associado. A remoção explícita em
    `api_post_excluir_cliente_arquivo` continua sendo a via preferencial,
    mas este signal garante que nenhum caminho de exclusão deixe arquivo
    residual no storage.
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.contratos_v2.models import (
    ClienteArquivo,
    ContratoExecucao,
    HistoricoEventoDigitacao,
    HistoricoEventoSimulacao,
    HistoricoTransicaoContrato,
    Pendencia,
    PropostaDados,
)

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=ClienteArquivo)
def _remover_arquivo_fisico_cliente_arquivo(sender, instance, **kwargs):
    """Remove o arquivo físico do storage quando a row é apagada.

    O método é best-effort: erros (arquivo ausente, permissão) são logados
    mas não reescalados — impedir a exclusão da row por causa de resíduo
    de storage causaria mais dano do que benefício.
    """
    try:
        arq = getattr(instance, 'arquivo', None)
        if arq and getattr(arq, 'name', None):
            # save=False para evitar ciclo de salvamento em um objeto já apagado.
            arq.delete(save=False)
    except Exception:
        logger.warning(
            'post_delete ClienteArquivo: falha ao remover arquivo físico (id=%s).',
            getattr(instance, 'id', None),
            exc_info=True,
        )


@receiver(post_save, sender=HistoricoEventoSimulacao)
def _espelhar_historico_simulacao_tecnico(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.contratos_v2.services.historico_transacao import espelhar_evento_simulacao
        espelhar_evento_simulacao(instance)
    except Exception:
        logger.exception('Signal: falha ao espelhar HistoricoEventoSimulacao id=%s', instance.id)


@receiver(post_save, sender=HistoricoEventoDigitacao)
def _espelhar_historico_digitacao_tecnico(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.contratos_v2.services.historico_transacao import espelhar_evento_digitacao
        espelhar_evento_digitacao(instance)
    except Exception:
        logger.exception('Signal: falha ao espelhar HistoricoEventoDigitacao id=%s', instance.id)


@receiver(post_save, sender=HistoricoTransicaoContrato)
def _espelhar_historico_contrato_tecnico(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.contratos_v2.services.historico_transacao import espelhar_transicao_contrato
        espelhar_transicao_contrato(instance)
    except Exception:
        logger.exception('Signal: falha ao espelhar HistoricoTransicaoContrato id=%s', instance.id)


@receiver(post_save, sender=PropostaDados)
def _registrar_transacao_proposta_criacao(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.contratos_v2.services.historico_transacao import registrar_criacao_proposta
        registrar_criacao_proposta(instance)
    except Exception:
        logger.exception('Signal: falha ao registrar criação proposta id=%s', instance.id)


@receiver(post_save, sender=ContratoExecucao)
def _registrar_transacao_contrato_criacao(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.contratos_v2.services.historico_transacao import registrar_criacao_contrato
        registrar_criacao_contrato(instance)
    except Exception:
        logger.exception('Signal: falha ao registrar criação contrato id=%s', instance.id)


@receiver(post_save, sender=Pendencia)
def _registrar_transacao_pendencia(sender, instance, created, **kwargs):
    try:
        from apps.contratos_v2.services.historico_transacao import (
            registrar_pendencia_aberta,
            registrar_pendencia_resolvida,
        )
        if created:
            registrar_pendencia_aberta(instance)
        elif instance.resolvido and instance.resolvido_em:
            from apps.contratos_v2.models import HistoricoTransacaoContrato
            if not HistoricoTransacaoContrato.objects.filter(
                pendencia_id=instance.id,
                acao=HistoricoTransacaoContrato.ACAO_PENDENCIA_RESOLVIDA,
            ).exists():
                registrar_pendencia_resolvida(instance)
    except Exception:
        logger.exception('Signal: falha ao registrar pendência id=%s', instance.id)
