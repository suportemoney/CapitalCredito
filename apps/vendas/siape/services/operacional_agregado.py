# -*- coding: utf-8 -*-
"""Sincronização de campos agregados na carteira (tabulação operacional)."""


def sincronizar_agregado_operacional(carteira):
    """Atualiza tags agregadas na carteira; implementação mínima para o fluxo v2."""
    if not carteira:
        return
    # Campos já são atualizados em _registrar_tabulacao no fluxo contratos.
    return
