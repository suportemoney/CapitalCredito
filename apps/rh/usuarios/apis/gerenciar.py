"""
APIs para gerenciar usuários Django
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import datetime

from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS19')
@require_http_methods(["GET"])
def api_listar_usuarios(request):
    """API GET para listar todos os usuários Django"""
    try:
        usuarios = User.objects.select_related('funcionario_profile').all().order_by('date_joined')
        
        usuarios_data = []
        for user in usuarios:
            # Verificar se está associado a um funcionário
            funcionario = None
            if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
                funcionario = {
                    'id': user.funcionario_profile.id,
                    'nome_completo': user.funcionario_profile.nome_completo,
                    'apelido': user.funcionario_profile.apelido or '',
                    'cpf': user.funcionario_profile.cpf
                }
            
            # Calcular senha padrão baseada no ano de criação
            ano_criacao = user.date_joined.year if user.date_joined else datetime.now().year
            senha_padrao = f"Capital@{ano_criacao}"
            
            usuarios_data.append({
                'id': user.id,
                'username': user.username,
                'senha_padrao': senha_padrao,
                'data_criacao': user.date_joined.strftime('%d/%m/%Y %H:%M') if user.date_joined else '-',
                'ano_criacao': ano_criacao,
                'funcionario': funcionario,
                'status': user.is_active,
                'email': user.email or '-',
                'first_name': user.first_name or '',
                'last_name': user.last_name or ''
            })
        
        return JsonResponse(usuarios_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar usuários: {str(e)}'}, status=500)

@login_required
@controle_acess('SS19')
@require_http_methods(["POST"])
def api_atualizar_status(request, user_id):
    """API POST para atualizar status (is_active) do usuário"""
    try:
        user = User.objects.get(id=user_id)
        status = request.POST.get('status', '').lower()
        
        if status == 'true' or status == '1' or status == 'on':
            user.is_active = True
        elif status == 'false' or status == '0' or status == 'off':
            user.is_active = False
        else:
            return JsonResponse({'success': False, 'message': 'Status inválido'})
        
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status do usuário "{user.username}" atualizado com sucesso!',
            'status': user.is_active
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Usuário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar status: {str(e)}'}, status=500)

