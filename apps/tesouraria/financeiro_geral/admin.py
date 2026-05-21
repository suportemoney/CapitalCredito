from django.contrib import admin
from .models import CategoriaConta, SubcategoriaConta, TipoBeneficio, Conta, Salario, Beneficio, BonificacaoAPagar, ContaReceber

@admin.register(CategoriaConta)
class CategoriaContaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'status')
    list_filter = ('status',)

@admin.register(SubcategoriaConta)
class SubcategoriaContaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'status')
    list_filter = ('categoria', 'status')

@admin.register(TipoBeneficio)
class TipoBeneficioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'status')
    list_filter = ('status',)

@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'categoria', 'valor', 'data_vencimento', 'pago', 'data_pagamento')
    list_filter = ('pago', 'categoria')

@admin.register(Salario)
class SalarioAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'funcionario', 'valor', 'data_vencimento', 'pago', 'data_pagamento')
    list_filter = ('pago',)

@admin.register(Beneficio)
class BeneficioAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'funcionario', 'tipo_beneficio', 'valor', 'data_vencimento', 'pago', 'data_pagamento')
    list_filter = ('pago', 'tipo_beneficio')

@admin.register(BonificacaoAPagar)
class BonificacaoAPagarAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'valor_bonificacao', 'mes_referente', 'data_pagamento', 'status_pagamento', 'status_ativo')
    list_filter = ('status_pagamento', 'status_ativo')

@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'data_prevista', 'recebido', 'data_recebimento')
    list_filter = ('recebido',)
