# -*- coding: utf-8 -*-
"""Verificação de proposta duplicada por fingerprint operacional."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from apps.contratos_v2.models import PropostaDados

MSG_PROPOSTA_JA_DIGITADA = 'Proposta Já digitada com esses dados!'


def _normalizar_decimal(valor, casas):
    """Converte valor para Decimal quantizado ou None."""
    if valor is None or valor == '':
        return None
    try:
        if isinstance(valor, Decimal):
            d = valor
        elif isinstance(valor, (int, float)):
            d = Decimal(str(valor))
        else:
            s = str(valor).strip()
            if not s:
                return None
            if ',' in s and '.' not in s:
                s = s.replace(',', '.')
            d = Decimal(s)
        if d < 0:
            return None
        q = Decimal('1').scaleb(-casas)
        return d.quantize(q, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _normalizar_prazo(valor):
    """Prazo inteiro positivo ou None."""
    if valor is None or valor == '' or valor == 0 or valor == '0':
        return None
    try:
        pv = int(Decimal(str(valor).strip().replace(',', '.')))
        return pv if pv >= 1 else None
    except Exception:
        return None


def normalizar_fingerprint_proposta(
    banco_id,
    convenio_id,
    produto_id,
    valor_parcela,
    prazo,
    coeficiente,
):
    """Retorna tupla normalizada para comparação de duplicata."""
    def _pk(v):
        if v is None or v == '':
            return None
        try:
            iv = int(v)
            return iv if iv > 0 else None
        except (TypeError, ValueError):
            return None

    return (
        _pk(banco_id),
        _pk(convenio_id),
        _pk(produto_id),
        _normalizar_decimal(valor_parcela, 2),
        _normalizar_prazo(prazo),
        _normalizar_decimal(coeficiente, 6),
    )


def proposta_ja_existe_para_cliente(
    cliente_dados_pessoais,
    banco_id,
    convenio_id,
    produto_id,
    valor_parcela,
    prazo,
    coeficiente,
) -> bool:
    """
    Verifica se já existe PropostaDados para o cliente com os mesmos 6 campos:
    Banco + Convênio + Produto + valor_parcela + prazo + coeficiente.
    """
    if not cliente_dados_pessoais:
        return False

    alvo = normalizar_fingerprint_proposta(
        banco_id, convenio_id, produto_id, valor_parcela, prazo, coeficiente,
    )
    if alvo[0] is None or alvo[1] is None or alvo[2] is None:
        return False

    existentes = PropostaDados.objects.filter(
        cliente_dados_pessoais=cliente_dados_pessoais,
        banco_id=alvo[0],
        convenio_id=alvo[1],
        produto_id=alvo[2],
    ).only(
        'valor_parcela', 'prazo', 'coeficiente',
    )

    for pd in existentes:
        existente_tail = (
            _normalizar_decimal(pd.valor_parcela, 2),
            _normalizar_prazo(pd.prazo),
            _normalizar_decimal(pd.coeficiente, 6),
        )
        if existente_tail == alvo[3:]:
            return True
    return False
