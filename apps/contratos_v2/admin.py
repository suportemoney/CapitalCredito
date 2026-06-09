# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db import transaction
from django.utils.html import format_html

from apps.contratos_v2.models import (
    Banco,
    ClienteArquivo,
    ClienteBancario,
    ClienteContato,
    ClienteContatoDinamico,
    ClienteDadosPessoais,
    ClienteEndereco,
    ClienteEnderecoDinamico,
    ClienteRepresentante,
    ComprovanteTC,
    ContratoDadosOperacionais,
    ContratoExecucao,
    ContratoPortado,
    Convenio,
    EnvioComprovantePagamentoVendedor,
    HistoricoEventoDigitacao,
    HistoricoEventoSimulacao,
    HistoricoTransacaoContrato,
    HistoricoTransacaoProposta,
    HistoricoTransacaoSimulacao,
    HistoricoTransicaoContrato,
    LogCatalogoContratos,
    Pendencia,
    Produto,
    PropostaDados,
    Simulacao,
    SolicitacaoDigitacao,
    SolicitacaoPropostaCliente,
    TabelaCms,
    TagStatusOperacional,
)


# --- Inlines (auditoria / vínculos) ---


class HistoricoTransicaoContratoInline(admin.TabularInline):
    model = HistoricoTransicaoContrato
    extra = 0
    readonly_fields = ('etapa_anterior', 'sub_anterior', 'etapa_nova', 'sub_nova', 'usuario', 'observacao', 'data')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class HistoricoEventoDigitacaoInline(admin.TabularInline):
    model = HistoricoEventoDigitacao
    extra = 0
    readonly_fields = ('estado_anterior', 'estado_novo', 'usuario', 'observacao', 'data')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class HistoricoEventoSimulacaoInline(admin.TabularInline):
    model = HistoricoEventoSimulacao
    extra = 0
    readonly_fields = ('estado_anterior', 'estado_novo', 'usuario', 'observacao', 'data')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ContratoPortadoInline(admin.TabularInline):
    model = ContratoPortado
    extra = 0
    raw_id_fields = ('contrato_execucao', 'banco')


class PendenciaInline(admin.TabularInline):
    model = Pendencia
    extra = 0
    readonly_fields = ('criado_em', 'resolvido_em')
    raw_id_fields = ('criado_por', 'resolvido_por')


class ComprovanteTCInline(admin.TabularInline):
    model = ComprovanteTC
    extra = 0
    readonly_fields = ('criado_em',)
    raw_id_fields = ('criado_por',)


class EnvioComprovantePagamentoVendedorInline(admin.TabularInline):
    model = EnvioComprovantePagamentoVendedor
    extra = 0
    readonly_fields = ('criado_em',)
    raw_id_fields = ('enviado_por',)


class ClienteContatoDinamicoInline(admin.TabularInline):
    model = ClienteContatoDinamico
    extra = 0


class ClienteEnderecoDinamicoInline(admin.TabularInline):
    model = ClienteEnderecoDinamico
    extra = 0


# --- Cliente / catálogo ---


@admin.register(ClienteDadosPessoais)
class ClienteDadosPessoaisAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'cpf', 'data_criacao')
    search_fields = ('nome_completo', 'cpf')
    list_filter = ('data_criacao',)
    inlines = (ClienteContatoDinamicoInline, ClienteEnderecoDinamicoInline)


@admin.register(ClienteContato)
class ClienteContatoAdmin(admin.ModelAdmin):
    list_display = ('cliente_dados_pessoais', 'email', 'telefone')
    raw_id_fields = ('cliente_dados_pessoais',)


@admin.register(ClienteEndereco)
class ClienteEnderecoAdmin(admin.ModelAdmin):
    list_display = ('cliente_dados_pessoais', 'cep', 'logradouro')
    raw_id_fields = ('cliente_dados_pessoais',)


@admin.register(ClienteBancario)
class ClienteBancarioAdmin(admin.ModelAdmin):
    list_display = ('cliente_dados_pessoais', 'proposta_dados', 'banco', 'agencia', 'conta')
    raw_id_fields = ('cliente_dados_pessoais', 'proposta_dados', 'contrato_execucao')


@admin.register(ClienteRepresentante)
class ClienteRepresentanteAdmin(admin.ModelAdmin):
    list_display = ('cliente_dados_pessoais', 'nome_representante', 'cpf_representante')
    raw_id_fields = ('cliente_dados_pessoais',)


@admin.register(ClienteArquivo)
class ClienteArquivoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'cliente_dados_pessoais', 'tipo', 'data_criacao', 'status')
    list_filter = ('tipo', 'status')
    raw_id_fields = ('cliente_dados_pessoais',)


