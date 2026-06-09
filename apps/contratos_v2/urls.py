# -*- coding: utf-8 -*-
from django.urls import path

from . import views
from .apis import acoes_crm, bancos_logos, config_catalogos, dashboard_operacional, fluxo, relatorio_cms

app_name = 'contratos'

urlpatterns = [
    path('', views.render_contratos_index, name='index'),
    path('crm-operacional/', views.render_crm_operacional_v2, name='crm_operacional_v2'),
    path('dashboard-operacional/', views.render_dashboard_operacional_v2, name='dashboard_operacional_v2'),
    path('config/', views.render_config_contratos_v2, name='config_v2'),
    # APIs fluxo v2
    path('api/v2/fila-operacional/', fluxo.api_get_fila_operacional, name='api_v2_fila_operacional'),
    path('api/v2/solicitacoes-pendentes/', fluxo.api_get_solicitacoes_pendentes_operacional, name='api_v2_solicitacoes_pendentes'),
    path('api/v2/solicitacao-proposta/', fluxo.api_post_solicitacao_proposta_inicial, name='api_v2_solicitacao_proposta'),
    path('api/v2/solicitacao-proposta/responder/', fluxo.api_post_responder_solicitacao_proposta, name='api_v2_responder_solicitacao'),
    path('api/v2/solicitacao-proposta/<int:solicitacao_id>/propostas/', fluxo.api_get_propostas_solicitacao_operacional, name='api_v2_solicitacao_proposta_propostas'),
    path('api/v2/solicitar-digitacao/', fluxo.api_post_solicitar_digitacao, name='api_v2_solicitar_digitacao'),
    path('api/v2/solicitar-digitacao-sem-pdf/', fluxo.api_post_solicitar_digitacao_sem_pdf, name='api_v2_solicitar_digitacao_sem_pdf'),
    path('api/v2/simulacao/enviar-propostas-digitacao/', fluxo.api_post_enviar_propostas_simuladas_para_digitacao, name='api_v2_simulacao_enviar_propostas_digitacao'),
    path('api/v2/propostas-por-carteira/', fluxo.api_get_propostas_dados_por_carteira, name='api_v2_propostas_carteira'),
    path('api/v2/propostas-container/', fluxo.api_get_propostas_container, name='api_v2_propostas_container'),
    path('api/v2/catalogos/', fluxo.api_get_catalogos_contrato, name='api_v2_catalogos'),
    path('api/v2/bancos-logos/', bancos_logos.api_get_bancos_logos, name='api_v2_bancos_logos'),
    path('api/v2/tabelas-cms/', fluxo.api_get_tabelas_cms_por_solicitacao, name='api_v2_tabelas_cms_por_solicitacao'),
    path('api/v2/fila-unificada/', fluxo.api_get_fila_unificada, name='api_v2_fila_unificada'),
    path('api/v2/esteira-resumo/', fluxo.api_get_esteira_resumo, name='api_v2_esteira_resumo'),
    path('api/v2/dashboard/visao-geral/', dashboard_operacional.api_dashboard_visao_geral, name='api_v2_dashboard_visao_geral'),
    path('api/v2/dashboard/esteira/', dashboard_operacional.api_dashboard_esteira, name='api_v2_dashboard_esteira'),
    path('api/v2/dashboard/producao/', dashboard_operacional.api_dashboard_producao, name='api_v2_dashboard_producao'),
    path('api/v2/dashboard/pendencias/', dashboard_operacional.api_dashboard_pendencias, name='api_v2_dashboard_pendencias'),
    path('api/v2/auditoria-fluxo/', fluxo.api_get_auditoria_fluxo, name='api_v2_auditoria_fluxo'),
    path('api/v2/ficha/', fluxo.api_get_ficha, name='api_v2_ficha'),
    path('api/v2/ficha/pdf/', fluxo.api_get_ficha_pdf, name='api_v2_ficha_pdf'),
    path('api/v2/transicoes-disponiveis/', fluxo.api_get_transicoes_disponiveis, name='api_v2_transicoes_disponiveis'),
    path('api/v2/evoluir/', fluxo.api_post_evoluir, name='api_v2_evoluir'),
    path('api/v2/contrato/gerar-digitacao/', fluxo.api_post_gerar_contrato_digitacao, name='api_v2_gerar_contrato_digitacao'),
    path('api/v2/contrato/<int:contrato_id>/dados-cms-snapshot/', fluxo.api_patch_contrato_dados_cms_snapshot, name='api_v2_contrato_dados_cms_snapshot'),
    path('api/v2/contrato/<int:contrato_id>/definir-link-formalizacao/', fluxo.api_post_definir_link_formalizacao, name='api_v2_definir_link'),
    path('api/v2/contrato/<int:contrato_id>/upload-video/', fluxo.api_post_upload_video_contrato, name='api_v2_upload_video'),
    path(
        'api/v2/contrato/<int:contrato_id>/refin-port-defaults/',
        fluxo.api_get_refin_port_defaults,
        name='api_v2_refin_port_defaults',
    ),
    path('api/v2/contrato/<int:contrato_id>/midia-arquivos/', fluxo.api_get_contrato_midia_arquivos, name='api_v2_contrato_midia_arquivos'),
    path('api/v2/solicitacao-dig/<int:solicitacao_id>/midia-arquivos/', fluxo.api_get_solicitacao_dig_midia_arquivos, name='api_v2_solicitacao_dig_midia_arquivos'),
    path('api/v2/solicitacao-dig/<int:solicitacao_id>/cliente-arquivo/', fluxo.api_post_solicitacao_dig_cliente_arquivo, name='api_v2_solicitacao_dig_cliente_arquivo'),
    path(
        'api/v2/solicitacao-dig/<int:solicitacao_id>/correcao-concluida/',
        fluxo.api_post_solicitacao_dig_correcao_concluida,
        name='api_v2_solicitacao_dig_correcao_concluida',
    ),
    path('api/v2/contrato/<int:contrato_id>/cliente-arquivo/', fluxo.api_post_contrato_cliente_arquivo, name='api_v2_contrato_cliente_arquivo'),
    path(
        'api/v2/contrato/<int:contrato_id>/ranking-supervisor-context/',
        fluxo.api_get_ranking_supervisor_context,
        name='api_v2_ranking_supervisor_context',
    ),
    path(
        'api/v2/contrato/<int:contrato_id>/ranking-supervisor/',
        fluxo.api_post_ranking_supervisor,
        name='api_v2_ranking_supervisor',
    ),
    path(
        'api/v2/contrato/<int:contrato_id>/comprovante-pagamento-vendedor/',
        fluxo.api_post_contrato_comprovante_pagamento_vendedor,
        name='api_v2_contrato_comprovante_pagamento_vendedor',
    ),
    path('api/v2/contrato/<int:contrato_id>/transicao/', fluxo.api_post_contrato_transicao, name='api_v2_contrato_transicao'),
    path('api/v2/supervisao-contratos/', fluxo.api_get_supervisao_contratos_v2, name='api_v2_supervisao_contratos'),
    # Endpoints step-by-step: modais independentes de Simulação e Propostas
    path('api/v2/cliente-dados-pessoais/lookup/', fluxo.api_get_cliente_dados_pessoais_lookup, name='api_v2_cliente_dp_lookup'),
    path('api/v2/cliente-dados-pessoais/salvar/', fluxo.api_post_cliente_dados_pessoais_salvar, name='api_v2_cliente_dp_salvar'),
    path('api/v2/solicitar-simulacao/', fluxo.api_post_solicitar_simulacao, name='api_v2_solicitar_simulacao'),
    path('api/v2/solicitar-propostas/', fluxo.api_post_solicitar_propostas, name='api_v2_solicitar_propostas'),
    # APIs config catálogos (SS37)
    path('api/v2/config/resumo/', config_catalogos.api_get_config_resumo, name='api_v2_config_resumo'),
    path('api/v2/config/dependencias/', config_catalogos.api_get_catalogo_dependencias, name='api_v2_config_dependencias'),
    path('api/v2/config/banco/', config_catalogos.api_post_banco, name='api_v2_config_banco_post'),
    path('api/v2/config/banco/<int:pk>/', config_catalogos.api_detail_banco, name='api_v2_config_banco_detail'),
    path('api/v2/config/convenio/', config_catalogos.api_post_convenio, name='api_v2_config_convenio_post'),
    path('api/v2/config/convenio/<int:pk>/', config_catalogos.api_detail_convenio, name='api_v2_config_convenio_detail'),
    path('api/v2/config/produto/', config_catalogos.api_post_produto, name='api_v2_config_produto_post'),
    path('api/v2/config/produto/<int:pk>/', config_catalogos.api_detail_produto, name='api_v2_config_produto_detail'),
    path('api/v2/config/tabela-cms/', config_catalogos.api_post_tabela_cms, name='api_v2_config_tabela_cms_post'),
    path('api/v2/config/tabela-cms/<int:pk>/', config_catalogos.api_detail_tabela_cms, name='api_v2_config_tabela_cms_detail'),
    path('api/v2/config/importar/', config_catalogos.api_post_importar_csv, name='api_v2_config_importar'),
    path('api/v2/config/logs/', config_catalogos.api_get_config_logs, name='api_v2_config_logs'),
    # Exclusão definitiva (SS37)
    path('api/v2/config/banco/<int:pk>/excluir/', config_catalogos.api_delete_banco, name='api_v2_config_banco_excluir'),
    path('api/v2/config/convenio/<int:pk>/excluir/', config_catalogos.api_delete_convenio, name='api_v2_config_convenio_excluir'),
    path('api/v2/config/produto/<int:pk>/excluir/', config_catalogos.api_delete_produto, name='api_v2_config_produto_excluir'),
    path('api/v2/solicitacao/<int:pk>/excluir/', fluxo.api_delete_solicitacao, name='api_v2_solicitacao_excluir'),
    path('api/v2/contrato/<int:pk>/excluir/', fluxo.api_delete_contrato, name='api_v2_contrato_excluir'),

    # Filtro dinâmico de TabelaCms por (banco, convênio, produto) no modal de envio de proposta
    path('api/v2/tabelas-cms-filtradas/', fluxo.api_get_tabelas_cms_filtradas, name='api_v2_tabelas_cms_filtradas'),

    # Ações CRM: editar dados, pendências, comprovantes TC
    path('api/v2/contrato/editar-dados/', acoes_crm.api_post_editar_dados_contrato, name='api_v2_editar_dados_contrato'),
    path('api/v2/cliente-arquivo/excluir/', acoes_crm.api_post_excluir_cliente_arquivo, name='api_v2_cliente_arquivo_excluir'),
    path('api/v2/pendencia/', acoes_crm.api_post_criar_pendencia, name='api_v2_pendencia_criar'),
    path('api/v2/pendencia/resolver/', acoes_crm.api_post_resolver_pendencia, name='api_v2_pendencia_resolver'),
    path('api/v2/pendencia/sanar/', acoes_crm.api_post_sanar_pendencias_contrato, name='api_v2_pendencia_sanar'),
    path('api/v2/pendencias/', acoes_crm.api_get_pendencias_contrato, name='api_v2_pendencias_listar'),
    path('api/v2/comprovante-tc/', acoes_crm.api_post_comprovante_tc, name='api_v2_comprovante_tc_post'),
    path(
        'api/v2/comprovante-tc/excluir/',
        acoes_crm.api_post_excluir_comprovante_tc,
        name='api_v2_comprovante_tc_excluir',
    ),
    path(
        'api/v2/comprovante-tc/from-envio-vendedor/',
        acoes_crm.api_post_comprovante_tc_from_envio_vendedor,
        name='api_v2_comprovante_tc_from_envio_vendedor',
    ),
    path('api/v2/atualizar-tc-modal-pago/', acoes_crm.api_post_atualizar_tc_modal_pago, name='api_v2_atualizar_tc_modal_pago'),
    path(
        'api/v2/salvar-dados-pago-tc-modal/',
        acoes_crm.api_post_salvar_dados_pago_tc_modal,
        name='api_v2_salvar_dados_pago_tc_modal',
    ),
    path('api/v2/comprovantes-tc/', acoes_crm.api_get_comprovantes_tc, name='api_v2_comprovantes_tc_get'),

    # Relatório CMS (Financeiro)
    path('relatorio-cms/', views.render_relatorio_cms, name='relatorio_cms'),
    path('api/v2/relatorio-cms/', relatorio_cms.api_get_relatorio_cms_lista, name='api_v2_relatorio_cms_lista'),
    path('api/v2/relatorio-cms/meta/', relatorio_cms.api_get_relatorio_cms_meta, name='api_v2_relatorio_cms_meta'),
    path('api/v2/relatorio-cms/pago-cms-empresa/', relatorio_cms.api_post_marcar_pago_cms_empresa, name='api_v2_relatorio_cms_marcar_pago'),
    path('api/v2/relatorio-cms/ajustar-af/', relatorio_cms.api_post_ajustar_percentual_af, name='api_v2_relatorio_cms_ajustar_af'),
]
