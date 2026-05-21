from django.contrib import admin
from .models import (
    Produto,
    Campanha,
    Cliente,
    Matricula,
    Margens,
    Contrato,
    TabulacaoCRM,
    ControleCRM,
    MetaSIAPE,
    Representante,
    DadosReversao,
    ArquivoReversao,
    DadosChecagem,
    ArquivoChecagem,
    HorarioDisponivel
)

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome', 'descricao')
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo',)
    readonly_fields = ('data_criacao',)
    ordering = ('-data_criacao',)

class MargensInline(admin.StackedInline):
    model = Margens
    extra = 0
    can_delete = False

class ContratoInline(admin.TabularInline):
    model = Contrato
    extra = 0

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'cpf', 'uf', 'tipo_base', 'situacao_funcional', 'status', 'data_criacao')
    list_filter = ('tipo_base', 'status', 'uf', 'data_criacao')
    search_fields = ('nome', 'cpf')
    readonly_fields = ('data_criacao',)
    ordering = ('nome',)

@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('id', 'matricula', 'cliente', 'campanha', 'orgao', 'base_calculo', 'status', 'data_criacao')
    list_filter = ('status', 'campanha', 'orgao', 'data_criacao')
    search_fields = ('matricula', 'cliente__nome', 'cliente__cpf')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    inlines = [MargensInline, ContratoInline]
    ordering = ('-data_criacao',)

@admin.register(Margens)
class MargensAdmin(admin.ModelAdmin):
    list_display = ('id', 'matricula', 'bruta_5', 'util_5', 'saldo_5', 'bruta_5b', 'util_5b', 'saldo_5b', 'bruta_35', 'util_35', 'saldo_35')
    list_filter = ('matricula__campanha',)
    search_fields = ('matricula__matricula', 'matricula__cliente__nome')
    readonly_fields = ()

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato', 'matricula', 'tipo_contrato', 'banco', 'valor_parcela', 'parcelas_restantes', 'campanha')
    list_filter = ('tipo_contrato', 'banco', 'campanha')
    search_fields = ('contrato', 'matricula__matricula', 'matricula__cliente__nome')
    readonly_fields = ()

@admin.register(TabulacaoCRM)
class TabulacaoCRMAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'ordem', 'cor', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('nome',)
    readonly_fields = ('data_criacao',)
    ordering = ('ordem', 'nome')

@admin.register(ControleCRM)
class ControleCRMAdmin(admin.ModelAdmin):
    list_display = ('id', 'cpf', 'cliente_nome_display', 'tabulacao', 'user', 'data_contato', 'hora_contato', 'status', 'data_criacao')
    list_filter = ('tabulacao', 'status', 'data_contato', 'data_criacao')
    search_fields = ('cpf', 'user__username')
    readonly_fields = ('data_criacao',)
    ordering = ('-data_criacao',)
    
    def cliente_nome_display(self, obj):
        from apps.vendas.siape.models import Cliente
        cliente = Cliente.objects.filter(cpf=obj.cpf, status=True).first()
        return cliente.nome if cliente else 'Cliente não encontrado'
    cliente_nome_display.short_description = 'Nome do Cliente'

@admin.register(MetaSIAPE)
class MetaSIAPEAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'valor_meta', 'data_inicio', 'data_final', 'status', 'data_criacao')
    list_filter = ('status', 'data_inicio', 'data_final', 'data_criacao')
    search_fields = ('titulo',)
    readonly_fields = ('data_criacao',)
    ordering = ('-data_inicio', 'titulo')

@admin.register(Representante)
class RepresentanteAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'usuarios_count', 'status', 'data_criacao')
    list_filter = ('tipo', 'status', 'data_criacao')
    search_fields = ('tipo',)
    readonly_fields = ('data_criacao',)
    filter_horizontal = ('usuarios',)
    ordering = ('tipo', '-data_criacao')
    
    def usuarios_count(self, obj):
        return obj.usuarios.count()
    usuarios_count.short_description = 'Quantidade de Usuários'

@admin.register(DadosReversao)
class DadosReversaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'controle', 'data_para_reversao', 'horario_disponivel', 'responsavel_por_reversao', 'data_criacao')
    list_filter = ('data_para_reversao', 'data_criacao')
    search_fields = ('controle__cpf', 'responsavel_por_reversao__username')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    ordering = ('-data_criacao',)

@admin.register(ArquivoReversao)
class ArquivoReversaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'reversao', 'titulo', 'data_criacao')
    list_filter = ('data_criacao',)
    search_fields = ('titulo', 'reversao__controle__cpf')
    readonly_fields = ('data_criacao',)
    ordering = ('-data_criacao',)

@admin.register(DadosChecagem)
class DadosChecagemAdmin(admin.ModelAdmin):
    list_display = ('id', 'controle', 'data_para_checagem', 'horario_disponivel', 'responsavel_por_checagem', 'nome_banco', 'data_criacao')
    list_filter = ('data_para_checagem', 'data_criacao')
    search_fields = ('controle__cpf', 'responsavel_por_checagem__username', 'nome_banco')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    ordering = ('-data_criacao',)

@admin.register(ArquivoChecagem)
class ArquivoChecagemAdmin(admin.ModelAdmin):
    list_display = ('id', 'checagem', 'titulo', 'data_criacao')
    list_filter = ('data_criacao',)
    search_fields = ('titulo', 'checagem__controle__cpf')
    readonly_fields = ('data_criacao',)
    ordering = ('-data_criacao',)

@admin.register(HorarioDisponivel)
class HorarioDisponivelAdmin(admin.ModelAdmin):
    list_display = ('id', 'controle_crm', 'data', 'hora', 'responsavel', 'tabulacao', 'status', 'data_criacao')
    list_filter = ('data', 'status', 'tabulacao', 'data_criacao')
    search_fields = ('controle_crm__cpf', 'responsavel__username')
    readonly_fields = ('data_criacao',)
    ordering = ('-data', '-hora')