@admin.register(ClienteContatoDinamico)
class ClienteContatoDinamicoAdmin(admin.ModelAdmin):
    list_display = ('cliente_dados_pessoais', 'tipo', 'valor')
    list_filter = ('tipo',)
    search_fields = ('valor', 'cliente_dados_pessoais__nome_completo', 'cliente_dados_pessoais__cpf')
    raw_id_fields = ('cliente_dados_pessoais',)


@admin.register(ClienteEnderecoDinamico)
class ClienteEnderecoDinamicoAdmin(admin.ModelAdmin):
    list_display = ('cliente_dados_pessoais', 'cep', 'logradouro', 'principal')
    list_filter = ('principal',)
    raw_id_fields = ('cliente_dados_pessoais',)


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'codigo', 'dominio', 'nome_curto', 'tem_logo', 'status', 'data_criacao')
    list_filter = ('status',)
    search_fields = ('titulo', 'codigo', 'dominio', 'nome_curto')
    readonly_fields = ('logo_preview',)
    actions = ['action_sincronizar_logo']

    @admin.display(boolean=True, description='Logo')
    def tem_logo(self, obj):
        return bool(obj.logo or obj.logo_url)

    @admin.display(description='Prévia')
    def logo_preview(self, obj):
        url = obj.logo_exibicao_url
        if not url:
            return '—'
        return format_html('<img src="{}" alt="" style="max-height:48px">', url)

    @admin.action(description='Sincronizar logo (Brandfetch / Logo.dev)')
    def action_sincronizar_logo(self, request, queryset):
        from apps.contratos_v2.services import banco_logo as logo_svc

        ok = 0
        for b in queryset:
            logo_svc.aplicar_dominio_por_codigo_ou_titulo(b)
            sucesso, _ = logo_svc.sincronizar_logo_banco(b, forcar=False)
            if sucesso:
                ok += 1
        self.message_user(request, f'{ok} logo(s) sincronizado(s).')


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'status', 'data_criacao')
    list_filter = ('status',)
    search_fields = ('titulo',)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'flag_port_mais_refin',
        'flag_refin_da_port',
        'status',
        'data_criacao',
    )
    list_filter = ('status', 'flag_port_mais_refin', 'flag_refin_da_port')
    search_fields = ('titulo',)


@admin.register(TabelaCms)
class TabelaCmsAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'banco', 'convenio', 'produto', 'status')
    list_filter = ('status', 'banco', 'convenio')
    search_fields = ('titulo',)


# --- Esteira: simulação, proposta, digitação, contrato ---


@admin.register(SolicitacaoPropostaCliente)
class SolicitacaoPropostaClienteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'carteira_clientes',
        'cliente_dados_pessoais',
        'estado',
        'criado_por',
        'data_criacao',
        'data_resposta',
    )
    list_filter = ('estado',)
    search_fields = (
        'cliente_dados_pessoais__nome_completo',
        'cliente_dados_pessoais__cpf',
    )
    raw_id_fields = (
        'carteira_clientes',
        'cliente_dados_pessoais',
        'criado_por',
        'respondido_por',
    )
    inlines = (HistoricoEventoSimulacaoInline,)


@admin.register(PropostaDados)
class PropostaDadosAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'cliente_dados_pessoais',
        'banco',
        'convenio',
        'produto',
        'aceita_pelo_cliente',
        'criado_por',
        'data_criacao',
    )
    list_filter = ('aceita_pelo_cliente', 'banco', 'convenio')
    search_fields = (
        'codigo',
        'cliente_dados_pessoais__nome_completo',
        'cliente_dados_pessoais__cpf',
    )
    raw_id_fields = (
        'cliente_dados_pessoais',
        'solicitacao_origem',
        'banco',
        'convenio',
        'produto',
        'tabela_cms',
        'criado_por',
        'proposta_vinculo_port',
    )
    inlines = (ContratoPortadoInline,)

    def _excluir_contratos_execucao_vinculados(self, proposta_ids):
        # ContratoExecucao aponta para PropostaDados com PROTECT; é preciso apagar o contrato antes da proposta.
        ids = {pk for pk in proposta_ids if pk is not None}
        if not ids:
            return
        ContratoExecucao.objects.filter(proposta_dados_id__in=ids).delete()

    def delete_model(self, request, obj):
        with transaction.atomic():
            self._excluir_contratos_execucao_vinculados([obj.pk])
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        ids = list(queryset.values_list('pk', flat=True))
        with transaction.atomic():
            self._excluir_contratos_execucao_vinculados(ids)
            super().delete_queryset(request, queryset)


