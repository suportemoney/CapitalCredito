from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from apps.seguranca.permissoes.decorators import controle_acess, controle_acess_any
from apps.tesouraria.financeiro_geral.models import CategoriaConta, SubcategoriaConta, TipoBeneficio


def _parse_status(status_val):
    """Converte string de status em bool ou None se não informado."""
    if status_val is None or status_val == '':
        return None
    low = str(status_val).lower()
    if low in ('true', '1', 'ativo'):
        return True
    if low in ('false', '0', 'inativo'):
        return False
    return None


@login_required
@controle_acess_any('SS22', 'SS23')
@require_http_methods(["GET"])
def api_get_categorias(request):
    """Lista categorias de conta (ativas ou todas conforme parâmetro). Leitura: SS22 ou SS23."""
    try:
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = CategoriaConta.objects.all()
        if apenas_ativos:
            qs = qs.filter(status=True)
        qs = qs.order_by('nome')
        data = [{'id': c.id, 'nome': c.nome, 'status': c.status} for c in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao listar categorias.'}, status=500)


@login_required
@controle_acess_any('SS22', 'SS23')
@require_http_methods(["GET"])
def api_get_subcategorias(request):
    """Lista subcategorias. Opcional: categoria_id. Leitura: SS22 ou SS23."""
    try:
        categoria_id = request.GET.get('categoria_id', '')
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = SubcategoriaConta.objects.select_related('categoria').all()
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        if apenas_ativos:
            qs = qs.filter(status=True)
        qs = qs.order_by('categoria__nome', 'nome')
        data = [
            {
                'id': s.id,
                'categoria_id': s.categoria_id,
                'categoria_nome': s.categoria.nome,
                'nome': s.nome,
                'status': s.status,
            }
            for s in qs
        ]
        return JsonResponse({'success': True, 'result': data})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao listar subcategorias.'}, status=500)


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
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao listar tipos de benefício.'}, status=500)


@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_categoria_criar(request):
    """Cria categoria de conta."""
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        if len(nome) > 255:
            return JsonResponse({'success': False, 'message': 'Nome não pode exceder 255 caracteres.'})
        nome_up = nome.upper()
        if CategoriaConta.objects.filter(nome=nome_up).exists():
            return JsonResponse({'success': False, 'message': 'Já existe uma categoria com este nome.'})
        CategoriaConta.objects.create(nome=nome_up, status=True)
        return JsonResponse({'success': True, 'message': 'Categoria criada com sucesso.', 'result': None})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao criar categoria.'}, status=500)


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
            if len(nome) > 255:
                return JsonResponse({'success': False, 'message': 'Nome não pode exceder 255 caracteres.'})
            nome_up = nome.upper()
            if CategoriaConta.objects.filter(nome=nome_up).exclude(id=cat.id).exists():
                return JsonResponse({'success': False, 'message': 'Já existe uma categoria com este nome.'})
            cat.nome = nome_up
        novo_status = _parse_status(status_val)
        if novo_status is not None:
            cat.status = novo_status
            # Ao inativar categoria, inativa subcategorias filhas
            if novo_status is False:
                SubcategoriaConta.objects.filter(categoria=cat).update(status=False)
        cat.save()
        return JsonResponse({'success': True, 'message': 'Categoria atualizada.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao atualizar categoria.'}, status=500)


@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_categoria_deletar(request):
    """Inativa categoria (soft delete) e cascata nas subcategorias."""
    try:
        categoria_id = request.POST.get('categoria_id')
        if not categoria_id:
            return JsonResponse({'success': False, 'message': 'ID da categoria é obrigatório'})
        cat = CategoriaConta.objects.get(id=categoria_id)
        with transaction.atomic():
            cat.status = False
            cat.save(update_fields=['status'])
            SubcategoriaConta.objects.filter(categoria=cat).update(status=False)
        return JsonResponse({'success': True, 'message': 'Categoria inativada.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao inativar categoria.'}, status=500)


@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_subcategoria_criar(request):
    """Cria subcategoria de conta (somente em categoria ativa)."""
    try:
        categoria_id = request.POST.get('categoria_id')
        nome = request.POST.get('nome', '').strip()
        if not categoria_id:
            return JsonResponse({'success': False, 'message': 'Categoria é obrigatória'})
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        if len(nome) > 255:
            return JsonResponse({'success': False, 'message': 'Nome não pode exceder 255 caracteres.'})
        cat = CategoriaConta.objects.get(id=categoria_id)
        if not cat.status:
            return JsonResponse({'success': False, 'message': 'Não é possível criar subcategoria em categoria inativa.'})
        nome_up = nome.upper()
        if SubcategoriaConta.objects.filter(categoria=cat, nome=nome_up).exists():
            return JsonResponse({'success': False, 'message': 'Já existe uma subcategoria com este nome nesta categoria.'})
        SubcategoriaConta.objects.create(categoria=cat, nome=nome_up, status=True)
        return JsonResponse({'success': True, 'message': 'Subcategoria criada com sucesso.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao criar subcategoria.'}, status=500)


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
        sub = SubcategoriaConta.objects.select_related('categoria').get(id=subcategoria_id)
        if nome:
            if len(nome) > 255:
                return JsonResponse({'success': False, 'message': 'Nome não pode exceder 255 caracteres.'})
            nome_up = nome.upper()
            if SubcategoriaConta.objects.filter(categoria=sub.categoria, nome=nome_up).exclude(id=sub.id).exists():
                return JsonResponse({'success': False, 'message': 'Já existe uma subcategoria com este nome nesta categoria.'})
            sub.nome = nome_up
        novo_status = _parse_status(status_val)
        if novo_status is not None:
            # Reativar subcategoria só se a categoria pai estiver ativa
            if novo_status is True and not sub.categoria.status:
                return JsonResponse({
                    'success': False,
                    'message': 'Não é possível reativar subcategoria com categoria inativa. Reative a categoria primeiro.',
                })
            sub.status = novo_status
        sub.save()
        return JsonResponse({'success': True, 'message': 'Subcategoria atualizada.', 'result': None})
    except SubcategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategoria não encontrada'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao atualizar subcategoria.'}, status=500)


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
        sub.save(update_fields=['status'])
        return JsonResponse({'success': True, 'message': 'Subcategoria inativada.', 'result': None})
    except SubcategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategoria não encontrada'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao inativar subcategoria.'}, status=500)


