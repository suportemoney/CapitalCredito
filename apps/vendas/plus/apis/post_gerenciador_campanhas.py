import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.campanha_factory import criar_campanha_siape_com_cpfs
from apps.vendas.plus.services.v2.csv_cpfs import extrair_cpfs_csv
from apps.vendas.plus.services.v2.preview_cpf_campanha import preview_cpfs_siape


def _preview_csv_campanha(request):
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Arquivo CSV obrigatório.'}, status=400)

    extraido = extrair_cpfs_csv(arquivo.read())
    if not extraido.get('ok'):
        return JsonResponse(extraido, status=400)

    cpfs = extraido['cpfs']
    preview = preview_cpfs_siape(cpfs)

    return JsonResponse({
        'ok': True,
        'invalidos_csv': extraido.get('invalidos', 0),
        **preview,
    })


def _criar_campanha_csv(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    nome = (data.get('nome') or '').strip()
    equipes_ids = data.get('equipes_ids') or []
    cpfs = data.get('cpfs') or []

    if not nome:
        return JsonResponse({'ok': False, 'erro': 'Nome da campanha obrigatório.'}, status=400)
    if not equipes_ids:
        return JsonResponse({'ok': False, 'erro': 'Selecione ao menos uma equipe.'}, status=400)
    if not cpfs:
        return JsonResponse({'ok': False, 'erro': 'Nenhum CPF para criar a campanha.'}, status=400)

    resultado = criar_campanha_siape_com_cpfs(nome, cpfs, equipes_ids)
    return JsonResponse({'ok': True, **resultado})


@login_required(login_url='/')
@controle_acess('SS49')
@require_POST
def api_post_gerenciador_siape_preview(request):
    return _preview_csv_campanha(request)


@login_required(login_url='/')
@controle_acess('SS49')
@require_POST
def api_post_gerenciador_siape_criar(request):
    return _criar_campanha_csv(request)
