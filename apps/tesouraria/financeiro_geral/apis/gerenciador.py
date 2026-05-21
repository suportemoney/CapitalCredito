from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.financeiro_geral.models import CategoriaConta, SubcategoriaConta, TipoBeneficio

@login_required
@controle_acess('SS23')
@require_http_methods(["GET"])
def api_get_categorias(request):
    """Lista categorias de conta (ativas ou todas conforme parâmetro)."""
    try:
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = CategoriaConta.objects.all()
        if apenas_ativos:
            qs = qs.filter(status=True)
        qs = qs.order_by('nome')
        data = [{'id': c.id, 'nome': c.nome, 'status': c.status} for c in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["GET"])
def api_get_subcategorias(request):
    """Lista subcategorias. Opcional: categoria_id para filtrar."""
    try:
        categoria_id = request.GET.get('categoria_id', '')
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = SubcategoriaConta.objects.select_related('categoria').all()
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        if apenas_ativos:
            qs = qs.filter(status=True)
        qs = qs.order_by('categoria__nome', 'nome')
        data = [{'id': s.id, 'categoria_id': s.categoria_id, 'categoria_nome': s.categoria.nome, 'nome': s.nome, 'status': s.status} for s in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["GET"])
def api_get_tipos_beneficio(request):
    """Lista tipos de benefício."""
    try:
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = TipoBeneficio.objects.all()
        if apenas_ativos:
            qs = qs.filter(status=True)
        qs = qs.order_by('nome')
        data = [{'id': t.id, 'nome': t.nome, 'status': t.status} for t in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_categoria_criar(request):
    """Cria categoria de conta."""
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        with transaction.atomic():
            CategoriaConta.objects.create(nome=nome.upper(), status=True)
        return JsonResponse({'success': True, 'message': 'Categoria criada com sucesso.', 'result': None})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_categoria_editar(request):
    """Edita categoria (nome e/ou status)."""
    try:
        categoria_id = request.POST.get('categoria_id')
        nome = request.POST.get('nome', '').strip()
        status_val = request.POST.get('status', '')
        if not categoria_id:
            return JsonResponse({'success': False, 'message': 'ID da categoria é obrigatório'})
        cat = CategoriaConta.objects.get(id=categoria_id)
        if nome:
            cat.nome = nome.upper()
        if status_val.lower() in ('true', '1', 'ativo'):
            cat.status = True
        elif status_val.lower() in ('false', '0', 'inativo'):
            cat.status = False
        cat.save()
        return JsonResponse({'success': True, 'message': 'Categoria atualizada.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_categoria_deletar(request):
    """Inativa categoria (soft delete)."""
    try:
        categoria_id = request.POST.get('categoria_id')
        if not categoria_id:
            return JsonResponse({'success': False, 'message': 'ID da categoria é obrigatório'})
        cat = CategoriaConta.objects.get(id=categoria_id)
        cat.status = False
        cat.save()
        return JsonResponse({'success': True, 'message': 'Categoria inativada.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_subcategoria_criar(request):
    """Cria subcategoria de conta."""
    try:
        categoria_id = request.POST.get('categoria_id')
        nome = request.POST.get('nome', '').strip()
        if not categoria_id:
            return JsonResponse({'success': False, 'message': 'Categoria é obrigatória'})
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        cat = CategoriaConta.objects.get(id=categoria_id)
        with transaction.atomic():
            SubcategoriaConta.objects.create(categoria=cat, nome=nome.upper(), status=True)
        return JsonResponse({'success': True, 'message': 'Subcategoria criada com sucesso.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_subcategoria_editar(request):
    """Edita subcategoria."""
    try:
        subcategoria_id = request.POST.get('subcategoria_id')
        nome = request.POST.get('nome', '').strip()
        status_val = request.POST.get('status', '')
        if not subcategoria_id:
            return JsonResponse({'success': False, 'message': 'ID da subcategoria é obrigatório'})
        sub = SubcategoriaConta.objects.get(id=subcategoria_id)
        if nome:
            sub.nome = nome.upper()
        if status_val.lower() in ('true', '1', 'ativo'):
            sub.status = True
        elif status_val.lower() in ('false', '0', 'inativo'):
            sub.status = False
        sub.save()
        return JsonResponse({'success': True, 'message': 'Subcategoria atualizada.', 'result': None})
    except SubcategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_subcategoria_deletar(request):
    """Inativa subcategoria."""
    try:
        subcategoria_id = request.POST.get('subcategoria_id')
        if not subcategoria_id:
            return JsonResponse({'success': False, 'message': 'ID da subcategoria é obrigatório'})
        sub = SubcategoriaConta.objects.get(id=subcategoria_id)
        sub.status = False
        sub.save()
        return JsonResponse({'success': True, 'message': 'Subcategoria inativada.', 'result': None})
    except SubcategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_tipo_beneficio_criar(request):
    """Cria tipo de benefício."""
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        with transaction.atomic():
            TipoBeneficio.objects.create(nome=nome.upper(), status=True)
        return JsonResponse({'success': True, 'message': 'Tipo de benefício criado com sucesso.', 'result': None})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_tipo_beneficio_editar(request):
    """Edita tipo de benefício."""
    try:
        tipo_id = request.POST.get('tipo_id')
        nome = request.POST.get('nome', '').strip()
        status_val = request.POST.get('status', '')
        if not tipo_id:
            return JsonResponse({'success': False, 'message': 'ID do tipo é obrigatório'})
        t = TipoBeneficio.objects.get(id=tipo_id)
        if nome:
            t.nome = nome.upper()
        if status_val.lower() in ('true', '1', 'ativo'):
            t.status = True
        elif status_val.lower() in ('false', '0', 'inativo'):
            t.status = False
        t.save()
        return JsonResponse({'success': True, 'message': 'Tipo de benefício atualizado.', 'result': None})
    except TipoBeneficio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tipo de benefício não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_tipo_beneficio_deletar(request):
    """Inativa tipo de benefício."""
    try:
        tipo_id = request.POST.get('tipo_id')
        if not tipo_id:
            return JsonResponse({'success': False, 'message': 'ID do tipo é obrigatório'})
        t = TipoBeneficio.objects.get(id=tipo_id)
        t.status = False
        t.save()
        return JsonResponse({'success': True, 'message': 'Tipo de benefício inativado.', 'result': None})
    except TipoBeneficio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tipo de benefício não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
