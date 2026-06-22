from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.equipe_filtros import listar_filtros_equipe_participantes


@login_required(login_url='/')
@controle_acess('SS49')
@require_GET
def api_get_gerenciador_equipe_filtros(request):
    dados = listar_filtros_equipe_participantes()
    return JsonResponse({'ok': True, **dados})
