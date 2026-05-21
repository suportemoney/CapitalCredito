from django.urls import path
from . import views
from .apis import gerenciar as apis_gerenciar
from .apis import schemas as apis_schemas
from .apis import contratos as apis_contratos
from .apis import administrativo as apis_administrativo

app_name = 'contratos'

urlpatterns = [
    # Views de renderização
    path('novo/', views.render_novo_contrato, name='novo_contrato'),
    path('editar/<int:contrato_id>/', views.render_editar_contrato, name='editar_contrato'),
    path('acompanhamento-crm/', views.render_acompanhamento_crm, name='acompanhamento_crm'),
    path('acompanhamento-tabela/', views.render_acompanhamento_tabela, name='acompanhamento_tabela'),
    path('gerenciar-bancos/', views.render_gerenciar_bancos, name='gerenciar_bancos'),
    path('administrativo/', views.render_administrativo, name='administrativo'),
    path('download-modelo-schema/', views.download_modelo_schema_csv, name='download_modelo_schema'),
    path('download-modelo-bancos/', views.download_modelo_bancos_csv, name='download_modelo_bancos'),
    path('download-modelo-convenios/', views.download_modelo_convenios_csv, name='download_modelo_convenios'),
    path('download-modelo-operacoes/', views.download_modelo_operacoes_csv, name='download_modelo_operacoes'),
    
    # APIs - Gerenciar (para consultores - novo contrato)
    path('api/bancos/ativos/', apis_gerenciar.api_get_bancos_ativos, name='api_bancos_ativos'),
    path('api/convenios/por-banco/', apis_gerenciar.api_get_convenios_por_banco, name='api_convenios_por_banco'),
    path('api/operacoes/por-convenio/', apis_gerenciar.api_get_operacoes_por_convenio, name='api_operacoes_por_convenio'),
    
    # APIs - Gerenciar (para admin - hierarquia completa)
    path('api/bancos/todos/', apis_gerenciar.api_get_bancos_todos, name='api_bancos_todos'),
    path('api/convenios/por-banco-admin/', apis_gerenciar.api_get_convenios_por_banco_admin, name='api_convenios_por_banco_admin'),
    path('api/operacoes/por-banco-convenio-admin/', apis_gerenciar.api_get_operacoes_por_banco_convenio_admin, name='api_operacoes_por_banco_convenio_admin'),
    path('api/schemas/por-operacao-admin/', apis_gerenciar.api_get_schemas_por_operacao_admin, name='api_schemas_por_operacao_admin'),
    path('api/ativar-banco-convenio-operacao/', apis_gerenciar.api_post_ativar_banco_convenio_operacao, name='api_ativar_banco_convenio_operacao'),
    path('api/desativar-banco-convenio-operacao/', apis_gerenciar.api_post_desativar_banco_convenio_operacao, name='api_desativar_banco_convenio_operacao'),
    
    # APIs - Gerenciar (legadas)
    path('api/convenios/com-schemas/', apis_gerenciar.api_get_convenios_com_schemas, name='api_convenios_com_schemas'),
    path('api/operacoes/com-schemas/por-convenio/', apis_gerenciar.api_get_operacoes_com_schemas_por_convenio, name='api_operacoes_com_schemas_por_convenio'),
    path('api/schemas/titulos/por-convenio-operacao/', apis_gerenciar.api_get_titulos_schemas_por_convenio_operacao, name='api_titulos_schemas_por_convenio_operacao'),
    
    # APIs - Schemas
    path('api/schemas/importados/', apis_schemas.api_get_schemas_importados, name='api_schemas_importados'),
    path('api/schemas/por-convenio-operacao/', apis_schemas.api_get_schemas_por_convenio_operacao, name='api_schemas_por_convenio_operacao'),
    path('api/schema/campos/', apis_schemas.api_get_schema_campos, name='api_schema_campos'),
    path('api/schema/criar-campo/', apis_schemas.api_post_criar_campo_schema, name='api_criar_campo_schema'),
    path('api/schema/upload-csv/', apis_schemas.api_post_upload_schema_csv, name='api_upload_schema_csv'),
    path('api/schema/reordenar-campos/', apis_schemas.api_post_reordenar_campos, name='api_reordenar_campos'),
    
    # APIs - Contratos
    path('api/contratos/kanban/', apis_contratos.api_get_kanban, name='api_kanban'),
    path('api/contratos/tabela/', apis_contratos.api_get_contratos_tabela, name='api_contratos_tabela'),
    path('api/contratos/<int:contrato_id>/', apis_contratos.api_get_contrato, name='api_contrato'),
    path('api/contratos/novo/', apis_contratos.api_post_novo_contrato, name='api_novo_contrato'),
    path('api/contratos/salvar-pagina/', apis_contratos.api_post_salvar_pagina, name='api_salvar_pagina'),
    path('api/contratos/mover/', apis_contratos.api_post_mover_contrato, name='api_mover_contrato'),
    
    # APIs - Administrativo
    path('api/admin/bancos/', apis_administrativo.api_get_bancos, name='api_admin_bancos'),
    path('api/admin/bancos/criar/', apis_administrativo.api_post_criar_banco, name='api_admin_criar_banco'),
    path('api/admin/bancos/<int:banco_id>/editar/', apis_administrativo.api_editar_banco, name='api_admin_editar_banco'),
    path('api/admin/bancos/<int:banco_id>/deletar/', apis_administrativo.api_deletar_banco, name='api_admin_deletar_banco'),
    path('api/admin/bancos/importar-csv/', apis_administrativo.api_post_importar_bancos_csv, name='api_admin_importar_bancos_csv'),
    path('api/admin/convenios/', apis_administrativo.api_get_convenios, name='api_admin_convenios'),
    path('api/admin/convenios/criar/', apis_administrativo.api_post_criar_convenio, name='api_admin_criar_convenio'),
    path('api/admin/convenios/<int:convenio_id>/editar/', apis_administrativo.api_editar_convenio, name='api_admin_editar_convenio'),
    path('api/admin/convenios/<int:convenio_id>/deletar/', apis_administrativo.api_deletar_convenio, name='api_admin_deletar_convenio'),
    path('api/admin/convenios/importar-csv/', apis_administrativo.api_post_importar_convenios_csv, name='api_admin_importar_convenios_csv'),
    path('api/admin/operacoes/', apis_administrativo.api_get_operacoes, name='api_admin_operacoes'),
    path('api/admin/operacoes/criar/', apis_administrativo.api_post_criar_operacao, name='api_admin_criar_operacao'),
    path('api/admin/operacoes/<int:operacao_id>/editar/', apis_administrativo.api_editar_operacao, name='api_admin_editar_operacao'),
    path('api/admin/operacoes/<int:operacao_id>/deletar/', apis_administrativo.api_deletar_operacao, name='api_admin_deletar_operacao'),
    path('api/admin/operacoes/importar-csv/', apis_administrativo.api_post_importar_operacoes_csv, name='api_admin_importar_operacoes_csv'),
    path('api/admin/bancos-convenios/', apis_administrativo.api_get_bancos_convenios, name='api_admin_bancos_convenios'),
    path('api/admin/bancos-convenios/associar/', apis_administrativo.api_post_associar_banco_convenio, name='api_admin_associar_banco_convenio'),
    path('api/admin/bancos-convenios/<int:banco_convenio_id>/desassociar/', apis_administrativo.api_post_desassociar_banco_convenio, name='api_admin_desassociar_banco_convenio'),
    path('api/admin/bancos-convenios/<int:banco_convenio_id>/ativar/', apis_administrativo.api_post_ativar_banco_convenio, name='api_admin_ativar_banco_convenio'),
    path('api/admin/convenios-operacoes/', apis_administrativo.api_get_convenios_operacoes, name='api_admin_convenios_operacoes'),
    path('api/admin/convenios-operacoes/associar/', apis_administrativo.api_post_associar_convenio_operacao, name='api_admin_associar_convenio_operacao'),
    path('api/admin/convenios-operacoes/<int:convenio_operacao_id>/desassociar/', apis_administrativo.api_post_desassociar_convenio_operacao, name='api_admin_desassociar_convenio_operacao'),
    path('api/admin/convenios-operacoes/<int:convenio_operacao_id>/ativar/', apis_administrativo.api_post_ativar_convenio_operacao, name='api_admin_ativar_convenio_operacao'),
    # APIs - Schemas (editar/deletar)
    path('api/schema/campo/<int:campo_id>/editar/', apis_schemas.api_editar_campo_schema, name='api_editar_campo_schema'),
    path('api/schema/campo/<int:campo_id>/deletar/', apis_schemas.api_deletar_campo_schema, name='api_deletar_campo_schema'),
    # APIs - Contratos (complementares)
    path('api/contratos/<int:contrato_id>/atualizar/', apis_contratos.api_post_atualizar_contrato, name='api_atualizar_contrato'),
    path('api/contratos/<int:contrato_id>/link-formalizacao/', apis_contratos.api_post_atualizar_link_formalizacao, name='api_atualizar_link_formalizacao'),
    path('api/contratos/<int:contrato_id>/cliente-formalizou/', apis_contratos.api_post_cliente_formalizou, name='api_cliente_formalizou'),
    path('api/contratos/mover-massa/', apis_contratos.api_post_mover_contratos_massa, name='api_mover_contratos_massa'),
    path('api/contratos/<int:contrato_id>/anexos/', apis_contratos.api_get_anexos_contrato, name='api_anexos_contrato'),
    path('api/contratos/<int:contrato_id>/anexos/upload/', apis_contratos.api_post_upload_anexo, name='api_upload_anexo'),
    path('api/anexos/<int:anexo_id>/deletar/', apis_contratos.api_post_deletar_anexo, name='api_deletar_anexo'),
    
    # APIs - SSE e Tabulações
    path('api/contratos/sse/', apis_contratos.api_sse_contratos, name='api_sse_contratos'),
    path('api/tabulacoes/', apis_contratos.api_get_tabulacoes, name='api_tabulacoes'),
    
    # APIs - Ações específicas de tabulação
    path('api/contratos/<int:contrato_id>/marcar-incompleto/', apis_contratos.api_post_marcar_incompleto, name='api_marcar_incompleto'),
    path('api/contratos/<int:contrato_id>/informar-link/', apis_contratos.api_post_informar_link_formalizacao, name='api_informar_link'),
    path('api/contratos/<int:contrato_id>/confirmar-assinatura/', apis_contratos.api_post_confirmar_assinatura, name='api_confirmar_assinatura'),
    path('api/contratos/<int:contrato_id>/upload-video/', apis_contratos.api_post_upload_video_cliente, name='api_upload_video'),
    path('api/contratos/<int:contrato_id>/solicitar-video/', apis_contratos.api_post_solicitar_video, name='api_solicitar_video'),
    
    # API - Exclusão (apenas superuser)
    path('api/contratos/<int:contrato_id>/excluir/', apis_contratos.api_delete_contrato, name='api_excluir_contrato'),
]

