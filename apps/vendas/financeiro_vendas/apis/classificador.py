"""
APIs para gerenciar classificadores
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.financeiro_vendas.models import Classificador

@login_required
@controle_acess('SS29')
@require_http_methods(["GET"])
def api_listar_classificadores(request):
    """API GET para listar classificadores"""
    try:
        classificadores = Classificador.objects.all().order_by('titulo')
        data = [{
            'id': classif.id,
            'titulo': classif.titulo,
            'percentual': float(classif.percentual),
            'status': classif.status,
            'data_criacao': classif.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for classif in classificadores]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar classificadores: {str(e)}'}, status=500)

@login_required
@controle_acess('SS29')
@require_http_methods(["POST"])
def api_criar_classificador(request):
    """API POST para criar classificador"""
    try:
        titulo = request.POST.get('titulo', '').strip()
        percentual = request.POST.get('percentual', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        
        if not percentual:
            return JsonResponse({'success': False, 'message': 'Percentual é obrigatório'})
        
        try:
            percentual_float = float(percentual)
            if percentual_float < 0 or percentual_float > 100:
                return JsonResponse({'success': False, 'message': 'Percentual deve estar entre 0 e 100'})
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Percentual inválido'})
        
        classificador = Classificador.objects.create(
            titulo=titulo,
            percentual=percentual_float,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Classificador criado com sucesso!',
            'data': {
                'id': classificador.id,
                'titulo': classificador.titulo,
                'percentual': float(classificador.percentual),
                'status': classificador.status,
                'data_criacao': classificador.data_criacao.strftime('%d/%m/%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar classificador: {str(e)}'}, status=500)

@login_required
@controle_acess('SS29')
@require_http_methods(["GET", "POST"])
def api_editar_classificador(request, classificador_id):
    """API para editar classificador"""
    try:
        classificador = Classificador.objects.get(id=classificador_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': classificador.id,
                    'titulo': classificador.titulo,
                    'percentual': float(classificador.percentual),
                    'status': classificador.status,
                }
            })
        
        titulo = request.POST.get('titulo', '').strip()
        percentual = request.POST.get('percentual', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        
        if not percentual:
            return JsonResponse({'success': False, 'message': 'Percentual é obrigatório'})
        
        try:
            percentual_float = float(percentual)
            if percentual_float < 0 or percentual_float > 100:
                return JsonResponse({'success': False, 'message': 'Percentual deve estar entre 0 e 100'})
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Percentual inválido'})
        
        classificador.titulo = titulo
        classificador.percentual = percentual_float
        classificador.status = status
        classificador.save()
        
        return JsonResponse({'success': True, 'message': 'Classificador atualizado com sucesso!'})
    except Classificador.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Classificador não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar classificador: {str(e)}'}, status=500)

@login_required
@controle_acess('SS29')
@require_http_methods(["POST"])
def api_deletar_classificador(request, classificador_id):
    """API POST para deletar classificador"""
    try:
        classificador = Classificador.objects.get(id=classificador_id)
        
        # Verificar se há contratos usando este classificador
        from apps.vendas.financeiro_vendas.models import ContratoPagamento
        contratos_count = ContratoPagamento.objects.filter(classificador=classificador, status_ativo=True).count()
        
        if contratos_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'Não é possível deletar o classificador. Existem {contratos_count} contrato(s) ativo(s) vinculado(s) a ele.'
            }, status=400)
        
        classificador.delete()
        return JsonResponse({'success': True, 'message': 'Classificador deletado com sucesso!'})
    except Classificador.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Classificador não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar classificador: {str(e)}'}, status=500)

