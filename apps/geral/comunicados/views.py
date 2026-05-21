"""
Views para renderizar templates (apenas renders)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Comunicado, CategoriaComunicado, VisualizacaoComunicado
from django.utils import timezone
from django.db.models import Case, When, IntegerField

@login_required
def render_mural(request):
    """Renderiza o mural de comunicados - página inicial após login"""
    # Buscar comunicados ativos
    comunicados = Comunicado.objects.filter(status=True).select_related('categoria', 'criado_por').prefetch_related('arquivos')
    
    # Ordenar: fixos primeiro, depois por prioridade (urgente > alta > normal > baixa) e data
    comunicados = comunicados.annotate(
        prioridade_order=Case(
            When(prioridade='URGENTE', then=4),
            When(prioridade='ALTA', then=3),
            When(prioridade='NORMAL', then=2),
            When(prioridade='BAIXA', then=1),
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('-fixo', '-prioridade_order', '-data_criacao')
    
    # Marcar comunicados visualizados pelo usuário
    visualizacoes = VisualizacaoComunicado.objects.filter(
        usuario=request.user,
        visualizado=True
    ).values_list('comunicado_id', flat=True)
    
    # Adicionar flag de visualizado em cada comunicado
    for comunicado in comunicados:
        comunicado.visualizado = comunicado.id in visualizacoes
    
    categorias = CategoriaComunicado.objects.filter(status=True).order_by('ordem', 'nome')
    
    context = {
        'comunicados': comunicados,
        'categorias': categorias,
    }
    
    return render(request, 'comunicados/mural.html', context)

@login_required
def render_listar(request):
    """Lista todos os comunicados para gerenciamento"""
    comunicados = Comunicado.objects.all().select_related('categoria', 'criado_por').order_by('-data_criacao')
    
    # Filtros
    status_filter = request.GET.get('status', '')
    tipo_filter = request.GET.get('tipo', '')
    categoria_filter = request.GET.get('categoria', '')
    
    if status_filter == 'ativo':
        comunicados = comunicados.filter(status=True)
    elif status_filter == 'inativo':
        comunicados = comunicados.filter(status=False)
    
    if tipo_filter:
        comunicados = comunicados.filter(tipo=tipo_filter)
    
    if categoria_filter:
        comunicados = comunicados.filter(categoria_id=categoria_filter)
    
    categorias = CategoriaComunicado.objects.filter(status=True).order_by('ordem', 'nome')
    
    context = {
        'comunicados': comunicados,
        'categorias': categorias,
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'categoria_filter': categoria_filter,
        'TIPO_CHOICES': Comunicado.TIPO_CHOICES,
    }
    
    return render(request, 'comunicados/listar.html', context)

@login_required
def render_criar(request):
    """Formulário para criar novo comunicado"""
    categorias = CategoriaComunicado.objects.filter(status=True).order_by('ordem', 'nome')
    
    context = {
        'categorias': categorias,
        'TIPO_CHOICES': Comunicado.TIPO_CHOICES,
        'PRIORIDADE_CHOICES': Comunicado.PRIORIDADE_CHOICES,
    }
    
    return render(request, 'comunicados/criar.html', context)

@login_required
def render_editar(request, comunicado_id):
    """Formulário para editar comunicado existente"""
    comunicado = get_object_or_404(Comunicado, id=comunicado_id)
    categorias = CategoriaComunicado.objects.filter(status=True).order_by('ordem', 'nome')
    
    context = {
        'comunicado': comunicado,
        'categorias': categorias,
        'TIPO_CHOICES': Comunicado.TIPO_CHOICES,
        'PRIORIDADE_CHOICES': Comunicado.PRIORIDADE_CHOICES,
    }
    
    return render(request, 'comunicados/editar.html', context)
