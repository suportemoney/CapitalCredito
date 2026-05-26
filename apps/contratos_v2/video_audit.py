# -*- coding: utf-8 -*-
"""Arquivamento de vídeo anterior do contrato antes de substituição (auditoria)."""
import logging
import os
import re

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

logger = logging.getLogger(__name__)

# Limite único de upload de vídeo (CRM, formalizar, etc.) — espelhar no front-end (JS)
VIDEO_UPLOAD_MAX_MB = 35
VIDEO_UPLOAD_MAX_BYTES = VIDEO_UPLOAD_MAX_MB * 1024 * 1024
MENSAGEM_ERRO_VIDEO_TAMANHO = (
    'O vídeo excede o tamanho máximo permitido (35 MB). Envie um arquivo menor.'
)


def video_upload_excede_limite(uploaded_file):
    """Retorna True se o arquivo ultrapassa VIDEO_UPLOAD_MAX_BYTES."""
    size = getattr(uploaded_file, 'size', None)
    if size is None:
        return False
    return size > VIDEO_UPLOAD_MAX_BYTES


def arquivar_video_atual_contrato(ce):
    """
    Copia o arquivo atual de video_cliente para contratos/videos_auditoria/YYYY/MM/.
    Não altera o modelo; chamar antes de atribuir novo arquivo.
    """
    field = ce.video_cliente
    if not field or not field.name:
        return
    try:
        with field.open('rb') as src:
            blob = src.read()
        ts = timezone.now().strftime('%Y%m%d_%H%M%S')
        base = os.path.basename(field.name)
        safe = re.sub(r'[^a-zA-Z0-9._-]', '_', base)[:180]
        dest = f'contratos/videos_auditoria/{timezone.now():%Y/%m}/contrato_{ce.id}_{ts}_{safe}'
        default_storage.save(dest, ContentFile(blob))
    except Exception:
        logger.exception('Falha ao arquivar vídeo do contrato %s', ce.pk)
        raise
