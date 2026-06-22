from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.gerenciador_overview import (
    build_gerenciador_kpis,
    detalhes_campanha,
    listar_campanhas_enriquecidas,
    listar_clientes_campanha_detalhe,
    proximos_agendamentos_campanha,
    ultima_importacao_campanha,
)


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_kpis(request):
    tipo = request.GET.get('tipo')
    return JsonResponse({'ok': True, 'kpis': build_gerenciador_kpis(tipo)})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_campanha_detalhe(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)
    detalhe = detalhes_campanha(int(campanha_id))
    if not detalhe:
        return JsonResponse({'ok': False, 'erro': 'Campanha não encontrada.'}, status=404)
    return JsonResponse({'ok': True, 'detalhe': detalhe})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_ultima_importacao(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)
    imp = ultima_importacao_campanha(int(campanha_id))
    return JsonResponse({'ok': True, 'importacao': imp})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_agendamentos_campanha(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)
    return JsonResponse({
        'ok': True,
        'agendamentos': proximos_agendamentos_campanha(int(campanha_id)),
    })


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_campanhas_enriquecidas(request):
    tipo = request.GET.get('tipo')
    return JsonResponse({'ok': True, 'campanhas': listar_campanhas_enriquecidas(tipo)})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_clientes_detalhe(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)
    return JsonResponse({
        'ok': True,
        'clientes': listar_clientes_campanha_detalhe(int(campanha_id)),
    })
