from django.urls import path
from . import views
from .apis import gerenciar as apis_gerenciar

app_name = 'rh_admin'

urlpatterns = [
    # Index
    path('', views.render_index, name='index'),
    path('gerenciar/', views.render_gerenciar, name='gerenciar'),
    
    # APIs - Empresas
    path('api/empresas/criar/', apis_gerenciar.api_criar_empresa, name='api_empresas_criar'),
    path('api/empresas/editar/<int:empresa_id>/', apis_gerenciar.api_editar_empresa, name='api_empresas_editar'),
    path('api/empresas/deletar/<int:empresa_id>/', apis_gerenciar.api_deletar_empresa, name='api_empresas_deletar'),
    
    # APIs - Lojas
    path('api/lojas/criar/', apis_gerenciar.api_criar_loja, name='api_lojas_criar'),
    path('api/lojas/editar/<int:loja_id>/', apis_gerenciar.api_editar_loja, name='api_lojas_editar'),
    path('api/lojas/deletar/<int:loja_id>/', apis_gerenciar.api_deletar_loja, name='api_lojas_deletar'),
    
    # APIs - Departamentos
    path('api/departamentos/criar/', apis_gerenciar.api_criar_departamento, name='api_departamentos_criar'),
    path('api/departamentos/editar/<int:departamento_id>/', apis_gerenciar.api_editar_departamento, name='api_departamentos_editar'),
    path('api/departamentos/deletar/<int:departamento_id>/', apis_gerenciar.api_deletar_departamento, name='api_departamentos_deletar'),
    
    # APIs - Setores
    path('api/setores/criar/', apis_gerenciar.api_criar_setor, name='api_setores_criar'),
    path('api/setores/editar/<int:setor_id>/', apis_gerenciar.api_editar_setor, name='api_setores_editar'),
    path('api/setores/deletar/<int:setor_id>/', apis_gerenciar.api_deletar_setor, name='api_setores_deletar'),
    
    # APIs - Cargos
    path('api/cargos/criar/', apis_gerenciar.api_criar_cargo, name='api_cargos_criar'),
    path('api/cargos/editar/<int:cargo_id>/', apis_gerenciar.api_editar_cargo, name='api_cargos_editar'),
    path('api/cargos/deletar/<int:cargo_id>/', apis_gerenciar.api_deletar_cargo, name='api_cargos_deletar'),
    
    # APIs - Equipes
    path('api/equipes/criar/', apis_gerenciar.api_criar_equipe, name='api_equipes_criar'),
    path('api/equipes/editar/<int:equipe_id>/', apis_gerenciar.api_editar_equipe, name='api_equipes_editar'),
    path('api/equipes/deletar/<int:equipe_id>/', apis_gerenciar.api_deletar_equipe, name='api_equipes_deletar'),
    
    # APIs - Níveis Hierárquicos
    path('api/niveis/criar/', apis_gerenciar.api_criar_nivel, name='api_niveis_criar'),
    path('api/niveis/editar/<int:nivel_id>/', apis_gerenciar.api_editar_nivel, name='api_niveis_editar'),
    path('api/niveis/deletar/<int:nivel_id>/', apis_gerenciar.api_deletar_nivel, name='api_niveis_deletar'),
    path('api/niveis/listar/', apis_gerenciar.api_listar_niveis, name='api_niveis_listar'),
    
    # APIs GET para atualizar tabelas
    path('api/get/empresas/', apis_gerenciar.api_get_empresas, name='api_get_empresas'),
    path('api/get/lojas/', apis_gerenciar.api_get_lojas, name='api_get_lojas'),
    path('api/get/departamentos/', apis_gerenciar.api_get_departamentos, name='api_get_departamentos'),
    path('api/get/setores/', apis_gerenciar.api_get_setores, name='api_get_setores'),
    path('api/get/cargos/', apis_gerenciar.api_get_cargos, name='api_get_cargos'),
    path('api/get/equipes/', apis_gerenciar.api_get_equipes, name='api_get_equipes'),
    path('api/get/niveis/', apis_gerenciar.api_get_niveis, name='api_get_niveis'),
]
