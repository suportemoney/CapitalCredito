from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.csv_import import confirmar_importacao_csv, parse_csv_preview


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_importacao_csv_preview(request):
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Arquivo CSV obrigatório.'}, status=400)

    conteudo = arquivo.read()
    preview = parse_csv_preview(conteudo)
    if not preview.get('ok'):
        return JsonResponse(preview, status=400)

    return JsonResponse(preview)


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_importacao_csv_confirmar(request):
    arquivo = request.FILES.get('arquivo')
    campanha_id = request.POST.get('campanha_id')
    if not arquivo or not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'arquivo e campanha_id obrigatórios.'}, status=400)

    resultado = confirmar_importacao_csv(
        int(campanha_id),
        arquivo.read(),
        arquivo.name,
        request.user,
    )
    if not resultado.get('ok'):
        return JsonResponse(resultado, status=400)

    return JsonResponse(resultado)
