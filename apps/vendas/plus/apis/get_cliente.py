
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.models_v2 import ClienteCampanhaV2
from apps.vendas.plus.services.v2.cliente_resolver import resolver_dados_cliente
from apps.vendas.plus.services.v2.utils import normalizar_cpf


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_cliente_ficha(request):
    """Retorna ficha resolvida por CPF e tipo."""
    cpf = request.GET.get('cpf', '')
    tipo = request.GET.get('tipo', '').upper()
    cliente_id = request.GET.get('cliente_id')

    dados_json = None
    if cliente_id:
        ref = ClienteCampanhaV2.objects.filter(pk=cliente_id).first()
        if ref:
            cpf = ref.cpf
            tipo = ref.tipo
            dados_json = ref.dados_json

    cpf_n = normalizar_cpf(cpf)
    if not cpf_n or not tipo:
        return JsonResponse({'ok': False, 'erro': 'CPF e tipo são obrigatórios.'}, status=400)

    ficha = resolver_dados_cliente(cpf_n, tipo, dados_json)
    return JsonResponse({'ok': True, 'cpf': cpf_n, 'tipo': tipo, 'ficha': ficha})
