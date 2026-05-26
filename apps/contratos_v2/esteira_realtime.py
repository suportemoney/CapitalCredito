# -*- coding: utf-8 -*-
"""Fingerprint leve para SSE da esteira (contratos/propostas/simulações + tabulações comercial/operacional)."""
from django.db.models import Max

from apps.contratos_v2.models import (
    ContratoExecucao,
    HistoricoEventoDigitacao,
    HistoricoEventoSimulacao,
    HistoricoTransicaoContrato,
)
from apps.vendas.siape.models import TabulacaoVendedor


def compute_esteira_fingerprint():
    """
    Retorna o maior timestamp de atividade relevante ou None se não houver dados.
    Inclui tabulações do Siape: ao operacional registrar propostas simuladas, cria-se TabulacaoVendedor
    sem HistoricoEventoSimulacao — sem isso o SSE não mudava o `rev` e a consulta cliente não atualizava.
    """
    datas = [
        HistoricoTransicaoContrato.objects.aggregate(Max('data'))['data__max'],
        HistoricoEventoSimulacao.objects.aggregate(Max('data'))['data__max'],
        HistoricoEventoDigitacao.objects.aggregate(Max('data'))['data__max'],
        ContratoExecucao.objects.aggregate(Max('data_ultima_atualizacao'))['data_ultima_atualizacao__max'],
        TabulacaoVendedor.objects.aggregate(Max('data_criacao'))['data_criacao__max'],
    ]
    datas = [d for d in datas if d is not None]
    return max(datas) if datas else None
