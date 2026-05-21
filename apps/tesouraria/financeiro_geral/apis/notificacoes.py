import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.seguranca.permissoes.utils import user_has_access
from apps.tesouraria.financeiro_geral.models import Conta, Salario, Beneficio, BonificacaoAPagar

def get_contas_notificacao_count():
    """Retorna quantidade de contas a pagar vencendo hoje ou atrasadas (Conta + Salario + Beneficio)."""
    hoje = timezone.now().date()
    total = 0
    total += Conta.objects.filter(status_ativo=True, pago=False, data_vencimento__lte=hoje).count()
    total += Salario.objects.filter(status_ativo=True, pago=False, data_vencimento__lte=hoje).count()
    total += Beneficio.objects.filter(status_ativo=True, pago=False, data_vencimento__lte=hoje).count()
    return min(total, 99)

@login_required
@require_http_methods(["GET"])
def api_get_notificacoes_count(request):
    """Retorna apenas o contador para o badge. Apenas para quem tem CX44."""
    if not user_has_access(request.user, 'CX44'):
        return JsonResponse({'success': True, 'result': {'count': 0}})
    try:
        return JsonResponse({'success': True, 'result': {'count': get_contas_notificacao_count()}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_get_notificacoes_contas(request):
    """Retorna contas a pagar vencendo hoje e atrasadas (Conta + Salario + Beneficio). Apenas para usuários com acesso CX44."""
    if not user_has_access(request.user, 'CX44'):
        return JsonResponse({'success': True, 'result': {'hoje': [], 'atrasadas': []}})
    try:
        hoje = timezone.now().date()
        hoje_lista = []
        atrasadas_lista = []
        for qs, tipo, tipo_display in [
            (Conta.objects.filter(status_ativo=True, pago=False, data_vencimento__lte=hoje).select_related('categoria').order_by('data_vencimento')[:20], 'CONTA', 'Conta (empresa)'),
            (Salario.objects.filter(status_ativo=True, pago=False, data_vencimento__lte=hoje).select_related('funcionario').order_by('data_vencimento')[:20], 'SALARIO', 'Salário'),
            (Beneficio.objects.filter(status_ativo=True, pago=False, data_vencimento__lte=hoje).select_related('funcionario', 'tipo_beneficio').order_by('data_vencimento')[:20], 'BENEFICIO', 'Benefício'),
        ]:
            for c in qs:
                item = {
                    'id': c.id,
                    'tipo': tipo,
                    'tipo_display': tipo_display,
                    'descricao': c.descricao,
                    'valor': float(c.valor),
                    'data_vencimento': c.data_vencimento.strftime('%Y-%m-%d'),
                    'status': 'Pago' if c.pago else 'Pendente',
                    'funcionario_nome': getattr(c, 'funcionario', None) and c.funcionario.nome_completo or None,
                }
                if c.data_vencimento == hoje:
                    hoje_lista.append(item)
                else:
                    atrasadas_lista.append(item)
        hoje_lista.sort(key=lambda x: x['data_vencimento'])
        atrasadas_lista.sort(key=lambda x: x['data_vencimento'])
        return JsonResponse({
            'success': True,
            'result': {
                'hoje': hoje_lista[:30],
                'atrasadas': atrasadas_lista[:30],
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_get_bonificacoes_usuario(request):
    """Bonificações do funcionário logado cujo mes_referente é o mês anterior (visível só no mês seguinte)."""
    try:
        if not getattr(request.user, 'funcionario_profile', None):
            return JsonResponse({'success': True, 'result': {'mes_referente': '', 'itens': []}})
        hoje = timezone.now().date()
        if hoje.month == 1:
            mes_anterior, ano = 12, hoje.year - 1
        else:
            mes_anterior, ano = hoje.month - 1, hoje.year
        mes_anterior_str = f"{mes_anterior:02d}/{ano}"
        qs = BonificacaoAPagar.objects.filter(
            funcionario=request.user.funcionario_profile,
            status_ativo=True,
            mes_referente=mes_anterior_str
        ).order_by('status_pagamento', '-data_criacao')
        itens = [
            {'id': b.id, 'valor_bonificacao': float(b.valor_bonificacao), 'status_pagamento': b.status_pagamento}
            for b in qs
        ]
        return JsonResponse({'success': True, 'result': {'mes_referente': mes_anterior_str, 'itens': itens}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
