"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Acesso, ControleAcessos, GroupsAcessos
from .decorators import controle_acess

@login_required
@controle_acess('SS20')  # Requer permissão para gerenciar permissões
def render_index(request):
    """Lista todos os usuários e suas permissões"""
    usuarios = User.objects.all().order_by('username')
    grupos = GroupsAcessos.objects.filter(status=True).order_by('titulo')
    
    # Buscar permissões de cada usuário
    usuarios_com_permissoes = []
    for usuario in usuarios:
        try:
            controle = ControleAcessos.objects.get(user=usuario, status=True)
            acessos = controle.acessos.filter(status=True)
            usuarios_com_permissoes.append({
                'usuario': usuario,
                'acessos': acessos,
                'total': acessos.count()
            })
        except ControleAcessos.DoesNotExist:
            usuarios_com_permissoes.append({
                'usuario': usuario,
                'acessos': [],
                'total': 0
            })
    
    # Organizar acessos por tipo
    acessos_por_tipo = {}
    for tipo, nome in Acesso.TIPO_CHOICES:
        acessos_por_tipo[tipo] = Acesso.objects.filter(tipo=tipo, status=True).order_by('nome')
    
    context = {
        'usuarios_com_permissoes': usuarios_com_permissoes,
        'grupos': grupos,
        'acessos_por_tipo': acessos_por_tipo,
    }
    
    return render(request, 'permissoes/index.html', context)

@login_required
@controle_acess('SS20')
def render_editar_usuario(request, user_id):
    """Página para editar permissões de um usuário específico"""
    usuario = get_object_or_404(User, id=user_id)
    
    # Buscar ou criar ControleAcessos
    controle, created = ControleAcessos.objects.get_or_create(
        user=usuario,
        defaults={'status': True}
    )
    
    acessos_usuario = controle.acessos.filter(status=True) if controle.status else []
    acessos_ids_usuario = list(acessos_usuario.values_list('id', flat=True))
    
    # Organizar acessos por tipo (usando lista de tuplas para manter ordem)
    acessos_por_tipo = []
    for tipo, nome in Acesso.TIPO_CHOICES:
        acessos = Acesso.objects.filter(tipo=tipo, status=True).order_by('nome')
        acessos_list = [
            {
                'acesso': acesso,
                'codigo': acesso.gerar_codigo(),
                'tem_acesso': acesso.id in acessos_ids_usuario
            }
            for acesso in acessos
        ]
        acessos_por_tipo.append({
            'tipo': tipo,
            'nome': nome,
            'acessos': acessos_list
        })
    
    grupos = GroupsAcessos.objects.filter(status=True).order_by('titulo')
    
    context = {
        'usuario': usuario,
        'controle': controle,
        'acessos_por_tipo': acessos_por_tipo,
        'acessos_ids_usuario': acessos_ids_usuario,
        'grupos': grupos,
        'TIPO_CHOICES': Acesso.TIPO_CHOICES,
    }
    
    return render(request, 'permissoes/editar_usuario.html', context)

@login_required
@controle_acess('SS20')
def render_gerenciar(request):
    """Página principal de gerenciamento de permissões com tabs"""
    usuarios = User.objects.all().order_by('username')
    grupos = GroupsAcessos.objects.filter(status=True).order_by('titulo')
    acessos = Acesso.objects.filter(status=True).order_by('tipo', 'nome')
    
    context = {
        'usuarios': usuarios,
        'grupos': grupos,
        'acessos': acessos,
        'TIPO_CHOICES': Acesso.TIPO_CHOICES,
    }
    
    return render(request, 'permissoes/gerenciar.html', context)
