from django.contrib import admin

from .models import Equipe, StatusChoice
from .models_v2 import (
    AgendamentoV2,
    CampanhaV2,
    ClienteCampanhaV2,
    ControleClienteV2,
    ImportacaoCsvV2,
)


@admin.register(StatusChoice)
class StatusChoiceAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 'order', 'cor_tag', 'impacto', 'comportamento',
        'conversao', 'cpc', 'oportunidade', 'status_booleano', 'data_criacao',
    )
    search_fields = ('nome',)
    list_filter = (
        'status_booleano', 'impacto', 'comportamento',
        'conversao', 'cpc', 'oportunidade', 'data_criacao',
    )
    ordering = ('order', 'nome')

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'cor_tag', 'order', 'status_booleano'),
        }),
        ('Classificação', {
            'fields': ('impacto', 'comportamento'),
        }),
        ('Indicadores', {
            'fields': ('conversao', 'cpc', 'oportunidade'),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status_booleano:
            StatusChoice.objects.filter(nome=obj.nome).exclude(id=obj.id).update(status_booleano=False)


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'status', 'data_criacao')
    search_fields = ('nome',)
    filter_horizontal = ('participantes',)


@admin.register(CampanhaV2)
class CampanhaV2Admin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_campanha', 'status', 'data_criacao')
    list_filter = ('tipo_campanha', 'status')
    search_fields = ('nome',)
    filter_horizontal = ('equipes',)


@admin.register(ClienteCampanhaV2)
class ClienteCampanhaV2Admin(admin.ModelAdmin):
    list_display = ('cpf', 'tipo', 'campanha', 'data_criacao')
    list_filter = ('tipo', 'campanha')
    search_fields = ('cpf',)


@admin.register(ControleClienteV2)
class ControleClienteV2Admin(admin.ModelAdmin):
    list_display = ('cliente', 'user', 'campanha', 'tabulacao', 'status', 'updated_at')
    list_filter = ('campanha', 'status', 'tabulacao')
    search_fields = ('cliente__cpf', 'user__username')


@admin.register(AgendamentoV2)
class AgendamentoV2Admin(admin.ModelAdmin):
    list_display = ('controle', 'dia_agendamento', 'hora', 'responsavel', 'status')
    list_filter = ('status', 'dia_agendamento')


@admin.register(ImportacaoCsvV2)
class ImportacaoCsvV2Admin(admin.ModelAdmin):
    list_display = ('arquivo_nome', 'campanha', 'total_linhas', 'criado_por', 'data_criacao')
    list_filter = ('campanha',)