@admin.register(ContratoPortado)
class ContratoPortadoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'proposta_dados',
        'contrato_execucao',
        'banco',
        'numero_contrato',
        'valor_af',
        'data_criacao',
    )
    raw_id_fields = ('proposta_dados', 'contrato_execucao', 'banco')
    search_fields = ('numero_contrato', 'proposta_dados__codigo')


@admin.register(SolicitacaoDigitacao)
class SolicitacaoDigitacaoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'proposta_dados',
        'carteira_clientes',
        'estado',
        'criado_por',
        'data_criacao',
    )
    list_filter = ('estado',)
    search_fields = (
        'proposta_dados__codigo',
        'carteira_clientes__cliente__nome',
        'carteira_clientes__cliente__cpf',
    )
    raw_id_fields = ('proposta_dados', 'carteira_clientes', 'criado_por')
    inlines = (HistoricoEventoDigitacaoInline,)


@admin.register(Simulacao)
class SimulacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_dados_pessoais', 'titulo', 'criado_por', 'status', 'data_criacao')
    list_filter = ('status',)
    search_fields = ('titulo', 'cliente_dados_pessoais__nome_completo', 'cliente_dados_pessoais__cpf')
    raw_id_fields = ('cliente_dados_pessoais', 'criado_por')


@admin.register(HistoricoTransicaoContrato)
class HistoricoTransicaoContratoAdmin(admin.ModelAdmin):
    list_display = ('contrato_execucao', 'etapa_nova', 'sub_nova', 'usuario', 'data')
    list_filter = ('etapa_nova',)
    search_fields = ('contrato_execucao__codigo',)
    raw_id_fields = ('contrato_execucao', 'usuario')
    readonly_fields = (
        'contrato_execucao',
        'etapa_anterior',
        'sub_anterior',
        'etapa_nova',
        'sub_nova',
        'usuario',
        'observacao',
        'data',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HistoricoEventoSimulacao)
class HistoricoEventoSimulacaoAdmin(admin.ModelAdmin):
    list_display = ('solicitacao', 'estado_novo', 'usuario', 'data')
    list_filter = ('estado_novo',)
    raw_id_fields = ('solicitacao', 'usuario')
    readonly_fields = ('solicitacao', 'estado_anterior', 'estado_novo', 'usuario', 'observacao', 'data')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HistoricoEventoDigitacao)
class HistoricoEventoDigitacaoAdmin(admin.ModelAdmin):
    list_display = ('solicitacao', 'estado_novo', 'usuario', 'data')
    list_filter = ('estado_novo',)
    raw_id_fields = ('solicitacao', 'usuario')
    readonly_fields = ('solicitacao', 'estado_anterior', 'estado_novo', 'usuario', 'observacao', 'data')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ContratoExecucao)
class ContratoExecucaoAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'col_nome_cliente',
        'col_numero_proposta',
        'proposta_dados',
        'etapa_operacional',
        'sub_status_operacional',
        'fase',
        'portabilidade',
        'destaque_vendedor',
        'status',
        'data_ultima_atualizacao',
    )
    list_filter = (
        'fase',
        'etapa_operacional',
        'sub_status_operacional',
        'status',
        'portabilidade',
        'destaque_vendedor',
        'nivel_risco_checagem_supervisor',
        'tag_financeira',
    )
    search_fields = (
        'codigo',
        'cliente_dados_pessoais__nome_completo',
        'cliente_dados_pessoais__cpf',
        'proposta_dados__codigo',
    )
    raw_id_fields = (
        'proposta_dados',
        'cliente_dados_pessoais',
        'solicitacao_digitacao',
        'simulacao_origem',
        'contrato_vinculo_port',
    )
    inlines = (
        HistoricoTransicaoContratoInline,
        PendenciaInline,
        ComprovanteTCInline,
        EnvioComprovantePagamentoVendedorInline,
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cliente_dados_pessoais', 'proposta_dados')

    @admin.display(description='Cliente', ordering='cliente_dados_pessoais__nome_completo')
    def col_nome_cliente(self, obj):
        if obj.cliente_dados_pessoais_id:
            return obj.cliente_dados_pessoais.nome_completo or '—'
        return '—'

    @admin.display(description='Nº proposta (token)', ordering='proposta_dados__codigo')
    def col_numero_proposta(self, obj):
        if obj.proposta_dados_id:
            return obj.proposta_dados.codigo or '—'
        return '—'


@admin.register(Pendencia)
class PendenciaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'contrato_execucao',
        'tipo',
        'resolvido',
        'criado_por',
        'criado_em',
        'resolvido_por',
        'resolvido_em',
    )
    list_filter = ('tipo', 'resolvido')
    search_fields = ('contrato_execucao__codigo', 'observacao')
    raw_id_fields = ('contrato_execucao', 'criado_por', 'resolvido_por')


