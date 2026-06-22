from django.db.models import Q

from apps.contratos_v2.models import ContratoExecucao
from apps.vendas.siape.models import CarteiraClientes, Cliente, RegisterMoney

from .utils import normalizar_cpf, serializar_decimal

BATCH_SIZE = 100
PREVIEW_ITENS_LIMITE = 20


def _formatar_data(valor) -> str | None:
    if not valor:
        return None
    return valor.isoformat() if hasattr(valor, 'isoformat') else str(valor)


def _nome_siape(cliente, carteira) -> str:
    if cliente and cliente.nome:
        return cliente.nome
    if carteira and carteira.cliente_operacional:
        return carteira.cliente_operacional.nome_completo or '—'
    return '—'


def _preview_cpfs_siape_bulk(cpfs: list[str]) -> dict:
    """Consulta CPFs SIAPE em lote (evita N+1)."""
    cpfs_n = [normalizar_cpf(c) for c in cpfs]
    cpf_set = set(cpfs_n)

    clientes = {c.cpf: c for c in Cliente.objects.filter(cpf__in=cpf_set)}

    carteiras: dict[str, CarteiraClientes] = {}
    if cpf_set:
        for cart in (
            CarteiraClientes.objects.filter(status='ATIVO')
            .filter(Q(cliente__cpf__in=cpf_set) | Q(cliente_operacional__cpf__in=cpf_set))
            .select_related('cliente', 'cliente_operacional')
            .order_by('-data_criacao')
        ):
            for cpf_key in (
                cart.cliente.cpf if cart.cliente_id and cart.cliente else None,
                cart.cliente_operacional.cpf if cart.cliente_operacional_id and cart.cliente_operacional else None,
            ):
                if cpf_key in cpf_set and cpf_key not in carteiras:
                    carteiras[cpf_key] = cart

    rm_map: dict[str, RegisterMoney] = {}
    if cpf_set:
        for rm in RegisterMoney.objects.filter(cpf_cliente__in=cpf_set, status=True).order_by('-data'):
            if rm.cpf_cliente not in rm_map:
                rm_map[rm.cpf_cliente] = rm

    contrato_map: dict[str, ContratoExecucao] = {}
    if cpf_set:
        for contrato in (
            ContratoExecucao.objects.filter(cliente_dados_pessoais__cpf__in=cpf_set)
            .select_related('cliente_dados_pessoais')
            .order_by('-data_criacao')
        ):
            cpf = contrato.cliente_dados_pessoais.cpf if contrato.cliente_dados_pessoais_id else None
            if cpf and cpf not in contrato_map:
                contrato_map[cpf] = contrato

    itens = []
    encontrados = 0
    for cpf_n in cpfs_n:
        cliente = clientes.get(cpf_n)
        carteira = carteiras.get(cpf_n)
        rm = rm_map.get(cpf_n)
        contrato = contrato_map.get(cpf_n)
        tem_fonte = bool(cliente or carteira or rm or contrato)
        if tem_fonte:
            encontrados += 1
        itens.append({
            'cpf': cpf_n,
            'encontrado': tem_fonte,
            'nome': _nome_siape(cliente, carteira),
            'carteira': carteira.get_status_comercial_display() if carteira else '—',
            'register_money': (
                f"{_formatar_data(rm.data)} / R$ {serializar_decimal(rm.valor_est) or 0}"
                if rm else '—'
            ),
            'contrato': contrato.get_fase_display() if contrato else '—',
        })

    return {
        'itens': itens,
        'total': len(itens),
        'encontrados': encontrados,
        'nao_encontrados': len(itens) - encontrados,
        'cpfs': [i['cpf'] for i in itens],
    }


def preview_cpfs_siape(cpfs: list[str]) -> dict:
    if not cpfs:
        return {'itens': [], 'total': 0, 'encontrados': 0, 'nao_encontrados': 0, 'cpfs': []}
    if len(cpfs) <= BATCH_SIZE:
        return _preview_cpfs_siape_bulk(cpfs)

    itens = []
    encontrados = 0
    cpfs_ok: list[str] = []
    for i in range(0, len(cpfs), BATCH_SIZE):
        lote = _preview_cpfs_siape_bulk(cpfs[i:i + BATCH_SIZE])
        encontrados += lote['encontrados']
        cpfs_ok.extend(lote['cpfs'])
        if len(itens) < PREVIEW_ITENS_LIMITE:
            itens.extend(lote['itens'][:PREVIEW_ITENS_LIMITE - len(itens)])

    return {
        'itens': itens,
        'total': len(cpfs),
        'encontrados': encontrados,
        'nao_encontrados': len(cpfs) - encontrados,
        'cpfs': cpfs_ok,
    }


def iter_preview_cpfs(cpfs: list[str], tipo: str):
    """Gera eventos de progresso e resultado final para SSE."""
    total = len(cpfs)
    if total == 0:
        yield {'evento': 'complete', 'ok': True, 'itens': [], 'total': 0, 'encontrados': 0, 'nao_encontrados': 0, 'cpfs': []}
        return

    if tipo != 'SIAPE':
        yield {'evento': 'error', 'ok': False, 'erro': f'Tipo de campanha não suportado: {tipo}'}
        return

    encontrados_total = 0
    itens_preview: list[dict] = []
    cpfs_ok: list[str] = []

    yield {'evento': 'progress', 'processados': 0, 'total': total, 'encontrados': 0, 'nao_encontrados': 0}

    for i in range(0, total, BATCH_SIZE):
        lote = _preview_cpfs_siape_bulk(cpfs[i:i + BATCH_SIZE])
        encontrados_total += lote['encontrados']
        cpfs_ok.extend(lote['cpfs'])
        if len(itens_preview) < PREVIEW_ITENS_LIMITE:
            itens_preview.extend(lote['itens'][:PREVIEW_ITENS_LIMITE - len(itens_preview)])

        yield {
            'evento': 'progress',
            'processados': min(i + BATCH_SIZE, total),
            'total': total,
            'encontrados': encontrados_total,
            'nao_encontrados': len(cpfs_ok) - encontrados_total,
        }

    yield {
        'evento': 'complete',
        'ok': True,
        'itens': itens_preview,
        'total': total,
        'encontrados': encontrados_total,
        'nao_encontrados': total - encontrados_total,
        'cpfs': cpfs_ok,
    }
