"""Geração de campanhas SIAPE a partir de carteira, RegisterMoney e contratos."""
from datetime import datetime

from django.db import transaction

from apps.contratos_v2.models import ContratoExecucao
from apps.vendas.siape.models import CarteiraClientes, RegisterMoney

from .utils import normalizar_cpf


def listar_status_comercial_siape() -> list[dict]:
    return [
        {'value': v, 'label': l}
        for v, l in CarteiraClientes.STATUS_COMERCIAL_CHOICES
    ]


def _parse_datas(filtros: dict):
    data_inicio = datetime.strptime(filtros['data_inicio'], '%Y-%m-%d').date()
    data_fim = datetime.strptime(filtros['data_fim'], '%Y-%m-%d').date()
    if data_inicio > data_fim:
        raise ValueError('Data de início deve ser anterior à data de fim.')
    return data_inicio, data_fim


def coletar_cpfs_siape(filtros: dict) -> set[str]:
    """
    Coleta CPFs de:
    - CarteiraClientes (cliente SIAPE ou cliente_operacional contratos)
    - RegisterMoney (cpf_cliente no período)
    - ContratoExecucao vinculado à carteira via M2M
    """
    data_inicio, data_fim = _parse_datas(filtros)
    cpfs: set[str] = set()

    if filtros.get('fonte_carteira', True):
        qs = CarteiraClientes.objects.filter(
            status='ATIVO',
            data_criacao__date__range=[data_inicio, data_fim],
        ).select_related('cliente', 'cliente_operacional')
        status_list = filtros.get('status_comercial') or []
        if status_list:
            qs = qs.filter(status_comercial__in=status_list)
        responsavel_id = filtros.get('responsavel_id')
        if responsavel_id:
            qs = qs.filter(user_responsavel_id=int(responsavel_id))
        for cart in qs:
            if cart.cliente and cart.cliente.cpf:
                cpfs.add(normalizar_cpf(cart.cliente.cpf))
            elif cart.cliente_operacional and cart.cliente_operacional.cpf:
                cpfs.add(normalizar_cpf(cart.cliente_operacional.cpf))

    if filtros.get('fonte_register_money', True):
        rm_qs = RegisterMoney.objects.filter(
            status=True,
            data__date__range=[data_inicio, data_fim],
        ).exclude(cpf_cliente__in=[None, ''])
        for rm in rm_qs.values_list('cpf_cliente', flat=True).distinct():
            cpf = normalizar_cpf(rm)
            if len(cpf) == 11:
                cpfs.add(cpf)

    if filtros.get('fonte_contratos', False):
        contratos_qs = ContratoExecucao.objects.filter(
            data_criacao__date__range=[data_inicio, data_fim],
        )
        fase = filtros.get('fase_contrato')
        if fase:
            contratos_qs = contratos_qs.filter(fase=fase)
        for cpf in contratos_qs.values_list('cliente_dados_pessoais__cpf', flat=True).distinct():
            n = normalizar_cpf(cpf)
            if len(n) == 11:
                cpfs.add(n)

    return cpfs


def preview_campanha_siape(filtros: dict) -> dict:
    cpfs = coletar_cpfs_siape(filtros)
    amostra = []
    for cpf in list(cpfs)[:20]:
        from apps.vendas.siape.models import Cliente
        cli = Cliente.objects.filter(cpf=cpf).first()
        amostra.append({'cpf': cpf, 'nome': cli.nome if cli else '—'})
    return {'total': len(cpfs), 'amostra': amostra, 'cpfs': list(cpfs)}
