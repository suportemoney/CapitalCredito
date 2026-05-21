from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.financeiro_geral.models import Conta, Salario, Beneficio, ContaReceber

@login_required
@controle_acess('SS21')
@require_http_methods(["GET"])
def api_get_dashboard(request):
    """Retorna totais a pagar (Conta + Salario + Beneficio não pagos) e a receber (não recebidos)."""
    try:
        total_contas = Conta.objects.filter(status_ativo=True, pago=False).aggregate(s=Sum('valor'))['s'] or 0
        total_salarios = Salario.objects.filter(status_ativo=True, pago=False).aggregate(s=Sum('valor'))['s'] or 0
        total_beneficios = Beneficio.objects.filter(status_ativo=True, pago=False).aggregate(s=Sum('valor'))['s'] or 0
        total_a_pagar = total_contas + total_salarios + total_beneficios
        total_a_receber = ContaReceber.objects.filter(status_ativo=True, recebido=False).aggregate(s=Sum('valor'))['s'] or 0
        return JsonResponse({
            'success': True,
            'result': {
                'total_a_pagar': float(total_a_pagar),
                'total_a_receber': float(total_a_receber),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
