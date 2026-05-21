from django.urls import path
from . import views
from .apis import gerenciar as apis_gerenciar
from .apis import classificador as apis_classificador

app_name = 'financeiro_vendas'

urlpatterns = [
    path('', views.render_index, name='index'),
    path('classificador/', views.render_classificador, name='classificador'),
    
    # APIs Contratos
    path('api/contratos/resumo/', apis_gerenciar.api_resumo_contratos, name='api_resumo_contratos'),
    path('api/contratos/listar/', apis_gerenciar.api_listar_contratos, name='api_listar_contratos'),
    path('api/contratos/criar/', apis_gerenciar.api_criar_contrato, name='api_criar_contrato'),
    path('api/contratos/editar-campo/<int:contrato_id>/', apis_gerenciar.api_editar_campo, name='api_editar_campo'),
    path('api/contratos/inativar/<int:contrato_id>/', apis_gerenciar.api_inativar_contrato, name='api_inativar_contrato'),
    path('api/cliente/buscar-cpf/', apis_gerenciar.api_buscar_cliente_por_cpf, name='api_buscar_cliente_cpf'),
    path('api/funcionario/get-setor/<int:user_id>/', apis_gerenciar.api_get_setor_funcionario, name='api_get_setor_funcionario'),
    
    # APIs Classificador
    path('api/classificador/listar/', apis_classificador.api_listar_classificadores, name='api_listar_classificadores'),
    path('api/classificador/criar/', apis_classificador.api_criar_classificador, name='api_criar_classificador'),
    path('api/classificador/editar/<int:classificador_id>/', apis_classificador.api_editar_classificador, name='api_editar_classificador'),
    path('api/classificador/deletar/<int:classificador_id>/', apis_classificador.api_deletar_classificador, name='api_deletar_classificador'),
]

