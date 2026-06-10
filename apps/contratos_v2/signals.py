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

from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.contratos_v2.models import ClienteArquivo

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
