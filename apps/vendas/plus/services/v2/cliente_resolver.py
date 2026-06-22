from .cliente_outros import build_payload_outros
from .cliente_siape import build_payload_siape


def resolver_dados_cliente(cpf: str, tipo: str, dados_json: dict | None = None) -> dict:
    """Ponto único de resolução de ficha por tipo."""
    tipo = (tipo or '').upper()
    if tipo == 'SIAPE':
        return build_payload_siape(cpf)
    if tipo == 'OUTROS':
        return build_payload_outros(dados_json)
    return {'encontrado': False, 'erro': f'Tipo inválido: {tipo}'}
