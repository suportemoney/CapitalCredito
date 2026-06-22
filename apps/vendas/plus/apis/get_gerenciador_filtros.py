from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.gerador_siape import listar_status_comercial_siape


@login_required(login_url='/')
@controle_acess('SS49')
@require_GET
def api_get_gerenciador_siape_filtros(request):
    from apps.contratos_v2.fluxo_constants import FaseContratoExecucao
    fases = [{'value': v, 'label': l} for v, l in FaseContratoExecucao.CHOICES]
    return JsonResponse({
        'ok': True,
        'status_comercial': listar_status_comercial_siape(),
        'fases_contrato': fases,
    })
