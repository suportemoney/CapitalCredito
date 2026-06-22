import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.campanha_factory import iter_criar_campanha_com_cpfs


def _sse_criar_campanha(request, tipo: str):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)

    nome = (data.get('nome') or '').strip()
    equipes_ids = data.get('equipes_ids') or []
    cpfs = data.get('cpfs') or []

    def event_stream():
        try:
            for payload in iter_criar_campanha_com_cpfs(nome, cpfs, equipes_ids, tipo):
                evento = payload.pop('evento', 'progress')
                yield f"event: {evento}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield (
                'event: error\n'
                f"data: {json.dumps({'ok': False, 'erro': str(exc)}, ensure_ascii=False)}\n\n"
            )

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required(login_url='/')
@controle_acess('SS49')
@require_POST
def api_sse_gerenciador_siape_criar(request):
    return _sse_criar_campanha(request, 'SIAPE')
