from django.contrib import admin
from .models import (
    CategoriaComunicado,
    Comunicado,
    ArquivoComunicado,
    VisualizacaoComunicado
)

class ArquivoComunicadoInline(admin.TabularInline):
    model = ArquivoComunicado
    extra = 0

@admin.register(CategoriaComunicado)
class CategoriaComunicadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'cor', 'icone', 'ordem', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome', 'descricao')
    readonly_fields = ('data_criacao',)
    ordering = ('ordem', 'nome')

@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'tipo', 'categoria', 'prioridade', 'fixo', 'status', 'criado_por', 'data_criacao')
    list_filter = ('tipo', 'prioridade', 'fixo', 'status', 'categoria', 'data_criacao')
    search_fields = ('titulo', 'conteudo')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    inlines = [ArquivoComunicadoInline]
    ordering = ('-fixo', '-prioridade', '-data_criacao')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('titulo', 'tipo', 'categoria', 'prioridade', 'conteudo')
        }),
        ('Mídia e Evento', {
            'fields': ('banner', 'data_evento')
        }),
        ('Configurações', {
            'fields': ('fixo', 'status', 'criado_por')
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ArquivoComunicado)
class ArquivoComunicadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'comunicado', 'titulo', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo', 'comunicado__titulo')
    readonly_fields = ('data_criacao',)
    ordering = ('-data_criacao',)

@admin.register(VisualizacaoComunicado)
class VisualizacaoComunicadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'comunicado', 'usuario', 'visualizado', 'data_visualizacao')
    list_filter = ('visualizado', 'data_visualizacao')
    search_fields = ('comunicado__titulo', 'usuario__username')
    readonly_fields = ('data_visualizacao',)
    ordering = ('-data_visualizacao',)
