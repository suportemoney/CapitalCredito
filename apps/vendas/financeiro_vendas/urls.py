from django.urls import path
from . import views
from .apis import gerenciar as apis_gerenciar
from .apis import classificador as apis_classificador
from .apis import comprovante as apis_comprovante
from .apis import pagamento_tc as apis_pagamento_tc

app_name = 'financeiro_vendas'

urlpatterns = [
    path('', views.render_index, name='index'),
    path('classificador/', views.render_classificador, name='classificador'),
    path('pagamento-tc/', views.render_pagamento_tc, name='pagamento_tc'),
    
    # APIs Contratos
    path('api/contratos/resumo/', apis_gerenciar.api_resumo_contratos, name='api_resumo_contratos'),
    path('api/contratos/listar/', apis_gerenciar.api_listar_contratos, name='api_listar_contratos'),
    path('api/contratos/criar/', apis_gerenciar.api_criar_contrato, name='api_criar_contrato'),
    path('api/contratos/editar-campo/<int:contrato_id>/', apis_gerenciar.api_editar_campo, name='api_editar_campo'),
    path('api/contratos/inativar/<int:contrato_id>/', apis_gerenciar.api_inativar_contrato, name='api_inativar_contrato'),
    path('api/cliente/buscar-cpf/', apis_gerenciar.api_buscar_cliente_por_cpf, name='api_buscar_cliente_cpf'),
    path('api/funcionario/get-setor/<int:user_id>/', apis_gerenciar.api_get_setor_funcionario, name='api_get_setor_funcionario'),

    # APIs Comprovante TC
    path('api/comprovante-tc/', apis_comprovante.api_upload_comprovante_tc, name='api_upload_comprovante_tc'),
    path('api/comprovantes-tc/', apis_comprovante.api_listar_comprovantes_tc, name='api_listar_comprovantes_tc'),
    path('api/comprovante-tc/excluir/', apis_comprovante.api_excluir_comprovante_tc, name='api_excluir_comprovante_tc'),
    
    # APIs Classificador
    path('api/classificador/listar/', apis_classificador.api_listar_classificadores, name='api_listar_classificadores'),
    path('api/classificador/criar/', apis_classificador.api_criar_classificador, name='api_criar_classificador'),
    path('api/classificador/editar/<int:classificador_id>/', apis_classificador.api_editar_classificador, name='api_editar_classificador'),
    path('api/classificador/deletar/<int:classificador_id>/', apis_classificador.api_deletar_classificador, name='api_deletar_classificador'),

    # APIs Pagamento TC (contratos v2)
    path('api/pagamento-tc/listar/', apis_pagamento_tc.api_listar_pagamento_tc, name='api_listar_pagamento_tc'),
    path('api/pagamento-tc/modal-defaults/', apis_pagamento_tc.api_modal_defaults_pagamento_tc, name='api_modal_defaults_pagamento_tc'),
    path('api/pagamento-tc/salvar-dados/', apis_pagamento_tc.api_salvar_dados_pagamento_tc, name='api_salvar_dados_pagamento_tc'),
    path('api/pagamento-tc/comprovantes/', apis_pagamento_tc.api_comprovantes_pagamento_tc, name='api_comprovantes_pagamento_tc'),
    path('api/pagamento-tc/comprovante/', apis_pagamento_tc.api_upload_comprovante_pagamento_tc, name='api_upload_comprovante_pagamento_tc'),
    path('api/pagamento-tc/comprovante/excluir/', apis_pagamento_tc.api_excluir_comprovante_pagamento_tc, name='api_excluir_comprovante_pagamento_tc'),
    path('api/pagamento-tc/confirmar/', apis_pagamento_tc.api_confirmar_pagamento_tc, name='api_confirmar_pagamento_tc'),
]

