"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.rh.funcionarios.models import Funcionario, HorarioTrabalho
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS40')
def render_index(request):
    """Página principal de presença"""
    return render(request, 'ponto/index.html')

@login_required
@controle_acess('SS41')
def render_justificativas(request):
    """Página para admin criar justificativas"""
    funcionarios = Funcionario.objects.filter(status=True).order_by('nome_completo')
    context = {
        'funcionarios': funcionarios,
    }
    return render(request, 'ponto/justificativas.html', context)

@login_required
@controle_acess('SS42')
def render_relatorio(request):
    """Relatório de presença com filtros"""
    funcionarios = Funcionario.objects.filter(status=True).order_by('nome_completo')
    context = {
        'funcionarios': funcionarios,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'ponto/relatorio.html', context)

@login_required
@controle_acess('SS43')
def render_horario_trabalho(request):
    """Configurar horário de trabalho do funcionário"""
    funcionarios = Funcionario.objects.filter(status=True).order_by('nome_completo')
    context = {
        'funcionarios': funcionarios,
    }
    return render(request, 'ponto/horario_trabalho.html', context)
