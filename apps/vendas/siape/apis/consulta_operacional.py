# -*- coding: utf-8 -*-
"""APIs da consulta SIAPE integradas ao fluxo operacional (apps.contratos_v2)."""
import json
import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.contratos_v2.fluxo_constants import EstadoSolicitacaoProposta
from apps.contratos_v2.models import PropostaDados, SolicitacaoPropostaCliente
from apps.contratos_v2.permissoes_codigos import COD_CX_NOVO_CONTRATO
from apps.seguranca.permissoes.utils import user_has_access
from apps.vendas.siape.models import CarteiraClientes, Cliente
from apps.vendas.siape.services.carteira_operacional import get_or_create_carteira
from apps.vendas.siape.services.container_novo_contrato import (
    montar_container_novo_contrato,
    montar_container_todas_propostas,
)


def _norm_cpf(cpf):
    d = re.sub(r'\D', '', str(cpf or ''))
    if not d:
        return None
    if len(d) < 11:
        d = d.zfill(11)
    return d[:11] if len(d) >= 11 else None


@login_required
@require_GET
def api_carteira_por_cpf(request):
    """Resolve ou cria carteira do vendedor para o CPF informado."""
    cpf = _norm_cpf(request.GET.get('cpf'))
    if not cpf:
        return JsonResponse({'ok': False, 'message': 'CPF inválido.'}, status=400)
    cliente = Cliente.objects.filter(cpf=cpf, status=True).first()
    if not cliente:
        return JsonResponse({'ok': False, 'message': 'Cliente não encontrado.'}, status=404)
    carteira, criada = get_or_create_carteira(cliente, request.user)
    return JsonResponse({
        'ok': True,
        'carteira_id': carteira.id,
        'status_comercial': carteira.status_comercial or 'EM_NEGOCIACAO',
        'tag_status_operacional': carteira.tag_status_operacional or '',
        'criada': criada,
    })


@login_required
@require_GET
def api_get_simulacoes(request):
    """Solicitações de simulação da carteira (card lateral na consulta)."""
    try:
        cid = int(request.GET.get('carteira_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'sucesso', 'itens': []})
    if not cid:
        return JsonResponse({'status': 'sucesso', 'itens': []})
    carteira = CarteiraClientes.objects.filter(
        pk=cid, user_responsavel=request.user
    ).first()
    if not carteira:
        return JsonResponse({'status': 'sucesso', 'itens': []})
    qs = (
        SolicitacaoPropostaCliente.objects.filter(carteira_clientes=carteira)
        .select_related('cliente_dados_pessoais')
        .order_by('-data_criacao')[:50]
    )
    itens = []
    for sol in qs:
        itens.append({
            'id': sol.id,
            'estado': sol.estado,
            'data_criacao': sol.data_criacao.isoformat() if sol.data_criacao else '',
            'cliente_nome': (
                sol.cliente_dados_pessoais.nome_completo if sol.cliente_dados_pessoais_id else ''
            ),
        })
    return JsonResponse({'status': 'sucesso', 'itens': itens})


@login_required
@require_GET
def api_get_operacional(request):
    """Propostas operacionais vinculadas à carteira."""
    try:
        cid = int(request.GET.get('carteira_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'sucesso', 'itens': []})
    if not cid:
        return JsonResponse({'status': 'sucesso', 'itens': []})
    carteira = CarteiraClientes.objects.filter(
        pk=cid, user_responsavel=request.user
    ).first()
    if not carteira:
        return JsonResponse({'status': 'sucesso', 'itens': []})

    cliente_dp_raw = (request.GET.get('cliente_dados_pessoais_id') or '').strip()
    try:
        cliente_dp_param = int(cliente_dp_raw) if cliente_dp_raw else None
    except (TypeError, ValueError):
        cliente_dp_param = None

    cliente_dp = cliente_dp_param or carteira.cliente_operacional_id
    if cliente_dp:
        propostas = (
            PropostaDados.objects.filter(cliente_dados_pessoais_id=cliente_dp)
            .select_related('banco', 'convenio', 'produto')
            .order_by('-data_criacao')[:100]
        )
    else:
        propostas = (
            PropostaDados.objects.filter(carteiras_siape_propostas=carteira)
            .select_related('banco', 'convenio', 'produto')
            .order_by('-data_criacao')[:100]
        )
    itens = []
    for pd in propostas:
        itens.append({
            'id': pd.id,
            'codigo': pd.codigo or '',
            'banco': pd.banco.titulo if pd.banco_id else '',
            'produto': pd.produto.titulo if pd.produto_id else '',
            'banco_id': pd.banco_id,
            'convenio_id': pd.convenio_id,
            'produto_id': pd.produto_id,
            'valor_parcela': str(pd.valor_parcela) if pd.valor_parcela is not None else '',
            'prazo': pd.prazo,
            'coeficiente': str(pd.coeficiente) if pd.coeficiente is not None else '',
            'valor_af': str(pd.valor_af) if pd.valor_af is not None else '',
            'aceita_pelo_cliente': bool(pd.aceita_pelo_cliente),
            'data_criacao': pd.data_criacao.isoformat() if pd.data_criacao else '',
        })
    return JsonResponse({'status': 'sucesso', 'itens': itens})


@login_required
@require_GET
def api_get_container_novo_contrato(request):
    """Container compacto operacional na consulta SIAPE (CX48)."""
    if not user_has_access(request.user, COD_CX_NOVO_CONTRATO):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão (CX48).'}, status=403)
    raw_cid = (request.GET.get('carteira_id') or '').strip()
    if not raw_cid:
        return JsonResponse(montar_container_todas_propostas(request.user))
    try:
        cid = int(raw_cid)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'carteira_id inválido.'}, status=400)
    if not cid:
        return JsonResponse(montar_container_todas_propostas(request.user))
    carteira = CarteiraClientes.objects.filter(
        pk=cid, user_responsavel=request.user
    ).select_related('cliente').first()
    if not carteira:
        return JsonResponse({'ok': False, 'erro': 'Carteira não encontrada.'}, status=404)
    return JsonResponse(montar_container_novo_contrato(carteira, request.user))
