from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.bonificacoes.models import ReducaoBonificacaoRegra, ReducaoBonificacaoFuncionario

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_reducao_regras(request):
    try:
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = ReducaoBonificacaoRegra.objects.all()
        if apenas_ativos:
            qs = qs.filter(ativo=True)
        qs = qs.order_by('ordem', 'titulo')
        data = [{'id': r.id, 'titulo': r.titulo, 'percentual': float(r.percentual), 'ordem': r.ordem, 'ativo': r.ativo} for r in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_reducao_regra(request):
    try:
        regra_id = request.POST.get('regra_id', '').strip()
        titulo = request.POST.get('titulo', '').strip()
        percentual = request.POST.get('percentual', '').strip()
        ordem = request.POST.get('ordem', '1').strip()
        ativo = request.POST.get('ativo', 'true').strip()
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        if not percentual:
            return JsonResponse({'success': False, 'message': 'Percentual é obrigatório'})
        with transaction.atomic():
            if regra_id:
                regra = ReducaoBonificacaoRegra.objects.get(id=regra_id)
            else:
                regra = ReducaoBonificacaoRegra()
            regra.titulo = titulo.upper()
            regra.percentual = Decimal(percentual.replace(',', '.'))
            regra.ordem = int(ordem) if ordem else 1
            regra.ativo = ativo.lower() in ('true', '1', 'ativo')
            regra.save()
        return JsonResponse({'success': True, 'message': 'Regra de redução salva.', 'result': {'id': regra.id}})
    except ReducaoBonificacaoRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Regra não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_deletar_reducao_regra(request):
    try:
        regra_id = request.POST.get('regra_id')
        if not regra_id:
            return JsonResponse({'success': False, 'message': 'ID da regra é obrigatório'})
        regra = ReducaoBonificacaoRegra.objects.get(id=regra_id)
        regra.delete()
        return JsonResponse({'success': True, 'message': 'Regra de redução excluída.', 'result': None})
    except ReducaoBonificacaoRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Regra não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_reducoes_funcionario(request):
    try:
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        periodo_inicio = request.GET.get('periodo_inicio', '').strip()
        periodo_fim = request.GET.get('periodo_fim', '').strip()
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'funcionario_id é obrigatório'})
        qs = ReducaoBonificacaoFuncionario.objects.filter(funcionario_id=funcionario_id).select_related('regra_reducao').order_by('data_evento')
        if periodo_inicio:
            qs = qs.filter(data_evento__gte=periodo_inicio)
        if periodo_fim:
            qs = qs.filter(data_evento__lte=periodo_fim)
        data = [{'id': r.id, 'regra_reducao_id': r.regra_reducao_id, 'regra_titulo': r.regra_reducao.titulo, 'percentual': float(r.regra_reducao.percentual), 'data_evento': r.data_evento.strftime('%Y-%m-%d')} for r in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_reducao_funcionario(request):
    try:
        funcionario_id = request.POST.get('funcionario_id')
        regra_reducao_id = request.POST.get('regra_reducao_id')
        data_evento = request.POST.get('data_evento', '').strip()
        if not funcionario_id or not regra_reducao_id or not data_evento:
            return JsonResponse({'success': False, 'message': 'Funcionário, regra de redução e data do evento são obrigatórios'})
        with transaction.atomic():
            ReducaoBonificacaoFuncionario.objects.create(funcionario_id=funcionario_id, regra_reducao_id=regra_reducao_id, data_evento=data_evento)
        return JsonResponse({'success': True, 'message': 'Redução lançada.', 'result': None})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_deletar_reducao_funcionario(request):
    try:
        reducao_id = request.POST.get('reducao_id')
        if not reducao_id:
            return JsonResponse({'success': False, 'message': 'ID da redução é obrigatório'})
        reducao = ReducaoBonificacaoFuncionario.objects.get(id=reducao_id)
        reducao.delete()
        return JsonResponse({'success': True, 'message': 'Redução excluída.', 'result': None})
    except ReducaoBonificacaoFuncionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Redução não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
