"""
APIs para gerenciar metas SIAPE
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import datetime
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import MetaSIAPE

@login_required
@controle_acess('SS30')
@require_http_methods(["GET"])
def api_listar_metas(request):
    """API GET para listar metas"""
    try:
        metas = MetaSIAPE.objects.all().order_by('-data_criacao')
        data = [{
            'id': meta.id,
            'titulo': meta.titulo,
            'valor_meta': float(meta.valor_meta),
            'data_inicio': meta.data_inicio.strftime('%Y-%m-%d'),
            'data_final': meta.data_final.strftime('%Y-%m-%d'),
            'status': meta.status,
            'data_criacao': meta.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for meta in metas]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar metas: {str(e)}'}, status=500)

@login_required
@controle_acess('SS30')
@require_http_methods(["POST"])
def api_criar_meta(request):
    """API POST para criar meta"""
    try:
        titulo = request.POST.get('titulo', '').strip()
        valor_meta = request.POST.get('valor_meta', '').strip()
        data_inicio = request.POST.get('data_inicio', '').strip()
        data_final = request.POST.get('data_final', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        
        if not valor_meta:
            return JsonResponse({'success': False, 'message': 'Valor da meta é obrigatório'})
        
        if not data_inicio:
            return JsonResponse({'success': False, 'message': 'Data de início é obrigatória'})
        
        if not data_final:
            return JsonResponse({'success': False, 'message': 'Data final é obrigatória'})
        
        try:
            valor_meta_float = float(valor_meta)
            if valor_meta_float < 0:
                return JsonResponse({'success': False, 'message': 'Valor da meta deve ser maior ou igual a zero'})
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Valor da meta inválido'})
        
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_final_obj = datetime.strptime(data_final, '%Y-%m-%d').date()
            
            if data_final_obj < data_inicio_obj:
                return JsonResponse({'success': False, 'message': 'Data final deve ser maior ou igual à data de início'})
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Data inválida'})
        
        with transaction.atomic():
            meta = MetaSIAPE.objects.create(
                titulo=titulo,
                valor_meta=valor_meta_float,
                data_inicio=data_inicio_obj,
                data_final=data_final_obj,
                status=status
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Meta criada com sucesso!',
            'data': {
                'id': meta.id,
                'titulo': meta.titulo,
                'valor_meta': float(meta.valor_meta),
                'data_inicio': meta.data_inicio.strftime('%Y-%m-%d'),
                'data_final': meta.data_final.strftime('%Y-%m-%d'),
                'status': meta.status,
                'data_criacao': meta.data_criacao.strftime('%d/%m/%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar meta: {str(e)}'}, status=500)

@login_required
@controle_acess('SS30')
@require_http_methods(["GET", "POST"])
def api_editar_meta(request, meta_id):
    """API para editar meta"""
    try:
        meta = MetaSIAPE.objects.get(id=meta_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': meta.id,
                    'titulo': meta.titulo,
                    'valor_meta': float(meta.valor_meta),
                    'data_inicio': meta.data_inicio.strftime('%Y-%m-%d'),
                    'data_final': meta.data_final.strftime('%Y-%m-%d'),
                    'status': meta.status,
                }
            })
        
        titulo = request.POST.get('titulo', '').strip()
        valor_meta = request.POST.get('valor_meta', '').strip()
        data_inicio = request.POST.get('data_inicio', '').strip()
        data_final = request.POST.get('data_final', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        
        if not valor_meta:
            return JsonResponse({'success': False, 'message': 'Valor da meta é obrigatório'})
        
        if not data_inicio:
            return JsonResponse({'success': False, 'message': 'Data de início é obrigatória'})
        
        if not data_final:
            return JsonResponse({'success': False, 'message': 'Data final é obrigatória'})
        
        try:
            valor_meta_float = float(valor_meta)
            if valor_meta_float < 0:
                return JsonResponse({'success': False, 'message': 'Valor da meta deve ser maior ou igual a zero'})
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Valor da meta inválido'})
        
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_final_obj = datetime.strptime(data_final, '%Y-%m-%d').date()
            
            if data_final_obj < data_inicio_obj:
                return JsonResponse({'success': False, 'message': 'Data final deve ser maior ou igual à data de início'})
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Data inválida'})
        
        with transaction.atomic():
            meta.titulo = titulo
            meta.valor_meta = valor_meta_float
            meta.data_inicio = data_inicio_obj
            meta.data_final = data_final_obj
            meta.status = status
            meta.save()
        
        return JsonResponse({'success': True, 'message': 'Meta atualizada com sucesso!'})
    except MetaSIAPE.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Meta não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar meta: {str(e)}'}, status=500)

@login_required
@controle_acess('SS30')
@require_http_methods(["POST"])
def api_deletar_meta(request, meta_id):
    """API POST para deletar meta"""
    try:
        meta = MetaSIAPE.objects.get(id=meta_id)
        meta.delete()
        return JsonResponse({'success': True, 'message': 'Meta deletada com sucesso!'})
    except MetaSIAPE.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Meta não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar meta: {str(e)}'}, status=500)

