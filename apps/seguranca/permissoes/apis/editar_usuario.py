"""
APIs para o template editar_usuario.html
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.seguranca.permissoes.models import Acesso, ControleAcessos, GroupsAcessos
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_adicionar_acessos(request, user_id):
    """API para adicionar acessos a um usuário"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        acesso_ids = request.POST.getlist('acesso_ids[]')
        
        if not acesso_ids:
            return JsonResponse({'success': False, 'message': 'Nenhum acesso selecionado'})
        
        # Buscar ou criar ControleAcessos
        controle, created = ControleAcessos.objects.get_or_create(
            user=usuario,
            defaults={'status': True}
        )
        
        if not controle.status:
            controle.status = True
            controle.save()
        
        # Adicionar acessos
        acessos = Acesso.objects.filter(id__in=acesso_ids, status=True)
        controle.acessos.add(*acessos)
        
        return JsonResponse({
            'success': True,
            'message': f'{acessos.count()} permissão(ões) adicionada(s) com sucesso',
            'total': controle.acessos.filter(status=True).count()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_remover_acessos(request, user_id):
    """API para remover acessos de um usuário"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        acesso_ids = request.POST.getlist('acesso_ids[]')
        
        if not acesso_ids:
            return JsonResponse({'success': False, 'message': 'Nenhum acesso selecionado'})
        
        try:
            controle = ControleAcessos.objects.get(user=usuario, status=True)
            acessos = Acesso.objects.filter(id__in=acesso_ids)
            controle.acessos.remove(*acessos)
            
            return JsonResponse({
                'success': True,
                'message': f'{acessos.count()} permissão(ões) removida(s) com sucesso',
                'total': controle.acessos.filter(status=True).count()
            })
        except ControleAcessos.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Usuário não possui controle de acesso'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_aplicar_grupo(request, user_id):
    """API para aplicar um grupo de acessos a um usuário"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        grupo_id = request.POST.get('grupo_id')
        
        if not grupo_id:
            return JsonResponse({'success': False, 'message': 'Grupo não especificado'})
        
        grupo = get_object_or_404(GroupsAcessos, id=grupo_id, status=True)
        
        # Buscar ou criar ControleAcessos
        controle, created = ControleAcessos.objects.get_or_create(
            user=usuario,
            defaults={'status': True}
        )
        
        if not controle.status:
            controle.status = True
            controle.save()
        
        # Adicionar todos os acessos do grupo
        controle.acessos.add(*grupo.acessos.filter(status=True))
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{grupo.titulo}" aplicado com sucesso. {grupo.acessos.count()} permissão(ões) adicionada(s)',
            'total': controle.acessos.filter(status=True).count()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS20')
@require_http_methods(["POST"])
def api_salvar_permissoes(request, user_id):
    """API para salvar todas as permissões de uma vez (substitui as existentes)"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        acesso_ids = request.POST.getlist('acesso_ids[]')
        
        # Buscar ou criar ControleAcessos
        controle, created = ControleAcessos.objects.get_or_create(
            user=usuario,
            defaults={'status': True}
        )
        
        if not controle.status:
            controle.status = True
            controle.save()
        
        # Substituir todos os acessos
        acessos = Acesso.objects.filter(id__in=acesso_ids, status=True)
        controle.acessos.set(acessos)
        
        return JsonResponse({
            'success': True,
            'message': f'{acessos.count()} permissão(ões) salva(s) com sucesso',
            'total': acessos.count()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

