from django.contrib import admin
from .models import (
    Genero,
    TipoContrato,
    HorarioTrabalho,
    Funcionario,
    DadosPessoais,
    Contato,
    Localizacao,
    DadosProfissionais,
    Arquivos
)

@admin.register(Genero)
class GeneroAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'icone', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(TipoContrato)
class TipoContratoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(HorarioTrabalho)
class HorarioTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'entrada', 'saida_almoco', 'volta_almoco', 'saida', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

class DadosPessoaisInline(admin.StackedInline):
    model = DadosPessoais
    extra = 0
    can_delete = False

class ContatoInline(admin.StackedInline):
    model = Contato
    extra = 0
    can_delete = False

class LocalizacaoInline(admin.StackedInline):
    model = Localizacao
    extra = 0
    can_delete = False

class DadosProfissionaisInline(admin.StackedInline):
    model = DadosProfissionais
    extra = 0
    can_delete = False
    filter_horizontal = ('lojas',)

class ArquivosInline(admin.TabularInline):
    model = Arquivos
    extra = 0

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_completo', 'cpf', 'apelido', 'usuario', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome_completo', 'cpf', 'apelido', 'usuario__username')
    readonly_fields = ('data_criacao',)
    inlines = [DadosPessoaisInline, ContatoInline, LocalizacaoInline, DadosProfissionaisInline, ArquivosInline]
    ordering = ('nome_completo',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome_completo', 'cpf', 'rg', 'data_nascimento', 'apelido', 'foto', 'usuario', 'status')
        }),
    )

@admin.register(Arquivos)
class ArquivosAdmin(admin.ModelAdmin):
    list_display = ('id', 'funcionario', 'titulo', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo', 'funcionario__nome_completo')
    readonly_fields = ('data_criacao',)
    ordering = ('-data_criacao',)
