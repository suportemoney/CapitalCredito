import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.models import StatusChoice
from apps.vendas.plus.models_v2 import AgendamentoV2, ControleClienteV2


@login_required(login_url='/')
@controle_acess('SS50')
@require_POST
def api_post_esteira_tabulacao(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    controle_id = data.get('controle_id')
    status_id = data.get('status_id')
    if not controle_id or not status_id:
        return JsonResponse({'ok': False, 'erro': 'controle_id e status_id obrigatórios.'}, status=400)

    controle = ControleClienteV2.objects.filter(pk=controle_id, user=request.user).first()
    if not controle:
        return JsonResponse({'ok': False, 'erro': 'Controle não encontrado.'}, status=404)

    status = StatusChoice.objects.filter(pk=status_id, status_booleano=True).first()
    if not status:
        return JsonResponse({'ok': False, 'erro': 'Status inválido.'}, status=400)

    controle.tabulacao = status
    controle.save(update_fields=['tabulacao', 'updated_at'])

    return JsonResponse({
        'ok': True,
        'tabulacao': {'id': status.id, 'nome': status.nome},
        'tabulado': True,
    })


@login_required(login_url='/')
@controle_acess('SS50')
@require_POST
def api_post_esteira_agendamento(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    controle_id = data.get('controle_id')
    dia = data.get('dia_agendamento')
    hora = data.get('hora')
    if not all([controle_id, dia, hora]):
        return JsonResponse({'ok': False, 'erro': 'Campos obrigatórios faltando.'}, status=400)

    controle = ControleClienteV2.objects.filter(pk=controle_id, user=request.user).first()
    if not controle:
        return JsonResponse({'ok': False, 'erro': 'Controle não encontrado.'}, status=404)

    try:
        dia_date = datetime.strptime(dia, '%Y-%m-%d').date()
        hora_time = datetime.strptime(hora, '%H:%M').time()
    except ValueError:
        return JsonResponse({'ok': False, 'erro': 'Data/hora inválidas.'}, status=400)

    ag = AgendamentoV2.objects.create(
        controle=controle,
        dia_agendamento=dia_date,
        hora=hora_time,
        responsavel=data.get('responsavel') or request.user.get_full_name() or request.user.username,
        observacao=data.get('observacao', ''),
    )

    return JsonResponse({'ok': True, 'agendamento_id': ag.id})
