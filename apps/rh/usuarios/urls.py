from django.urls import path
from . import views
from .apis import gerenciar as apis_gerenciar

app_name = 'usuarios'

urlpatterns = [
    path('', views.render_index, name='index'),
    path('login/', views.render_login, name='render_login'),
    path('logout/', views.render_logout, name='render_logout'),
    path('gerenciar/', views.render_gerenciar, name='gerenciar'),
    
    # APIs
    path('api/gerenciar/listar/', apis_gerenciar.api_listar_usuarios, name='api_listar_usuarios'),
    path('api/gerenciar/atualizar-status/<int:user_id>/', apis_gerenciar.api_atualizar_status, name='api_atualizar_status'),
]

