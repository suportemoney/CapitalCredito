from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.utils import user_has_access

@login_required
@controle_acess('SS45')
def render_bonificacoes(request):
    """Renderiza a página de configuração de bonificações (sem dados extras)."""
    return render(request, 'bonificacoes/bonificacoes.html')

@login_required
@controle_acess('SS46')
def render_calc_bonificacoes(request):
    """Renderiza a página só de cálculo por mês (Calc Bonificações)."""
    has_pago_cms = user_has_access(request.user, 'CX47')
    try:
        # Usa apenas o path relativo para evitar mixed content (https/http)
        criar_ja_paga_url = reverse('financeiro_geral:api_post_bonificacoes_pagar_criar_ja_paga')
    except NoReverseMatch:
        # Fallback explícito para o path configurado em setup/urls.py
        criar_ja_paga_url = '/tesouraria/financeiro/api/bonificacoes-pagar/criar-ja-paga/'
    return render(
        request,
        'bonificacoes/calc_bonificacoes.html',
        {'has_pago_cms': has_pago_cms, 'criar_ja_paga_url': criar_ja_paga_url},
    )
