from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.gerenciador import (
    listar_campanhas,
    listar_clientes_campanha,
    listar_equipes,
    listar_status_choices,
)


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_equipes(request):
    return JsonResponse({'ok': True, 'equipes': listar_equipes()})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_campanhas(request):
    tipo = request.GET.get('tipo')
    return JsonResponse({'ok': True, 'campanhas': listar_campanhas(tipo)})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_status(request):
    return JsonResponse({'ok': True, 'status_choices': listar_status_choices()})


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_clientes(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)
    return JsonResponse({
        'ok': True,
        'clientes': listar_clientes_campanha(int(campanha_id)),
    })


@login_required(login_url='/')
@controle_acess('SS51')
@require_GET
def api_get_gerenciador_usuarios(request):
    users = list(
        User.objects.filter(is_active=True)
        .values('id', 'username', 'first_name', 'last_name')[:500]
    )
    return JsonResponse({'ok': True, 'usuarios': users})
