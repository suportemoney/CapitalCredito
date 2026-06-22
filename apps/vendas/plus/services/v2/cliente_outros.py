def build_payload_outros(dados_json: dict | None) -> dict:
    """Retorna schema dinâmico a partir do JSON importado."""
    dados = dados_json or {}
    return {
        'encontrado': bool(dados),
        'tipo': 'OUTROS',
        'schema': 'dinamico',
        'campos': dados,
        'colunas': list(dados.keys()) if dados else [],
    }