@admin.register(EnvioComprovantePagamentoVendedor)
class EnvioComprovantePagamentoVendedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato_execucao', 'titulo', 'enviado_por', 'criado_em')
    list_filter = ('criado_em',)
    search_fields = ('titulo', 'contrato_execucao__codigo', 'enviado_por__username')
    raw_id_fields = ('contrato_execucao', 'enviado_por')
    readonly_fields = ('criado_em',)


@admin.register(ComprovanteTC)
class ComprovanteTCAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato_execucao', 'valor', 'criado_por', 'status', 'criado_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('contrato_execucao__codigo',)
    raw_id_fields = ('contrato_execucao', 'criado_por')
    readonly_fields = ('criado_em',)


@admin.register(ContratoDadosOperacionais)
class ContratoDadosOperacionaisAdmin(admin.ModelAdmin):
    list_display = (
        'contrato_execucao',
        'banco',
        'convenio',
        'produto',
        'tabela_cms',
        'valor_af',
        'valor_tc',
    )
    raw_id_fields = (
        'contrato_execucao',
        'banco',
        'convenio',
        'produto',
        'tabela_cms',
        'user_att_cms',
    )
    search_fields = ('contrato_execucao__codigo', 'tabela_cms_titulo_snapshot')


@admin.register(TagStatusOperacional)
class TagStatusOperacionalAdmin(admin.ModelAdmin):
    list_display = ('carteira_clientes', 'tag', 'criado_por', 'data_criacao')
    list_filter = ('tag',)
    raw_id_fields = ('carteira_clientes', 'criado_por')


@admin.register(LogCatalogoContratos)
class LogCatalogoContratosAdmin(admin.ModelAdmin):
    list_display = ('data', 'acao', 'entidade', 'registro_id', 'registro_titulo', 'usuario')
    list_filter = ('acao', 'entidade', 'data')
    search_fields = ('registro_titulo', 'resumo', 'usuario__username')
    readonly_fields = (
        'acao', 'entidade', 'registro_id', 'registro_titulo', 'usuario', 'data',
        'dados_antes', 'dados_depois', 'resumo',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class _HistoricoTransacaoAdminBase(admin.ModelAdmin):
    """Base somente leitura — visível apenas para superusuários."""

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoricoTransacaoSimulacao)
class HistoricoTransacaoSimulacaoAdmin(_HistoricoTransacaoAdminBase):
    list_display = ('data_hora', 'acao', 'solicitacao', 'estado_novo', 'usuario', 'correlacao_id')
    list_filter = ('acao', 'data_hora')
    search_fields = ('solicitacao__id', 'correlacao_id', 'observacao')
    readonly_fields = (
        'correlacao_id', 'solicitacao', 'carteira_clientes', 'acao',
        'estado_anterior', 'estado_novo', 'payload', 'proposta_vinculada',
        'historico_evento', 'usuario', 'observacao', 'data_hora',
    )


@admin.register(HistoricoTransacaoProposta)
class HistoricoTransacaoPropostaAdmin(_HistoricoTransacaoAdminBase):
    list_display = ('data_hora', 'acao', 'proposta', 'contrato_vinculado', 'usuario', 'correlacao_id')
    list_filter = ('acao', 'data_hora')
    search_fields = ('proposta__codigo', 'correlacao_id', 'observacao')
    readonly_fields = (
        'correlacao_id', 'proposta', 'solicitacao_origem', 'carteira_clientes', 'acao',
        'payload', 'contrato_vinculado', 'historico_digitacao', 'usuario', 'observacao', 'data_hora',
    )


@admin.register(HistoricoTransacaoContrato)
class HistoricoTransacaoContratoAdmin(_HistoricoTransacaoAdminBase):
    list_display = ('data_hora', 'acao', 'contrato', 'etapa_nova', 'pendencia', 'usuario', 'correlacao_id')
    list_filter = ('acao', 'data_hora', 'etapa_nova')
    search_fields = ('contrato__codigo', 'correlacao_id', 'observacao')
    readonly_fields = (
        'correlacao_id', 'contrato', 'proposta_origem', 'solicitacao_digitacao', 'carteira_clientes',
        'acao', 'etapa_anterior', 'sub_anterior', 'etapa_nova', 'sub_nova', 'payload',
        'pendencia', 'historico_transicao', 'usuario', 'observacao', 'data_hora',
    )
