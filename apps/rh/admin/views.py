"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Empresa, Loja, NivelHierarquico, Cargo, Departamento, Setor, Equipe
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS16')
def render_index(request):
    """Página inicial do módulo administrativo"""
    empresas_count = Empresa.objects.filter(status=True).count()
    lojas_count = Loja.objects.filter(status=True).count()
    departamentos_count = Departamento.objects.filter(status=True).count()
    setores_count = Setor.objects.filter(status=True).count()
    cargos_count = Cargo.objects.filter(status=True).count()
    equipes_count = Equipe.objects.filter(status=True).count()
    niveis_count = NivelHierarquico.objects.filter(status=True).count()
    
    context = {
        'empresas_count': empresas_count,
        'lojas_count': lojas_count,
        'departamentos_count': departamentos_count,
        'setores_count': setores_count,
        'cargos_count': cargos_count,
        'equipes_count': equipes_count,
        'niveis_count': niveis_count,
    }
    return render(request, 'rh_admin/index.html', context)

@login_required
@controle_acess('SS16')
def render_gerenciar(request):
    """Página única de gerenciamento com tabs para todos os modelos"""
    empresas = Empresa.objects.all().order_by('nome')
    lojas = Loja.objects.all().order_by('nome')
    departamentos = Departamento.objects.all().order_by('nome')
    setores = Setor.objects.all().order_by('nome')
    cargos = Cargo.objects.select_related('nivel_hierarquico').all().order_by('nivel_hierarquico__importancia', 'nome')
    equipes = Equipe.objects.all().order_by('nome')
    niveis = NivelHierarquico.objects.filter(status=True).order_by('-importancia')
    
    context = {
        'empresas': empresas,
        'lojas': lojas,
        'departamentos': departamentos,
        'setores': setores,
        'cargos': cargos,
        'equipes': equipes,
        'niveis': niveis,
        'niveis_ativos': niveis,  # Para usar no JavaScript
    }
    return render(request, 'rh_admin/gerenciar.html', context)
