# -*- coding: utf-8 -*-
"""Cálculo de base AF e classificador banco para CMS (relatório + RegisterMoney).

Módulo isolado para evitar import circular com apps.contratos_v2.apis.fluxo.
"""
from decimal import Decimal


def base_af_para_cms(d):
    """
    Base monetária para cálculo CMS (flats % sobre valor).
    Precedência: valor_af_base_cms → AF × percentual_af_manual/100 → valor_af.
    Não altera o campo valor_af original.
    """
    if not d:
        return Decimal('0')
    vb = getattr(d, 'valor_af_base_cms', None)
    if vb is not None:
        try:
            return Decimal(str(vb)).quantize(Decimal('0.01'))
        except Exception:
            pass
    af_dec = d.valor_af or Decimal('0')
    pct = getattr(d, 'percentual_af_manual', None)
    if pct is not None:
        try:
            return (af_dec * (Decimal(str(pct)) / Decimal('100'))).quantize(Decimal('0.01'))
        except Exception:
            pass
    return af_dec


def classificador_banco_efetivo(d):
    """M1/M2/M3: override financeiro ou classificador da tabela CMS vinculada."""
    if not d:
        return None
    raw = getattr(d, 'classificador_banco_operacional', None)
    op = (str(raw).strip().upper() if raw is not None else '') or ''
    if op in ('M1', 'M2', 'M3'):
        return op
    if d.tabela_cms_id:
        t = d.tabela_cms.classificador_banco or 'M1'
        try:
            t = str(t).strip().upper()
        except Exception:
            t = 'M1'
        if t in ('M1', 'M2', 'M3'):
            return t
    return None
