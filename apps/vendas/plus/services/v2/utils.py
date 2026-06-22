import re
from decimal import Decimal


def normalizar_cpf(cpf: str) -> str:
    digitos = re.sub(r'\D', '', cpf or '')
    if not digitos:
        return ''
    return digitos.zfill(11)[-11:]


def serializar_decimal(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def normalizar_chave_csv(chave: str) -> str:
    """Converte cabeçalho CSV para snake_case."""
    chave = (chave or '').strip().lower()
    chave = re.sub(r'[^\w\s]', '', chave)
    chave = re.sub(r'\s+', '_', chave)
    return chave


CPF_ALIASES = {'cpf', 'documento', 'doc', 'cpf_cliente'}
