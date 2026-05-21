from django.contrib import admin
from .models import (
    Classificador,
    ContratoPagamento
)

@admin.register(Classificador)
class ClassificadorAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'percentual', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    search_fields = ('titulo',)
    readonly_fields = ('data_criacao',)
    ordering = ('titulo',)

@admin.register(ContratoPagamento)
class ContratoPagamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_nome', 'cliente_cpf', 'user', 'produto', 'banco', 'valor_af', 'valor_repasse', 'status', 'data_contrato', 'data_pagamento', 'status_ativo', 'data_criacao')
    list_filter = ('status', 'status_ativo', 'flg_ponta', 'classificador', 'data_contrato', 'data_pagamento', 'data_criacao')
    search_fields = ('cliente_nome', 'cliente_cpf', 'user__username', 'produto__nome', 'banco')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    ordering = ('-data_contrato', '-data_criacao')
    fieldsets = (
        ('Informações do Contrato', {
            'fields': ('user', 'setor', 'produto', 'classificador', 'banco', 'data_contrato', 'status')
        }),
        ('Informações do Cliente', {
            'fields': ('cliente_cpf', 'cliente_nome')
        }),
        ('Valores', {
            'fields': ('valor_af', 'valor_repasse', 'flg_ponta')
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
