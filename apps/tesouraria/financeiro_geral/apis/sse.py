# SSE (Server-Sent Events) para notificações de contas a pagar em tempo quase real
import json
import queue
from django.http import StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.utils import user_has_access
from apps.tesouraria.financeiro_geral.apis.notificacoes import get_contas_notificacao_count

_sse_queues = []

def push_contas_notificacao_count():
    """Chamado pelo signal quando Conta/Salario/Beneficio é criado/atualizado; envia count para todos os clientes SSE."""
    try:
        count = get_contas_notificacao_count()
        payload = json.dumps({'count': count})
        for q in list(_sse_queues):
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass
    except Exception:
        pass

def _stream_notificacoes(request):
    """Generator que mantém a conexão SSE e envia count quando há atualização."""
    q = queue.Queue(maxsize=10)
    _sse_queues.append(q)
    try:
        # Envia count inicial
        try:
            count = get_contas_notificacao_count()
            yield f"data: {json.dumps({'count': count})}\n\n"
        except Exception:
            pass
        while True:
            try:
                msg = q.get(timeout=25)
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    finally:
        if q in _sse_queues:
            _sse_queues.remove(q)

@csrf_exempt
@login_required
@require_http_methods(["GET"])
def sse_notificacoes_contas(request):
    """Stream SSE: apenas para usuários com CX44. Cliente recebe eventos com {count} quando contas a pagar mudam."""
    if not user_has_access(request.user, 'CX44'):
        return StreamingHttpResponse(
            iter([f"data: {json.dumps({'count': 0})}\n\n"]),
            content_type='text/event-stream'
        )
    response = StreamingHttpResponse(
        _stream_notificacoes(request),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
