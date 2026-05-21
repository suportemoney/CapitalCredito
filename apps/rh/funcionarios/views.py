"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.rh.admin.models import Empresa, Loja, Departamento, Setor, Equipe, Cargo
from apps.rh.funcionarios.models import HorarioTrabalho, Genero, TipoContrato
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.models import GroupsAcessos

@login_required
@controle_acess('SS18')
def render_index(request):
    """Página inicial do módulo de funcionários"""
    return render(request, 'funcionarios/index.html')

@login_required
@controle_acess('SS17')
def render_novo(request):
    """Página para cadastrar novo funcionário"""
    empresas = Empresa.objects.filter(status=True).order_by('nome')
    departamentos = Departamento.objects.filter(status=True).order_by('nome')
    setores = Setor.objects.filter(status=True).order_by('nome')
    lojas = Loja.objects.filter(status=True).order_by('nome')
    equipes = Equipe.objects.filter(status=True).order_by('nome')
    cargos = Cargo.objects.filter(status=True).select_related('nivel_hierarquico').order_by('nivel_hierarquico__importancia', 'nome')
    horarios = HorarioTrabalho.objects.filter(status=True).order_by('nome')
    grupos = GroupsAcessos.objects.filter(status=True).order_by('titulo')
    context = {
        'empresas': empresas,
        'departamentos': departamentos,
        'setores': setores,
        'lojas': lojas,
        'equipes': equipes,
        'cargos': cargos,
        'horarios': horarios,
        'grupos': grupos,
    }
    return render(request, 'funcionarios/novo.html', context)

@login_required
@controle_acess('SS18')
def render_gerenciar(request):
    """Página para gerenciar funcionários com filtros"""
    empresas = Empresa.objects.filter(status=True).order_by('nome')
    departamentos = Departamento.objects.filter(status=True).order_by('nome')
    setores = Setor.objects.filter(status=True).order_by('nome')
    lojas = Loja.objects.filter(status=True).order_by('nome')
    equipes = Equipe.objects.filter(status=True).order_by('nome')
    cargos = Cargo.objects.filter(status=True).select_related('nivel_hierarquico').order_by('nivel_hierarquico__importancia', 'nome')
    horarios = HorarioTrabalho.objects.filter(status=True).order_by('nome')
    generos = Genero.objects.filter(status=True).order_by('nome')
    tipos_contrato = TipoContrato.objects.filter(status=True).order_by('nome')
    grupos = GroupsAcessos.objects.filter(status=True).order_by('titulo')
    context = {
        'empresas': empresas,
        'departamentos': departamentos,
        'setores': setores,
        'lojas': lojas,
        'equipes': equipes,
        'cargos': cargos,
        'horarios': horarios,
        'generos': generos,
        'tipos_contrato': tipos_contrato,
        'grupos': grupos,
    }
    return render(request, 'funcionarios/gerenciar.html', context)
