# -*- coding: utf-8 -*-
"""APIs do Dashboard Operacional — KPIs, produção e pendências com histórico técnico."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.contratos_v2.apis.fluxo import (
    _build_fila_unificada_itens,
    _esteira_calcular_kpis,
    _esteira_filtrar_itens,
    _esteira_filtros_from_request,
    _esteira_mes_calendario_bounds,
    _esteira_periodo_bounds,
    _esteira_solicitantes_opcoes,
)
from apps.contratos_v2.fluxo_constants import EtapaOperacional
from apps.contratos_v2.models import (
    HistoricoTransacaoContrato,
    HistoricoTransacaoProposta,
    HistoricoTransacaoSimulacao,
    Pendencia,
)
from apps.contratos_v2.permissoes_codigos import COD_SS_ESTEIRA
from apps.seguranca.permissoes.decorators import controle_acess


def _periodo_efetivo(filtros):
    periodo = filtros.get('periodo') or 'mes_atual'
    inicio, fim = _esteira_periodo_bounds(periodo)
    if inicio is None or fim is None:
        inicio, fim = _esteira_mes_calendario_bounds(0)
    return periodo, inicio, fim


def _contrato_passa_filtros_catalogo(contrato, filtros):
    """Filtra contrato por banco/convênio/produto/solicitante."""
    pd = getattr(contrato, 'proposta_dados', None)
    do = getattr(contrato, 'dados_operacionais', None)
    banco_id = None
    convenio_id = None
    produto_id = None
    solicitante_id = None
    if do:
        banco_id = do.banco_id
        convenio_id = do.convenio_id
        produto_id = do.produto_id
    elif pd:
        banco_id = pd.banco_id
        convenio_id = pd.convenio_id
        produto_id = pd.produto_id
    if pd and getattr(pd, 'solicitacao_origem', None):
        solicitante_id = pd.solicitacao_origem.criado_por_id
    elif contrato.solicitacao_digitacao_id:
        sd = contrato.solicitacao_digitacao
        solicitante_id = sd.criado_por_id if sd else None
    if filtros.get('banco_id') and banco_id != filtros['banco_id']:
        return False
    if filtros.get('convenio_id') and convenio_id != filtros['convenio_id']:
        return False
    if filtros.get('produto_id') and produto_id != filtros['produto_id']:
        return False
    if filtros.get('solicitante_id') and solicitante_id != filtros['solicitante_id']:
        return False
    return True


def _pendencias_abertas_atuais(filtros):
    """Pendências tipadas abertas + contratos na etapa PENDENCIAS (estado atual)."""
    qs = Pendencia.objects.filter(resolvido=False).select_related(
        'contrato_execucao',
        'contrato_execucao__proposta_dados',
        'contrato_execucao__dados_operacionais',
        'contrato_execucao__solicitacao_digitacao',
    )
    resultado = []
    vistos = set()
    for p in qs:
        ce = p.contrato_execucao
        if ce.id in vistos:
            continue
        if not _contrato_passa_filtros_catalogo(ce, filtros):
            continue
        vistos.add(ce.id)
        resultado.append({
            'contrato_id': ce.id,
            'tipo': p.tipo,
            'tipo_label': p.get_tipo_display(),
            'criado_em': p.criado_em,
            'origem': 'pendencia_tipada',
        })

    from apps.contratos_v2.models import ContratoExecucao
    ce_qs = ContratoExecucao.objects.filter(
        etapa_operacional=EtapaOperacional.PENDENCIAS,
        status=True,
    ).exclude(id__in=vistos).select_related(
        'proposta_dados',
        'dados_operacionais',
        'solicitacao_digitacao',
    )
    for ce in ce_qs:
        if not _contrato_passa_filtros_catalogo(ce, filtros):
            continue
        resultado.append({
            'contrato_id': ce.id,
            'tipo': 'ETAPA_PENDENCIAS',
            'tipo_label': 'Etapa pendências',
            'criado_em': ce.data_ultima_atualizacao or ce.data_criacao,
            'origem': 'etapa_atual',
        })
    return resultado


def _montar_por_tipo_e_aging(itens_pendencia):
    por_tipo = {}
    aging = {'0-3 dias': 0, '4-7 dias': 0, '8-15 dias': 0, '16+ dias': 0}
    agora = timezone.now()
    for item in itens_pendencia:
        tipo = item.get('tipo_label') or item.get('tipo') or 'Outros'
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        dt = item.get('criado_em')
        if dt:
            dias = (agora - dt).days
            if dias <= 3:
                aging['0-3 dias'] += 1
            elif dias <= 7:
                aging['4-7 dias'] += 1
            elif dias <= 15:
                aging['8-15 dias'] += 1
            else:
                aging['16+ dias'] += 1
    return (
        [{'tipo': k, 'total': v} for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])],
        [{'faixa': k, 'total': v} for k, v in aging.items()],
    )


def _pendencias_do_historico(filtros, inicio, fim):
    """Eventos de pendência no histórico técnico dentro do período."""
    acoes = (
        HistoricoTransacaoContrato.ACAO_PENDENCIA_ABERTA,
        HistoricoTransacaoContrato.ACAO_ENTRADA_PENDENCIAS,
    )
    qs = HistoricoTransacaoContrato.objects.filter(
        acao__in=acoes,
        data_hora__gte=inicio,
        data_hora__lt=fim,
    ).select_related('contrato', 'pendencia', 'contrato__proposta_dados', 'contrato__dados_operacionais')

    itens = []
    vistos = set()
    for evt in qs.order_by('-data_hora'):
        ce = evt.contrato
        chave = (ce.id, evt.pendencia_id or evt.acao)
        if chave in vistos:
            continue
        if not _contrato_passa_filtros_catalogo(ce, filtros):
            continue
        vistos.add(chave)
        tipo = 'ETAPA_PENDENCIAS'
        tipo_label = 'Entrada em pendências'
        criado_em = evt.data_hora
        if evt.pendencia_id:
            tipo = evt.pendencia.tipo
            tipo_label = evt.pendencia.get_tipo_display()
            criado_em = evt.pendencia.criado_em or evt.data_hora
        itens.append({
            'contrato_id': ce.id,
            'tipo': tipo,
            'tipo_label': tipo_label,
            'criado_em': criado_em,
            'origem': 'historico',
        })
    return itens


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_dashboard_visao_geral(request):
    """KPIs gerais — reutiliza esteira-resumo + contagem do histórico técnico no período."""
    filtros = _esteira_filtros_from_request(request)
    periodo, inicio, fim = _periodo_efetivo(filtros)
    filtros['periodo'] = periodo

    todos = _build_fila_unificada_itens()
    filtrados = _esteira_filtrar_itens(todos, filtros, aplicar_periodo=True)
    filtros_sem_periodo = dict(filtros)
    filtros_sem_periodo['periodo'] = None
    base_variacao = _esteira_filtrar_itens(todos, filtros_sem_periodo, aplicar_periodo=False)
    kpis = _esteira_calcular_kpis(filtrados, base_variacao)

    eventos_periodo = (
        HistoricoTransacaoContrato.objects.filter(data_hora__gte=inicio, data_hora__lt=fim).count()
        + HistoricoTransacaoProposta.objects.filter(data_hora__gte=inicio, data_hora__lt=fim).count()
        + HistoricoTransacaoSimulacao.objects.filter(data_hora__gte=inicio, data_hora__lt=fim).count()
    )

    return JsonResponse({
        'ok': True,
        'kpis': kpis,
        'eventos_historico_periodo': eventos_periodo,
        'periodo': periodo,
        'solicitantes': _esteira_solicitantes_opcoes(todos),
    })


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_dashboard_esteira(request):
    """Distribuição por etapa na fila filtrada."""
    filtros = _esteira_filtros_from_request(request)
    periodo, _, _ = _periodo_efetivo(filtros)
    filtros['periodo'] = periodo
    todos = _build_fila_unificada_itens()
    filtrados = _esteira_filtrar_itens(todos, filtros, aplicar_periodo=True)
    por_etapa = {}
    for it in filtrados:
        etapa = it.get('etapa') or 'OUTROS'
        por_etapa[etapa] = por_etapa.get(etapa, 0) + 1
    return JsonResponse({
        'ok': True,
        'por_etapa': [{'etapa': k, 'total': v} for k, v in sorted(por_etapa.items(), key=lambda x: -x[1])],
        'total': len(filtrados),
    })


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_dashboard_producao(request):
    """Produção no período — histórico técnico ou fila atual como fallback."""
    filtros = _esteira_filtros_from_request(request)
    periodo, inicio, fim = _periodo_efetivo(filtros)
    filtros['periodo'] = periodo

    fonte = 'historico'
    contratos_hist = HistoricoTransacaoContrato.objects.filter(
        acao=HistoricoTransacaoContrato.ACAO_CRIACAO,
        data_hora__gte=inicio,
        data_hora__lt=fim,
    ).count()
    propostas_hist = HistoricoTransacaoProposta.objects.filter(
        acao=HistoricoTransacaoProposta.ACAO_CRIACAO,
        data_hora__gte=inicio,
        data_hora__lt=fim,
    ).count()
    simulacoes_hist = HistoricoTransacaoSimulacao.objects.filter(
        acao=HistoricoTransacaoSimulacao.ACAO_CRIACAO,
        data_hora__gte=inicio,
        data_hora__lt=fim,
    ).count()

    if contratos_hist == 0 and propostas_hist == 0 and simulacoes_hist == 0:
        fonte = 'atual'
        todos = _build_fila_unificada_itens()
        filtrados = _esteira_filtrar_itens(todos, filtros, aplicar_periodo=True)
        contratos_hist = sum(1 for it in filtrados if it.get('tipo') == 'contrato')
        propostas_hist = sum(1 for it in filtrados if it.get('tipo') == 'solicitacao_dig')
        simulacoes_hist = sum(1 for it in filtrados if it.get('tipo') == 'simulacao')

    return JsonResponse({
        'ok': True,
        'fonte_dados': fonte,
        'contratos': contratos_hist,
        'propostas': propostas_hist,
        'simulacoes': simulacoes_hist,
        'periodo': periodo,
    })


@login_required
@require_GET
@controle_acess(COD_SS_ESTEIRA)
def api_dashboard_pendencias(request):
    """Pendências por tipo e aging — histórico no período ou estado atual."""
    try:
        filtros = _esteira_filtros_from_request(request)
        periodo, inicio, fim = _periodo_efetivo(filtros)

        itens_hist = _pendencias_do_historico(filtros, inicio, fim)
        fonte = 'historico' if itens_hist else 'atual'

        if itens_hist:
            itens = itens_hist
        else:
            itens = _pendencias_abertas_atuais(filtros)

        por_tipo, aging = _montar_por_tipo_e_aging(itens)
        total = len(itens)
        sem_pendencias = total == 0

        return JsonResponse({
            'ok': True,
            'fonte_dados': fonte,
            'periodo': periodo,
            'por_tipo': por_tipo,
            'aging': aging,
            'total_abertas': total,
            'sem_pendencias': sem_pendencias,
            'mensagem': 'Nenhuma pendência aberta no momento.' if sem_pendencias else None,
        })
    except Exception as exc:
        return JsonResponse({
            'ok': False,
            'erro': f'Erro ao carregar pendências: {exc}',
            'por_tipo': [],
            'aging': [],
            'total_abertas': 0,
            'sem_pendencias': True,
            'mensagem': 'Nenhuma pendência encontrada.',
        }, status=200)
