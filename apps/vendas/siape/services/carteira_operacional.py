# -*- coding: utf-8 -*-
"""Vínculo entre carteira SIAPE e propostas/contratos operacionais."""
from apps.vendas.siape.models import CarteiraClientes, Cliente


def get_or_create_carteira(cliente, user):
    """
    Obtém ou cria carteira ativa do vendedor para o cliente SIAPE.
    """
    if isinstance(cliente, int):
        cliente = Cliente.objects.get(pk=cliente)
    carteira = (
        CarteiraClientes.objects.filter(
            cliente=cliente,
            user_responsavel=user,
            status='ATIVO',
        )
        .order_by('-id')
        .first()
    )
    if carteira:
        return carteira, False
    carteira = CarteiraClientes.objects.create(
        cliente=cliente,
        user_responsavel=user,
        status='ATIVO',
        status_comercial='EM_NEGOCIACAO',
    )
    return carteira, True


def adicionar_proposta_operacional_na_carteira(carteira, proposta_dados):
    """Garante M2M propostas_operacionais na carteira."""
    if not carteira or not proposta_dados:
        return
    carteira.propostas_operacionais.add(proposta_dados)
