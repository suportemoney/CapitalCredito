import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.gerenciador import (
    adicionar_clientes_campanha,
    alterar_status_campanha,
    atualizar_campanha,
    atualizar_equipe,
    criar_campanha,
    criar_equipe,
)


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_gerenciador_campanha(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    nome = data.get('nome', '').strip()
    if not nome:
        return JsonResponse({'ok': False, 'erro': 'Nome obrigatório.'}, status=400)

    campanha = criar_campanha(data)
    return JsonResponse({'ok': True, 'campanha_id': campanha.id})


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_gerenciador_equipe(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    nome = data.get('nome', '').strip()
    if not nome:
        return JsonResponse({'ok': False, 'erro': 'Nome obrigatório.'}, status=400)

    equipe = criar_equipe(nome, data.get('participantes_ids', []))
    return JsonResponse({'ok': True, 'equipe_id': equipe.id})


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_gerenciador_equipe_atualizar(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    equipe_id = data.get('equipe_id')
    if not equipe_id:
        return JsonResponse({'ok': False, 'erro': 'equipe_id obrigatório.'}, status=400)

    nome = data.get('nome')
    if nome is not None and not str(nome).strip():
        return JsonResponse({'ok': False, 'erro': 'Nome da equipe inválido.'}, status=400)

    equipe = atualizar_equipe(
        int(equipe_id),
        nome=nome.strip() if nome is not None else None,
        status=data.get('status') if 'status' in data else None,
        participantes_ids=data.get('participantes_ids'),
    )
    if not equipe:
        return JsonResponse({'ok': False, 'erro': 'Equipe não encontrada.'}, status=404)
    return JsonResponse({'ok': True, 'equipe_id': equipe.id})


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_gerenciador_campanha_status(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    campanha_id = data.get('campanha_id')
    status = data.get('status', True)
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)

    ok = alterar_status_campanha(int(campanha_id), bool(status))
    return JsonResponse({'ok': ok})


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_gerenciador_campanha_atualizar(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    campanha_id = data.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)

    nome = data.get('nome')
    if nome is not None and not str(nome).strip():
        return JsonResponse({'ok': False, 'erro': 'Nome da campanha inválido.'}, status=400)

    campanha = atualizar_campanha(
        int(campanha_id),
        {
            'nome': nome.strip() if nome is not None else None,
            'descricao': data.get('descricao'),
            'equipes_ids': data.get('equipes_ids'),
        },
    )
    if not campanha:
        return JsonResponse({'ok': False, 'erro': 'Campanha não encontrada.'}, status=404)
    return JsonResponse({'ok': True, 'campanha_id': campanha.id})


@login_required(login_url='/')
@controle_acess('SS51')
@require_POST
def api_post_gerenciador_clientes(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    campanha_id = data.get('campanha_id')
    clientes = data.get('clientes', [])
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)

    resultado = adicionar_clientes_campanha(int(campanha_id), clientes)
    return JsonResponse({'ok': True, **resultado})
