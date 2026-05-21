from django.contrib import admin
from .models import (
    Acesso,
    AcessoHierarquia,
    GroupsAcessos,
    ControleAcessos
)

@admin.register(Acesso)
class AcessoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'tipo', 'gerar_codigo', 'status', 'data_criacao')
    list_filter = ('tipo', 'status', 'data_criacao')
    search_fields = ('nome', 'descricao')
    readonly_fields = ('data_criacao', 'codigo_acesso')
    ordering = ('tipo', 'nome')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'tipo', 'descricao', 'status')
        }),
        ('Código de Acesso', {
            'fields': ('codigo_acesso',),
            'classes': ('collapse',)
        }),
    )
    
    def codigo_acesso(self, obj):
        if obj.pk:
            return obj.gerar_codigo()
        return "Salve o acesso para gerar o código"
    codigo_acesso.short_description = 'Código de Acesso'

@admin.register(AcessoHierarquia)
class AcessoHierarquiaAdmin(admin.ModelAdmin):
    list_display = ('id', 'pai', 'filhos_count', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('pai__nome',)
    readonly_fields = ('data_criacao',)
    filter_horizontal = ('filhos',)
    ordering = ('pai__nome',)
    
    def filhos_count(self, obj):
        return obj.filhos.count()
    filhos_count.short_description = 'Quantidade de Filhos'

@admin.register(GroupsAcessos)
class GroupsAcessosAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'acessos_count', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo', 'descricao')
    readonly_fields = ('data_criacao',)
    filter_horizontal = ('acessos',)
    ordering = ('titulo',)
    
    def acessos_count(self, obj):
        return obj.acessos.count()
    acessos_count.short_description = 'Quantidade de Acessos'

@admin.register(ControleAcessos)
class ControleAcessosAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'acessos_count', 'status', 'data_criacao', 'data_atualizacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    filter_horizontal = ('acessos',)
    ordering = ('user__username',)
    
    def acessos_count(self, obj):
        return obj.acessos.count()
    acessos_count.short_description = 'Quantidade de Acessos'
