from django.contrib import admin
from .models import BonificacaoRegra, BonificacaoGatilho, BonificacaoFuncionarioRegra, ReducaoBonificacaoRegra, ReducaoBonificacaoFuncionario, BonificacaoCalculada

@admin.register(BonificacaoRegra)
class BonificacaoRegraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_regra', 'campo_valor', 'percentual_padrao', 'ativo', 'data_criacao')
    list_filter = ('tipo_regra', 'campo_valor', 'ativo')
    search_fields = ('nome',)

@admin.register(BonificacaoGatilho)
class BonificacaoGatilhoAdmin(admin.ModelAdmin):
    list_display = ('regra', 'valor_minimo', 'percentual', 'valor_fixo', 'ordem', 'ativo')
    list_filter = ('regra', 'ativo')

@admin.register(BonificacaoFuncionarioRegra)
class BonificacaoFuncionarioRegraAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'regra', 'ativo', 'data_inicio', 'data_fim', 'prioridade')
    list_filter = ('regra', 'ativo')

@admin.register(ReducaoBonificacaoRegra)
class ReducaoBonificacaoRegraAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'percentual', 'ordem', 'ativo')

@admin.register(ReducaoBonificacaoFuncionario)
class ReducaoBonificacaoFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'regra_reducao', 'data_evento', 'data_criacao')
    list_filter = ('regra_reducao',)

@admin.register(BonificacaoCalculada)
class BonificacaoCalculadaAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'regra', 'periodo_inicio', 'periodo_fim', 'valor_base', 'valor_bonificacao', 'valor_bonificacao_final', 'data_calculo')
    list_filter = ('regra',)
