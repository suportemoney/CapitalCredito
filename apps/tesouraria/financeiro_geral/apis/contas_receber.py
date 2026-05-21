from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.financeiro_geral.models import ContaReceber

@login_required
@controle_acess('SS21')
@require_http_methods(["GET"])
def api_get_contas_receber(request):
    """Lista contas a receber. Filtro opcional: recebido (true/false)."""
    try:
        recebido = request.GET.get('recebido', '')
        contas = ContaReceber.objects.filter(status_ativo=True).order_by('-data_prevista', '-data_criacao')
        if recebido == 'true':
            contas = contas.filter(recebido=True)
        elif recebido == 'false':
            contas = contas.filter(recebido=False)
        data = []
        for c in contas:
            data.append({
                'id': c.id,
                'descricao': c.descricao,
                'valor': float(c.valor),
                'data_prevista': c.data_prevista.strftime('%Y-%m-%d'),
                'data_recebimento': c.data_recebimento.strftime('%Y-%m-%d') if c.data_recebimento else None,
                'recebido': c.recebido,
                'observacao': c.observacao or '',
            })
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS21')
@require_http_methods(["POST"])
def api_post_contas_receber_criar(request):
    """Cria conta a receber."""
    try:
        descricao = request.POST.get('descricao', '').strip()
        valor = request.POST.get('valor', '').strip()
        data_prevista = request.POST.get('data_prevista', '').strip()
        observacao = request.POST.get('observacao', '').strip() or None
        if not descricao:
            return JsonResponse({'success': False, 'message': 'Descrição é obrigatória'})
        if not valor:
            return JsonResponse({'success': False, 'message': 'Valor é obrigatório'})
        if not data_prevista:
            return JsonResponse({'success': False, 'message': 'Data prevista é obrigatória'})
        try:
            valor_dec = Decimal(valor.replace(',', '.'))
            data_prev = datetime.strptime(data_prevista, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Valor ou data inválidos'})
        with transaction.atomic():
            ContaReceber.objects.create(
                descricao=descricao,
                valor=valor_dec,
                data_prevista=data_prev,
                recebido=False,
                observacao=observacao,
                status_ativo=True,
            )
        return JsonResponse({'success': True, 'message': 'Conta a receber criada com sucesso.', 'result': None})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS21')
@require_http_methods(["POST"])
def api_post_contas_receber_marcar_recebido(request):
    """Marca conta a receber como recebida. data_recebimento opcional (default hoje)."""
    try:
        conta_id = request.POST.get('conta_id')
        data_recebimento = request.POST.get('data_recebimento', '').strip()
        if not conta_id:
            return JsonResponse({'success': False, 'message': 'ID da conta é obrigatório'})
        conta = ContaReceber.objects.get(id=conta_id, status_ativo=True)
        if data_recebimento:
            try:
                data_rec = datetime.strptime(data_recebimento, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Data de recebimento inválida'})
        else:
            data_rec = timezone.now().date()
        conta.recebido = True
        conta.data_recebimento = data_rec
        conta.save()
        return JsonResponse({'success': True, 'message': 'Conta marcada como recebida.', 'result': None})
    except ContaReceber.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Conta não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