@login_required
@controle_acess('SS23')
@require_http_methods(["POST"])
def api_post_tipo_beneficio_criar(request):
    """Cria tipo de benefício."""
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        if len(nome) > 255:
            return JsonResponse({'success': False, 'message': 'Nome não pode exceder 255 caracteres.'})
        nome_up = nome.upper()
        if TipoBeneficio.objects.filter(nome=nome_up).exists():
            return JsonResponse({'success': False, 'message': 'Já existe um tipo de benefício com este nome.'})
        TipoBeneficio.objects.create(nome=nome_up, status=True)
        return JsonResponse({'success': True, 'message': 'Tipo de benefício criado com sucesso.', 'result': None})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao criar tipo de benefício.'}, status=500)


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
            if len(nome) > 255:
                return JsonResponse({'success': False, 'message': 'Nome não pode exceder 255 caracteres.'})
            nome_up = nome.upper()
            if TipoBeneficio.objects.filter(nome=nome_up).exclude(id=t.id).exists():
                return JsonResponse({'success': False, 'message': 'Já existe um tipo de benefício com este nome.'})
            t.nome = nome_up
        novo_status = _parse_status(status_val)
        if novo_status is not None:
            t.status = novo_status
        t.save()
        return JsonResponse({'success': True, 'message': 'Tipo de benefício atualizado.', 'result': None})
    except TipoBeneficio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tipo de benefício não encontrado'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao atualizar tipo de benefício.'}, status=500)


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
        t.save(update_fields=['status'])
        return JsonResponse({'success': True, 'message': 'Tipo de benefício inativado.', 'result': None})
    except TipoBeneficio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tipo de benefício não encontrado'}, status=404)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Erro ao inativar tipo de benefício.'}, status=500)
