from django.urls import path
from . import views
from .apis import novo as apis_novo
from .apis import gerenciar as apis_gerenciar

app_name = 'funcionarios'

urlpatterns = [
    path('', views.render_index, name='index'),
    path('novo/', views.render_novo, name='novo'),
    path('gerenciar/', views.render_gerenciar, name='gerenciar'),
    
    # APIs
    path('api/novo/criar/', apis_novo.api_criar_funcionario, name='api_criar_funcionario'),
    path('api/gerenciar/listar/', apis_gerenciar.api_listar_funcionarios, name='api_listar_funcionarios'),
    path('api/gerenciar/buscar/<int:funcionario_id>/', apis_gerenciar.api_buscar_funcionario, name='api_buscar_funcionario'),
    path('api/gerenciar/editar/<int:funcionario_id>/', apis_gerenciar.api_editar_funcionario, name='api_editar_funcionario'),
    path('api/gerenciar/documentos/<int:funcionario_id>/', apis_gerenciar.api_get_documentos_funcionario, name='api_get_documentos_funcionario'),
    path('api/gerenciar/documentos/adicionar/', apis_gerenciar.api_post_adicionar_documento, name='api_post_adicionar_documento'),
    path('api/gerenciar/documentos/deletar/<int:documento_id>/', apis_gerenciar.api_post_deletar_documento, name='api_post_deletar_documento'),
]

