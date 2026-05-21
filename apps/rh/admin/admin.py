from django.contrib import admin
from .models import (
    Empresa,
    Loja,
    NivelHierarquico,
    Cargo,
    Departamento,
    Setor,
    Equipe
)

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'cnpj', 'flg_parceira', 'status', 'data_criacao')
    list_filter = ('status', 'flg_parceira', 'data_criacao')
    search_fields = ('nome', 'cnpj')
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(Loja)
class LojaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'flg_sede', 'flg_filial', 'flg_franquia', 'status', 'data_criacao')
    list_filter = ('status', 'flg_sede', 'flg_filial', 'flg_franquia', 'data_criacao')
    search_fields = ('nome', 'endereco')
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(NivelHierarquico)
class NivelHierarquicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'importancia', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('-importancia', 'nome')

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'nivel_hierarquico', 'status', 'data_criacao')
    list_filter = ('status', 'nivel_hierarquico', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nivel_hierarquico__importancia', 'nome')

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)
