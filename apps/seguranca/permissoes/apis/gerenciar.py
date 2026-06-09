"""
APIs para gerenciar permissões (CRUD completo)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from ..models import Acesso, ControleAcessos, GroupsAcessos
from ..decorators import controle_acess

# ========== TAB 1: CRUD Acesso ==========

@login_required
@controle_acess('SS20')
@require_http_methods(["GET"])
def api_listar_acessos(request):
    """API GET para listar todos os acessos"""
    try:
        acessos = Acesso.objects.all().order_by('tipo', 'nome')
        acessos_data = [{
            'id': acesso.id,
            'nome': acesso.nome,
            'tipo': acesso.tipo,
            'tipo_display': acesso.get_tipo_display(),
            'codigo': acesso.gerar_codigo(),
            'descricao': acesso.descricao or '',
            'status': acesso.status,
            'data_criacao': acesso.data_criacao.strftime('%d/%m/%Y %H:%M')
        } for acesso in acessos]
        return JsonResponse(acessos_data, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_criar_acesso(request):
    """API POST para criar novo acesso"""
    try:
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        if not tipo or tipo not in [choice[0] for choice in Acesso.TIPO_CHOICES]:
            return JsonResponse({'success': False, 'message': 'Tipo inválido'})
        
        acesso = Acesso.objects.create(
            nome=nome,
            tipo=tipo,
            descricao=descricao if descricao else None,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Acesso "{nome}" criado com sucesso!',
            'data': {
                'id': acesso.id,
                'codigo': acesso.gerar_codigo()
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["GET", "POST"])
def api_editar_acesso(request, acesso_id):
    """API GET/POST para editar acesso"""
    acesso = get_object_or_404(Acesso, id=acesso_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'data': {
                'id': acesso.id,
                'nome': acesso.nome,
                'tipo': acesso.tipo,
                'descricao': acesso.descricao or '',
                'status': acesso.status
            }
        })
    
    try:
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        if not tipo or tipo not in [choice[0] for choice in Acesso.TIPO_CHOICES]:
            return JsonResponse({'success': False, 'message': 'Tipo inválido'})
        
        acesso.nome = nome
        acesso.tipo = tipo
        acesso.descricao = descricao if descricao else None
        acesso.status = status
        acesso.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Acesso "{nome}" atualizado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_deletar_acesso(request, acesso_id):
    """API POST para deletar acesso"""
    try:
        acesso = get_object_or_404(Acesso, id=acesso_id)
        nome = acesso.nome
        acesso.delete()
        return JsonResponse({
            'success': True,
            'message': f'Acesso "{nome}" deletado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# ========== TAB 2: CRUD GroupsAcessos ==========

@login_required
@controle_acess('SS20')
@require_http_methods(["GET"])
def api_listar_grupos(request):
    """API GET para listar todos os grupos"""
    try:
        grupos = GroupsAcessos.objects.prefetch_related('acessos').all().order_by('titulo')
        grupos_data = []
        for grupo in grupos:
            grupos_data.append({
                'id': grupo.id,
                'titulo': grupo.titulo,
                'descricao': grupo.descricao or '',
                'acessos_ids': list(grupo.acessos.values_list('id', flat=True)),
                'acessos_count': grupo.acessos.count(),
                'status': grupo.status,
                'data_criacao': grupo.data_criacao.strftime('%d/%m/%Y %H:%M')
            })
        return JsonResponse(grupos_data, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_criar_grupo(request):
    """API POST para criar novo grupo"""
    try:
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        acessos_ids = request.POST.getlist('acessos[]')
        status = request.POST.get('status', 'on') == 'on'
        
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        
        with transaction.atomic():
            grupo = GroupsAcessos.objects.create(
                titulo=titulo,
                descricao=descricao if descricao else None,
                status=status
            )
            
            if acessos_ids:
                acessos = Acesso.objects.filter(id__in=acessos_ids, status=True)
                grupo.acessos.set(acessos)
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{titulo}" criado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["GET", "POST"])
def api_editar_grupo(request, grupo_id):
    """API GET/POST para editar grupo"""
    grupo = get_object_or_404(GroupsAcessos, id=grupo_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'data': {
                'id': grupo.id,
                'titulo': grupo.titulo,
                'descricao': grupo.descricao or '',
                'acessos_ids': list(grupo.acessos.values_list('id', flat=True)),
                'status': grupo.status
            }
        })
    
    try:
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        acessos_ids = request.POST.getlist('acessos[]')
        status = request.POST.get('status', 'on') == 'on'
        
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        
        with transaction.atomic():
            grupo.titulo = titulo
            grupo.descricao = descricao if descricao else None
            grupo.status = status
            grupo.save()
            
            if acessos_ids:
                acessos = Acesso.objects.filter(id__in=acessos_ids, status=True)
                grupo.acessos.set(acessos)
            else:
                grupo.acessos.clear()
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{titulo}" atualizado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_deletar_grupo(request, grupo_id):
    """API POST para deletar grupo"""
    try:
        grupo = get_object_or_404(GroupsAcessos, id=grupo_id)
        titulo = grupo.titulo
        grupo.delete()
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{titulo}" deletado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# ========== TAB 3: CRUD ControleAcessos ==========

@login_required
@controle_acess('SS20')
@require_http_methods(["GET"])
def api_listar_controles(request):
    """API GET para listar todos os controles de acesso"""
    try:
        controles = ControleAcessos.objects.select_related('user').prefetch_related('acessos').all().order_by('user__username')
        controles_data = []
        for controle in controles:
            controles_data.append({
                'id': controle.id,
                'user_id': controle.user.id,
                'username': controle.user.username,
                'user_full_name': f"{controle.user.first_name} {controle.user.last_name}".strip() or controle.user.username,
                'acessos_ids': list(controle.acessos.values_list('id', flat=True)),
                'acessos_count': controle.acessos.count(),
                'status': controle.status,
                'data_criacao': controle.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'data_atualizacao': controle.data_atualizacao.strftime('%d/%m/%Y %H:%M')
            })
        return JsonResponse(controles_data, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["GET"])
def api_get_controle_usuario(request, user_id):
    """API GET para obter controle de acesso de um usuário específico"""
    try:
        user = get_object_or_404(User, id=user_id)
        controle, created = ControleAcessos.objects.get_or_create(
            user=user,
            defaults={'status': True}
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': controle.id,
                'user_id': user.id,
                'username': user.username,
                'acessos_ids': list(controle.acessos.values_list('id', flat=True)),
                'status': controle.status,
                'created': created
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_salvar_permissoes_usuario(request, user_id):
    """API POST para salvar permissões de um usuário (manual ou por grupo)"""
    try:
        user = get_object_or_404(User, id=user_id)
        acessos_ids = request.POST.getlist('acessos[]')
        aplicar_grupo_id = request.POST.get('aplicar_grupo', '').strip()
        
        with transaction.atomic():
            controle, created = ControleAcessos.objects.get_or_create(
                user=user,
                defaults={'status': True}
            )
            
            if aplicar_grupo_id:
                # Aplicar grupo de permissões
                grupo = get_object_or_404(GroupsAcessos, id=aplicar_grupo_id, status=True)
                controle.acessos.set(grupo.acessos.filter(status=True))
                mensagem = f'Grupo "{grupo.titulo}" aplicado ao usuário "{user.username}" com sucesso!'
            else:
                # Aplicar permissões manuais
                if acessos_ids:
                    acessos = Acesso.objects.filter(id__in=acessos_ids, status=True)
                    controle.acessos.set(acessos)
                else:
                    controle.acessos.clear()
                mensagem = f'Permissões do usuário "{user.username}" atualizadas com sucesso!'
            
            controle.status = True
            controle.save()
        
        return JsonResponse({
            'success': True,
            'message': mensagem
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# ========== TAB 4: Permissões em Lote ==========

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_aplicar_lote(request):
    """API POST para adicionar ou remover permissões em vários usuários de uma vez"""
    try:
        usuarios_ids = request.POST.getlist('usuarios[]')
        acessos_ids = request.POST.getlist('acessos[]')
        acao = request.POST.get('acao', 'adicionar').strip().lower()

        if not usuarios_ids:
            return JsonResponse({'success': False, 'message': 'Selecione pelo menos um usuário'})

        if not acessos_ids:
            return JsonResponse({'success': False, 'message': 'Selecione pelo menos uma permissão'})

        if acao not in ('adicionar', 'remover'):
            return JsonResponse({'success': False, 'message': 'Ação inválida'})

        usuarios = User.objects.filter(id__in=usuarios_ids, is_active=True)
        acessos = Acesso.objects.filter(id__in=acessos_ids, status=True)

        if not usuarios.exists():
            return JsonResponse({'success': False, 'message': 'Nenhum usuário válido encontrado'})

        if not acessos.exists():
            return JsonResponse({'success': False, 'message': 'Nenhuma permissão válida encontrada'})

        usuarios_processados = 0

        with transaction.atomic():
            for usuario in usuarios:
                controle, _ = ControleAcessos.objects.get_or_create(
                    user=usuario,
                    defaults={'status': True}
                )

                if not controle.status:
                    controle.status = True
                    controle.save(update_fields=['status'])

                if acao == 'adicionar':
                    controle.acessos.add(*acessos)
                else:
                    controle.acessos.remove(*acessos)

                usuarios_processados += 1

        verbo = 'adicionada(s)' if acao == 'adicionar' else 'removida(s)'
        return JsonResponse({
            'success': True,
            'message': (
                f'{acessos.count()} permissão(ões) {verbo} para '
                f'{usuarios_processados} usuário(s) com sucesso!'
            ),
            'data': {
                'usuarios': usuarios_processados,
                'permissoes': acessos.count(),
                'acao': acao
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_deletar_controle(request, controle_id):
    """API POST para deletar controle de acesso"""
    try:
        controle = get_object_or_404(ControleAcessos, id=controle_id)
        username = controle.user.username
        controle.delete()
        return JsonResponse({
            'success': True,
            'message': f'Controle de acesso do usuário "{username}" removido com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

