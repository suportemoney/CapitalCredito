"""
APIs para gerenciar produtos
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import Produto

@login_required
@controle_acess('SS28')
@require_http_methods(["GET"])
def api_listar_produtos(request):
    """API GET para listar produtos"""
    try:
        produtos = Produto.objects.all().order_by('nome')
        data = [{
            'id': prod.id,
            'nome': prod.nome,
            'descricao': prod.descricao or '',
            'status': prod.status,
            'data_criacao': prod.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for prod in produtos]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar produtos: {str(e)}'}, status=500)

@login_required
@controle_acess('SS28')
@require_http_methods(["POST"])
def api_criar_produto(request):
    """API POST para criar produto"""
    try:
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        produto = Produto.objects.create(
            nome=nome,
            descricao=descricao if descricao else None,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Produto criado com sucesso!',
            'data': {
                'id': produto.id,
                'nome': produto.nome,
                'descricao': produto.descricao or '',
                'status': produto.status,
                'data_criacao': produto.data_criacao.strftime('%d/%m/%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar produto: {str(e)}'}, status=500)

@login_required
@controle_acess('SS28')
@require_http_methods(["GET", "POST"])
def api_editar_produto(request, produto_id):
    """API para editar produto"""
    try:
        produto = Produto.objects.get(id=produto_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': produto.id,
                    'nome': produto.nome,
                    'descricao': produto.descricao or '',
                    'status': produto.status,
                }
            })
        
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        produto.nome = nome
        produto.descricao = descricao if descricao else None
        produto.status = status
        produto.save()
        
        return JsonResponse({'success': True, 'message': 'Produto atualizado com sucesso!'})
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Produto não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar produto: {str(e)}'}, status=500)

@login_required
@controle_acess('SS28')
@require_http_methods(["POST"])
def api_deletar_produto(request, produto_id):
    """API POST para deletar produto"""
    try:
        produto = Produto.objects.get(id=produto_id)
        
        # Verificar se há contratos usando este produto
        from apps.vendas.financeiro_vendas.models import ContratoPagamento
        contratos_count = ContratoPagamento.objects.filter(produto=produto, status_ativo=True).count()
        
        if contratos_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'Não é possível deletar o produto. Existem {contratos_count} contrato(s) ativo(s) vinculado(s) a ele.'
            }, status=400)
        
        produto.delete()
        return JsonResponse({'success': True, 'message': 'Produto deletado com sucesso!'})
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Produto não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar produto: {str(e)}'}, status=500)

