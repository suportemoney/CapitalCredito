# -*- coding: utf-8 -*-
"""Classificação TC automática (stub mínimo para fluxo contratos)."""


def classificar_tc_automatico(cpf, user, dias=90):
    """Retorna dict com classificador M1/M2 e metadados."""
    return {
        'classificador': 'M1',
        'tipo': 'NOVO',
        'percentual_efetivo': 100,
    }


def obter_classificador_primeiro_rm(ce):
    """Classificador do primeiro RegisterMoney do contrato."""
    from apps.vendas.siape.models import RegisterMoney

    rm = (
        RegisterMoney.objects.filter(contrato_execucao=ce, status=True)
        .exclude(classificador_auto__isnull=True)
        .exclude(classificador_auto='')
        .order_by('id')
        .first()
    )
    if not rm:
        return None
    return rm.classificador_auto
