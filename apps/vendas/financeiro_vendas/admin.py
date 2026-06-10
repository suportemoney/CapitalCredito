from django.contrib import admin
from .models import (
    Classificador,
    ComprovanteTC,
    ContratoPagamento,
)


class ComprovanteTCInline(admin.TabularInline):
    model = ComprovanteTC
    extra = 0
    readonly_fields = ('criado_em', 'criado_por', 'comprovante_v2_id')
    fields = ('valor', 'arquivo', 'status', 'comprovante_v2_id', 'criado_por', 'criado_em')


@admin.register(Classificador)
class ClassificadorAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'percentual', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo',)
    readonly_fields = ('data_criacao',)
    ordering = ('titulo',)


@admin.register(ComprovanteTC)
class ComprovanteTCAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato_pagamento', 'valor', 'status', 'comprovante_v2_id', 'criado_por', 'criado_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('contrato_pagamento__cliente_nome', 'contrato_pagamento__cliente_cpf')
    readonly_fields = ('criado_em',)
    ordering = ('-criado_em',)


@admin.register(ContratoPagamento)
class ContratoPagamentoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'cliente_nome', 'cliente_cpf', 'user', 'produto', 'banco',
        'valor_af', 'valor_tc', 'valor_tc_acumulado', 'status',
        'data_contrato', 'data_pagamento', 'contrato_execucao', 'status_ativo', 'data_criacao',
    )
    list_filter = ('status', 'status_ativo', 'flg_ponta', 'flag_repasse', 'classificador', 'data_contrato', 'data_pagamento', 'data_criacao')
    search_fields = ('cliente_nome', 'cliente_cpf', 'user__username', 'produto__nome', 'banco')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    ordering = ('-data_contrato', '-data_criacao')
    inlines = [ComprovanteTCInline]
    fieldsets = (
        ('Informações do Contrato', {
            'fields': ('user', 'setor', 'produto', 'classificador', 'banco', 'data_contrato', 'status', 'contrato_execucao', 'flag_repasse')
        }),
        ('Informações do Cliente', {
            'fields': ('cliente_cpf', 'cliente_nome')
        }),
        ('Valores', {
            'fields': ('valor_af', 'valor_repasse', 'valor_tc', 'valor_tc_acumulado', 'flg_ponta')
        }),
        ('Pagamento', {
            'fields': ('data_pagamento',)
        }),
        ('Status', {
            'fields': ('status_ativo',)
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
