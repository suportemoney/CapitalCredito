"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.utils import user_has_access
from apps.tesouraria.financeiro_geral.models import CategoriaConta, TipoBeneficio
from apps.rh.funcionarios.models import Funcionario

@login_required
@controle_acess('SS21')
def render_dashboard(request):
    """Dashboard geral: resumo A pagar e A receber."""
    return render(request, 'financeiro_geral/dashboard.html')

@login_required
@controle_acess('SS22')
def render_contas_a_pagar(request):
    """Contas a pagar: Contas (empresa), Salários, Benefícios."""
    categorias = CategoriaConta.objects.filter(status=True).order_by('nome')
    tipos_beneficio = TipoBeneficio.objects.filter(status=True).order_by('nome')
    funcionarios = Funcionario.objects.all().order_by('nome_completo')
    context = {
        'categorias': categorias,
        'tipos_beneficio': tipos_beneficio,
        'funcionarios': funcionarios,
        'is_superuser': request.user.is_superuser,
        # CX53: pode ver ícone e excluir contas a pagar
        'has_perm_delet': user_has_access(request.user, 'CX53'),
    }
    return render(request, 'financeiro_geral/contas_a_pagar.html', context)

@login_required
@controle_acess('SS23')
def render_gerenciar(request):
    """Gerenciador: categorias, subcategorias, tipos de benefício."""
    return render(request, 'financeiro_geral/gerenciar.html')

@login_required
def render_index(request):
    """Redireciona para o dashboard."""
    return redirect('financeiro_geral:dashboard')
