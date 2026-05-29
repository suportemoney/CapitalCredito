"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.utils import get_user_home_url

def render_login(request):
    """View para renderizar a página de login"""
    if request.user.is_authenticated:
        return redirect(get_user_home_url(request.user))
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo, {user.username}!')
                next_url = request.GET.get('next') or get_user_home_url(user)
                return redirect(next_url)
            else:
                messages.error(request, 'Usuário ou senha incorretos.')
        else:
            messages.error(request, 'Por favor, preencha todos os campos.')
    
    return render(request, 'usuarios/login.html')

def render_logout(request):
    """View para fazer logout"""
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('usuarios:render_login')

@login_required
def render_index(request):
    """Página inicial do módulo de usuários (requer login)"""
    return render(request, 'usuarios/index.html')

@login_required
def render_sem_acesso(request):
    """Página exibida quando o usuário não possui permissão para nenhuma área do sistema."""
    return render(request, 'usuarios/sem_acesso.html')

@login_required
@controle_acess('SS19')
def render_gerenciar(request):
    """Página para gerenciar usuários Django"""
    return render(request, 'usuarios/gerenciar.html')
