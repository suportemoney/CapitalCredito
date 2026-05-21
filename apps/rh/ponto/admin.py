from django.contrib import admin
from django.utils import timezone
from .models import RegistroPonto, Justificativa, JustificativaArquivo, ConfiguracaoHorarioFuncionario

@admin.register(RegistroPonto)
class RegistroPontoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'tipo', 'numero', 'data_hora_local', 'data', 'status')
    list_filter = ('tipo', 'data', 'status')
    search_fields = ('funcionario__nome_completo', 'funcionario__cpf')
    readonly_fields = ('data_criacao',)
    date_hierarchy = 'data'
    def data_hora_local(self, obj):
        if obj.data_hora:
            return timezone.localtime(obj.data_hora).strftime('%d/%m/%Y %H:%M:%S')
        return '-'
    data_hora_local.short_description = 'Data e Hora'

@admin.register(Justificativa)
class JustificativaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'funcionario', 'data_inicio', 'data_fim', 'status', 'criado_por')
    list_filter = ('tipo', 'status', 'data_inicio', 'data_fim')
    search_fields = ('titulo', 'funcionario__nome_completo')
    readonly_fields = ('data_criacao',)

@admin.register(JustificativaArquivo)
class JustificativaArquivoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'justificativa', 'data_criacao')
    list_filter = ('data_criacao',)
    search_fields = ('titulo', 'justificativa__titulo')

@admin.register(ConfiguracaoHorarioFuncionario)
class ConfiguracaoHorarioFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'horario_trabalho', 'trabalha_fim_semana', 'status')
    list_filter = ('trabalha_fim_semana', 'status')
    search_fields = ('funcionario__nome_completo',)
