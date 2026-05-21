from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import (
    TipoUsuario, Banco, Convenio, Operacao,
    BancoConvenio, ConvenioOperacao, BancoConvenioOperacao, SchemaCampo,
    TabelaComissao, RegraComissao,
    TabulacaoContrato, ContratoOperacional, AnexoContrato
)

@admin.register(TipoUsuario)
class TipoUsuarioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'status', 'data_criacao']
    list_filter = ['status']
    search_fields = ['nome', 'descricao']

@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'status', 'data_criacao']
    list_filter = ['status']
    search_fields = ['nome', 'codigo']

@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'status', 'data_criacao']
    list_filter = ['status']
    search_fields = ['nome', 'codigo']

@admin.register(Operacao)
class OperacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'status', 'data_criacao']
    list_filter = ['status']
    search_fields = ['nome', 'codigo']

@admin.register(BancoConvenio)
class BancoConvenioAdmin(admin.ModelAdmin):
    list_display = ['banco', 'convenio', 'ativo', 'data_ativacao', 'data_criacao']
    list_filter = ['ativo', 'banco', 'convenio']
    search_fields = ['banco__nome', 'convenio__nome']

@admin.register(ConvenioOperacao)
class ConvenioOperacaoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'convenio', 'operacao', 'data_criacao']
    list_filter = ['convenio', 'operacao']
    search_fields = ['titulo', 'convenio__nome', 'operacao__nome']


@admin.register(BancoConvenioOperacao)
class BancoConvenioOperacaoAdmin(admin.ModelAdmin):
    list_display = ['banco', 'convenio_operacao', 'ativo', 'data_ativacao', 'data_criacao']
    list_filter = ['ativo', 'banco', 'convenio_operacao__convenio', 'convenio_operacao__operacao']
    search_fields = ['banco__nome', 'convenio_operacao__titulo', 'convenio_operacao__convenio__nome', 'convenio_operacao__operacao__nome']
    raw_id_fields = ['convenio_operacao']

@admin.register(SchemaCampo)
class SchemaCampoAdmin(admin.ModelAdmin):
    list_display = ['convenio_operacao', 'label', 'type', 'category', 'required', 'ordem']
    list_filter = ['type', 'category', 'required', 'convenio_operacao']
    search_fields = ['label', 'category']
    ordering = ['convenio_operacao', 'ordem']

@admin.register(TabelaComissao)
class TabelaComissaoAdmin(admin.ModelAdmin):
    list_display = ['banco_convenio', 'nome_tabela', 'nome_produto', 'operacao', 'status']
    list_filter = ['status', 'operacao']
    search_fields = ['nome_tabela', 'nome_produto']

@admin.register(RegraComissao)
class RegraComissaoAdmin(admin.ModelAdmin):
    list_display = ['tabela_comissao', 'tipo_regra', 'vigencia_inicio', 'vigencia_fim']
    list_filter = ['tipo_regra']
    search_fields = ['tabela_comissao__nome_tabela']

@admin.register(TabulacaoContrato)
class TabulacaoContratoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ordem', 'cor', 'status', 'data_criacao']
    list_filter = ['status']
    search_fields = ['nome']
    ordering = ['ordem']

class AnexoContratoInline(admin.TabularInline):
    model = AnexoContrato
    extra = 0
    readonly_fields = ['arquivo', 'titulo', 'tipo_documento', 'data_criacao']
    can_delete = False
    fields = ['titulo', 'tipo_documento', 'arquivo', 'data_criacao']

@admin.register(ContratoOperacional)
class ContratoOperacionalAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'id', 'banco', 'vendedor', 'status_tabulacao', 'is_rascunho', 'data_criacao']
    list_filter = ['status_tabulacao', 'banco', 'is_rascunho', 'data_criacao']
    search_fields = ['numero_serie', 'vendedor__username', 'vendedor__first_name', 'vendedor__last_name']
    readonly_fields = ['numero_serie', 'data_criacao', 'data_atualizacao', 'dados_contrato_display', 'arquivos_display']
    inlines = [AnexoContratoInline]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('numero_serie', 'banco', 'convenio_operacao', 'vendedor', 'operador', 'status_tabulacao')
        }),
        ('Status', {
            'fields': ('is_rascunho', 'pagina_atual', 'cliente_formalizou', 'link_formalizacao')
        }),
        ('Observações', {
            'fields': ('observacoes', 'observacoes_incompleto')
        }),
        ('Arquivos', {
            'fields': ('video_cliente', 'video_tamanho', 'arquivos_display')
        }),
        ('Dados do Contrato', {
            'fields': ('dados_contrato_display',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_atualizacao', 'data_formalizacao', 'data_liberacao', 'data_pagamento')
        }),
    )
    
    def dados_contrato_display(self, obj):
        """Exibe os dados do contrato de forma legível"""
        if not obj.dados_contrato:
            return "Nenhum dado"
        import json
        return mark_safe(f"<pre>{json.dumps(obj.dados_contrato, indent=2, ensure_ascii=False)}</pre>")
    dados_contrato_display.short_description = "Dados do Contrato"
    
    def arquivos_display(self, obj):
        """Lista todos os arquivos salvos no dados_contrato"""
        if not obj.dados_contrato or not isinstance(obj.dados_contrato, dict):
            return "Nenhum arquivo"
        
        html = "<ul>"
        arquivos_encontrados = False
        for categoria, campos in obj.dados_contrato.items():
            if isinstance(campos, dict):
                for campo, valor in campos.items():
                    if isinstance(valor, str) and valor.startswith('/media/'):
                        arquivos_encontrados = True
                        nome_arquivo = valor.split('/')[-1]
                        html += f'<li><strong>{categoria}.{campo}:</strong> <a href="{valor}" target="_blank">{nome_arquivo}</a></li>'
        html += "</ul>"
        
        if not arquivos_encontrados:
            return "Nenhum arquivo encontrado no JSON"
        
        return mark_safe(html)
    arquivos_display.short_description = "Arquivos Anexados"

@admin.register(AnexoContrato)
class AnexoContratoAdmin(admin.ModelAdmin):
    list_display = ['contrato', 'titulo', 'tipo_documento', 'data_criacao']
    list_filter = ['tipo_documento', 'data_criacao']
    search_fields = ['titulo', 'contrato__id']
