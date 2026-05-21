from django.urls import path
from . import views
from .apis import gerenciar as apis_gerenciar

app_name = 'comunicados'

urlpatterns = [
    # Renders
    path('', views.render_mural, name='mural'),
    path('gerenciar/', views.render_listar, name='listar'),
    path('gerenciar/criar/', views.render_criar, name='criar'),
    path('gerenciar/editar/<int:comunicado_id>/', views.render_editar, name='editar'),
    
    # APIs - gerenciar (listar, criar, editar)
    path('api/criar/', apis_gerenciar.api_criar, name='api_criar'),
    path('api/editar/<int:comunicado_id>/', apis_gerenciar.api_editar, name='api_editar'),
    path('api/deletar/<int:comunicado_id>/', apis_gerenciar.api_deletar, name='api_deletar'),
    path('api/toggle-status/<int:comunicado_id>/', apis_gerenciar.api_toggle_status, name='api_toggle_status'),
    path('api/deletar-arquivo/<int:arquivo_id>/', apis_gerenciar.api_deletar_arquivo, name='api_deletar_arquivo'),
]
