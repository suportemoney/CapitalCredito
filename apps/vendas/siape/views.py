"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS24')
def render_ranking(request):
    """Página de ranking do módulo SIAPE - Ranking de INSS"""
    return render(request, 'siape/ranking.html')

@login_required
@controle_acess('SS25')
def render_consulta(request):
    """Página de consulta de cliente SIAPE"""
    return render(request, 'siape/index.html')

@login_required
@controle_acess('SS25')
def render_campanhas(request):
    """Página de campanhas com importação CSV"""
    return render(request, 'siape/campanhas.html')

@login_required
@controle_acess('SS26')
def render_crm(request):
    """Página do CRM Kanban"""
    return render(request, 'siape/crm.html')

@login_required
@controle_acess('SS28')
def render_produtos(request):
    """Página de gerenciamento de produtos"""
    return render(request, 'siape/produtos.html')

@login_required
@controle_acess('SS30')
def render_metas(request):
    """Página de gerenciamento de metas SIAPE"""
    return render(request, 'siape/metas.html')

@login_required
@controle_acess('SS31')
def render_responsaveis(request):
    """Página de gerenciamento de responsáveis de reversão e checagem"""
    return render(request, 'siape/responsaveis.html')
