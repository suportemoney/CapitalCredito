from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.models import StatusChoice
from apps.vendas.plus.services.v2.distribuicao import (
    campanhas_do_usuario,
    carregar_controle,
    cliente_pendente_usuario,
    listar_agendamentos_usuario,
    listar_historico_usuario,
    proximo_cliente,
)
from apps.vendas.plus.services.v2.esteira_kpis import build_esteira_kpis


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_campanhas(request):
    campanhas = campanhas_do_usuario(request.user)
    return JsonResponse({
        'ok': True,
        'campanhas': [
            {'id': c.id, 'nome': c.nome, 'tipo_campanha': c.tipo_campanha}
            for c in campanhas
        ],
    })


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_proximo_cliente(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)

    solicitar_novo = request.GET.get('novo') in ('1', 'true', 'True')
    resultado = proximo_cliente(request.user, int(campanha_id), solicitar_novo=solicitar_novo)

    if not resultado:
        return JsonResponse({'ok': True, 'cliente': None, 'mensagem': 'Nenhum cliente disponível.'})

    if resultado.get('_bloqueio'):
        return JsonResponse({
            'ok': False,
            'bloqueado': True,
            'erro': resultado.get('mensagem'),
            'cliente': resultado.get('cliente'),
        }, status=409)

    return JsonResponse({'ok': True, 'cliente': resultado})


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_pendente(request):
    campanha_id = request.GET.get('campanha_id')
    if not campanha_id:
        return JsonResponse({'ok': False, 'erro': 'campanha_id obrigatório.'}, status=400)

    cliente = cliente_pendente_usuario(request.user, int(campanha_id))
    return JsonResponse({'ok': True, 'cliente': cliente})


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_historico(request):
    campanha_id = request.GET.get('campanha_id')
    cid = int(campanha_id) if campanha_id else None
    return JsonResponse({
        'ok': True,
        'historico': listar_historico_usuario(request.user, cid),
    })


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_controle(request):
    controle_id = request.GET.get('controle_id')
    if not controle_id:
        return JsonResponse({'ok': False, 'erro': 'controle_id obrigatório.'}, status=400)

    cliente = carregar_controle(request.user, int(controle_id))
    if not cliente:
        return JsonResponse({'ok': False, 'erro': 'Controle não encontrado.'}, status=404)

    return JsonResponse({'ok': True, 'cliente': cliente})


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_kpis(request):
    campanha_id = request.GET.get('campanha_id')
    cid = int(campanha_id) if campanha_id else None
    return JsonResponse({'ok': True, 'kpis': build_esteira_kpis(request.user, cid)})


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_agendamentos(request):
    campanha_id = request.GET.get('campanha_id')
    cid = int(campanha_id) if campanha_id else None
    return JsonResponse({
        'ok': True,
        'agendamentos': listar_agendamentos_usuario(request.user, cid),
    })


@login_required(login_url='/')
@controle_acess('SS50')
@require_GET
def api_get_esteira_status_choices(request):
    status = list(
        StatusChoice.objects.filter(status_booleano=True)
        .order_by('order', 'nome')
        .values('id', 'nome', 'cor_tag', 'impacto', 'conversao')
    )
    return JsonResponse({'ok': True, 'status_choices': status})
