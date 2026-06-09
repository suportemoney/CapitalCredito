from django.urls import path
from . import views
from .apis import editar_usuario as apis_editar_usuario
from .apis import gerenciar as apis_gerenciar

app_name = 'permissoes'

urlpatterns = [
    # Renders
    path('', views.render_index, name='index'),
    path('gerenciar/', views.render_gerenciar, name='gerenciar'),
    path('usuario/<int:user_id>/editar/', views.render_editar_usuario, name='editar_usuario'),
    
    # APIs - editar_usuario.html
    path('api/usuario/<int:user_id>/adicionar/', apis_editar_usuario.api_adicionar_acessos, name='api_adicionar_acessos'),
    path('api/usuario/<int:user_id>/remover/', apis_editar_usuario.api_remover_acessos, name='api_remover_acessos'),
    path('api/usuario/<int:user_id>/aplicar-grupo/', apis_editar_usuario.api_aplicar_grupo, name='api_aplicar_grupo'),
    path('api/usuario/<int:user_id>/salvar/', apis_editar_usuario.api_salvar_permissoes, name='api_salvar_permissoes'),
    
    # APIs - gerenciar.html (Tab 1: Acessos)
    path('api/gerenciar/acessos/listar/', apis_gerenciar.api_listar_acessos, name='api_listar_acessos'),
    path('api/gerenciar/acessos/criar/', apis_gerenciar.api_criar_acesso, name='api_criar_acesso'),
    path('api/gerenciar/acessos/editar/<int:acesso_id>/', apis_gerenciar.api_editar_acesso, name='api_editar_acesso'),
    path('api/gerenciar/acessos/deletar/<int:acesso_id>/', apis_gerenciar.api_deletar_acesso, name='api_deletar_acesso'),
    
    # APIs - gerenciar.html (Tab 2: Grupos)
    path('api/gerenciar/grupos/listar/', apis_gerenciar.api_listar_grupos, name='api_listar_grupos'),
    path('api/gerenciar/grupos/criar/', apis_gerenciar.api_criar_grupo, name='api_criar_grupo'),
    path('api/gerenciar/grupos/editar/<int:grupo_id>/', apis_gerenciar.api_editar_grupo, name='api_editar_grupo'),
    path('api/gerenciar/grupos/deletar/<int:grupo_id>/', apis_gerenciar.api_deletar_grupo, name='api_deletar_grupo'),
    
    # APIs - gerenciar.html (Tab 3: Usuários)
    path('api/gerenciar/usuarios/listar/', apis_gerenciar.api_listar_controles, name='api_listar_controles'),
    path('api/gerenciar/usuarios/get-controle/<int:user_id>/', apis_gerenciar.api_get_controle_usuario, name='api_get_controle_usuario'),
    path('api/gerenciar/usuarios/salvar/<int:user_id>/', apis_gerenciar.api_salvar_permissoes_usuario, name='api_salvar_permissoes_usuario'),
    path('api/gerenciar/usuarios/deletar/<int:controle_id>/', apis_gerenciar.api_deletar_controle, name='api_deletar_controle'),

    # APIs - gerenciar.html (Tab 4: Em Lote)
    path('api/gerenciar/lote/aplicar/', apis_gerenciar.api_aplicar_lote, name='api_aplicar_lote'),
]
