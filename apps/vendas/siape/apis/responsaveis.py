"""
APIs para gerenciar responsáveis de reversão e checagem
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import Representante
from django.contrib.auth.models import User
from apps.rh.funcionarios.models import Funcionario

logger = logging.getLogger(__name__)

@login_required
@controle_acess('SS31')
@require_http_methods(["GET"])
def api_listar_responsaveis(request):
    """API GET para listar responsáveis"""
    try:
        responsaveis = Representante.objects.all().order_by('tipo', '-data_criacao').prefetch_related('usuarios')
        data = []
        for resp in responsaveis:
            usuarios_list = []
            for user in resp.usuarios.filter(is_active=True):
                try:
                    nome = user.username
                    if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
                        nome = user.funcionario_profile.nome_completo
                    usuarios_list.append({
                        'id': user.id,
                        'nome': nome,
                        'username': user.username
                    })
                except Exception as e:
                    logger.error(f"[Responsáveis] Erro ao processar usuário {user.id} do responsável {resp.id}: {str(e)}")
                    continue
            
            data.append({
                'id': resp.id,
                'tipo': resp.tipo,
                'tipo_display': resp.get_tipo_display(),
                'usuarios': usuarios_list,
                'usuarios_count': len(usuarios_list),
                'horario_inicio': resp.horario_inicio.strftime('%H:%M') if resp.horario_inicio else None,
                'horario_final': resp.horario_final.strftime('%H:%M') if resp.horario_final else None,
                'tempo_call': resp.tempo_call,
                'status': resp.status,
                'data_criacao': resp.data_criacao.strftime('%d/%m/%Y %H:%M'),
            })
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[Responsáveis] Erro ao listar responsáveis: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar responsáveis: {str(e)}'}, status=500)

@login_required
@controle_acess('SS31')
@require_http_methods(["GET"])
def api_listar_usuarios_disponiveis(request):
    """API GET para listar usuários disponíveis para seleção"""
    try:
        usuarios = User.objects.filter(is_active=True).select_related('funcionario_profile')
        data = []
        for user in usuarios:
            try:
                nome = user.username
                if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
                    nome = user.funcionario_profile.nome_completo
                data.append({
                    'id': user.id,
                    'nome': nome,
                    'username': user.username
                })
            except Exception as e:
                logger.error(f"[Responsáveis] Erro ao processar usuário {user.id}: {str(e)}")
                continue
        
        data.sort(key=lambda x: x['nome'])
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[Responsáveis] Erro ao listar usuários disponíveis: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar usuários: {str(e)}'}, status=500)

@login_required
@controle_acess('SS31')
@require_http_methods(["POST"])
def api_criar_responsavel(request):
    """API POST para criar responsável"""
    try:
        tipo = request.POST.get('tipo', '').strip().upper()
        usuarios_ids = request.POST.getlist('usuarios')
        horario_inicio = request.POST.get('horario_inicio', '').strip()
        horario_final = request.POST.get('horario_final', '').strip()
        tempo_call = request.POST.get('tempo_call', '30').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not tipo or tipo not in ['REVERSAO', 'CHECAGEM']:
            return JsonResponse({'success': False, 'message': 'Tipo inválido. Use REVERSAO ou CHECAGEM.'})
        
        if not usuarios_ids:
            return JsonResponse({'success': False, 'message': 'Selecione pelo menos um usuário responsável.'})
        
        if not horario_inicio or not horario_final:
            return JsonResponse({'success': False, 'message': 'Preencha horário de início e final.'})
        
        try:
            from datetime import datetime
            horario_inicio_obj = datetime.strptime(horario_inicio, '%H:%M').time()
            horario_final_obj = datetime.strptime(horario_final, '%H:%M').time()
            tempo_call_int = int(tempo_call)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Formato de horário inválido. Use HH:MM.'})
        
        # Verificar se já existe um responsável ativo do mesmo tipo
        responsavel_existente = Representante.objects.filter(tipo=tipo, status=True).first()
        if responsavel_existente:
            # Adicionar usuários ao responsável existente
            usuarios = User.objects.filter(id__in=usuarios_ids, is_active=True)
            responsavel_existente.usuarios.add(*usuarios)
            responsavel_existente.horario_inicio = horario_inicio_obj
            responsavel_existente.horario_final = horario_final_obj
            responsavel_existente.tempo_call = tempo_call_int
            responsavel_existente.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Usuários adicionados ao responsável existente com sucesso!',
                'data': {
                    'id': responsavel_existente.id,
                    'tipo': responsavel_existente.tipo,
                    'tipo_display': responsavel_existente.get_tipo_display(),
                }
            })
        
        # Criar novo responsável
        responsavel = Representante.objects.create(
            tipo=tipo,
            horario_inicio=horario_inicio_obj,
            horario_final=horario_final_obj,
            tempo_call=tempo_call_int,
            status=status
        )
        
        usuarios = User.objects.filter(id__in=usuarios_ids, is_active=True)
        responsavel.usuarios.set(usuarios)
        
        usuarios_list = []
        for user in usuarios:
            try:
                nome = user.username
                if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
                    nome = user.funcionario_profile.nome_completo
                usuarios_list.append({
                    'id': user.id,
                    'nome': nome,
                    'username': user.username
                })
            except Exception as e:
                logger.error(f"[Responsáveis] Erro ao processar usuário {user.id}: {str(e)}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': 'Responsável criado com sucesso!',
            'data': {
                'id': responsavel.id,
                'tipo': responsavel.tipo,
                'tipo_display': responsavel.get_tipo_display(),
                'usuarios': usuarios_list,
                'usuarios_count': len(usuarios_list),
                'status': responsavel.status,
                'data_criacao': responsavel.data_criacao.strftime('%d/%m/%Y %H:%M'),
            }
        })
    except Exception as e:
        logger.error(f"[Responsáveis] Erro ao criar responsável: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao criar responsável: {str(e)}'}, status=500)

@login_required
@controle_acess('SS31')
@require_http_methods(["GET", "POST"])
def api_editar_responsavel(request, responsavel_id):
    """API para editar responsável"""
    try:
        responsavel = Representante.objects.get(id=responsavel_id)
        
        if request.method == 'GET':
            usuarios_list = []
            for user in responsavel.usuarios.filter(is_active=True):
                try:
                    nome = user.username
                    if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
                        nome = user.funcionario_profile.nome_completo
                    usuarios_list.append({
                        'id': user.id,
                        'nome': nome,
                        'username': user.username
                    })
                except Exception as e:
                    logger.error(f"[Responsáveis] Erro ao processar usuário {user.id}: {str(e)}")
                    continue
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': responsavel.id,
                    'tipo': responsavel.tipo,
                    'usuarios': usuarios_list,
                    'horario_inicio': responsavel.horario_inicio.strftime('%H:%M') if responsavel.horario_inicio else None,
                    'horario_final': responsavel.horario_final.strftime('%H:%M') if responsavel.horario_final else None,
                    'tempo_call': responsavel.tempo_call,
                    'status': responsavel.status,
                }
            })
        
        tipo = request.POST.get('tipo', '').strip().upper()
        usuarios_ids = request.POST.getlist('usuarios')
        horario_inicio = request.POST.get('horario_inicio', '').strip()
        horario_final = request.POST.get('horario_final', '').strip()
        tempo_call = request.POST.get('tempo_call', '30').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not usuarios_ids:
            return JsonResponse({'success': False, 'message': 'Selecione pelo menos um usuário responsável.'})
        
        if not horario_inicio or not horario_final:
            return JsonResponse({'success': False, 'message': 'Preencha horário de início e final.'})
        
        try:
            from datetime import datetime
            horario_inicio_obj = datetime.strptime(horario_inicio, '%H:%M').time()
            horario_final_obj = datetime.strptime(horario_final, '%H:%M').time()
            tempo_call_int = int(tempo_call)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Formato de horário inválido. Use HH:MM.'})
        
        usuarios = User.objects.filter(id__in=usuarios_ids, is_active=True)
        responsavel.usuarios.set(usuarios)
        responsavel.horario_inicio = horario_inicio_obj
        responsavel.horario_final = horario_final_obj
        responsavel.tempo_call = tempo_call_int
        responsavel.status = status
        responsavel.save()
        
        return JsonResponse({'success': True, 'message': 'Responsável atualizado com sucesso!'})
    except Representante.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Responsável não encontrado'}, status=404)
    except Exception as e:
        logger.error(f"[Responsáveis] Erro ao editar responsável: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao editar responsável: {str(e)}'}, status=500)

@login_required
@controle_acess('SS31')
@require_http_methods(["POST"])
def api_deletar_responsavel(request, responsavel_id):
    """API POST para deletar responsável"""
    try:
        responsavel = Representante.objects.get(id=responsavel_id)
        responsavel.delete()
        return JsonResponse({'success': True, 'message': 'Responsável deletado com sucesso!'})
    except Representante.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Responsável não encontrado'}, status=404)
    except Exception as e:
        logger.error(f"[Responsáveis] Erro ao deletar responsável: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao deletar responsável: {str(e)}'}, status=500)

