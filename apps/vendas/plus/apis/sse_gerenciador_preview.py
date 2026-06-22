import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST

from apps.seguranca.permissoes.decorators import controle_acess

from apps.vendas.plus.services.v2.csv_cpfs import extrair_cpfs_csv
from apps.vendas.plus.services.v2.preview_cpf_campanha import iter_preview_cpfs


def _sse_preview_csv_campanha(request):
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Arquivo CSV obrigatório.'}, status=400)

    extraido = extrair_cpfs_csv(arquivo.read())
    if not extraido.get('ok'):
        return JsonResponse(extraido, status=400)

    cpfs = extraido['cpfs']
    invalidos_csv = extraido.get('invalidos', 0)

    def event_stream():
        try:
            yield (
                'event: start\n'
                f"data: {json.dumps({'total': len(cpfs), 'invalidos_csv': invalidos_csv}, ensure_ascii=False)}\n\n"
            )
            for payload in iter_preview_cpfs(cpfs, 'SIAPE'):
                evento = payload.pop('evento', 'progress')
                if evento == 'complete':
                    payload['invalidos_csv'] = invalidos_csv
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
def api_sse_gerenciador_siape_preview(request):
    return _sse_preview_csv_campanha(request)
