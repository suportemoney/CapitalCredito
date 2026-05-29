"""
Decorators para controle de acesso em views.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.utils import user_has_access, user_has_any_access, get_user_home_url

def controle_acess(code):
    """
    Decorator para views que requerem permissão específica.
    
    Uso:
        @controle_acess('CT1')
        def minha_view(request):
            ...
    
    Se o usuário não tiver permissão, será redirecionado para a página inicial
    com mensagem de erro.
    
    Args:
        code: Código de acesso no formato TIPO + ID (ex: 'CT1', 'SCT5')
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if user_has_access(request.user, code):
                return view_func(request, *args, **kwargs)
            
            # Usuário não tem permissão
            messages.error(
                request, 
                'Você não tem permissão para acessar esta página.'
            )
            return redirect(get_user_home_url(request.user))
        
        return _wrapped
    return decorator

def controle_acess_any(*codes):
    """Decorator para views que requerem pelo menos uma das permissões."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if user_has_any_access(request.user, list(codes)):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect(get_user_home_url(request.user))
        return _wrapped
    return decorator

