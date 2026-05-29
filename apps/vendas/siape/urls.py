from django.urls import path
from . import views
from .apis import campanhas as apis_campanhas
from .apis import consulta as apis_consulta
from .apis import crm as apis_crm
from .apis import produtos as apis_produtos
from .apis import metas as apis_metas
from .apis import ranking as apis_ranking
from .apis import responsaveis as apis_responsaveis
from .apis import consulta_operacional as apis_consulta_operacional

app_name = 'siape'

urlpatterns = [
    # Rotas específicas primeiro (antes da rota raiz)
    path('consulta/', views.render_consulta, name='consulta'),
    path('campanhas/', views.render_campanhas, name='campanhas'),
    path('crm/', views.render_crm, name='crm'),
    path('produtos/', views.render_produtos, name='produtos'),
    path('metas/', views.render_metas, name='metas'),
    path('responsaveis/', views.render_responsaveis, name='responsaveis'),
    
    # APIs
    # APIs Campanhas
    path('api/campanhas/listar/', apis_campanhas.api_listar_campanhas, name='api_listar_campanhas'),
    path('api/campanhas/criar/', apis_campanhas.api_criar_campanha, name='api_criar_campanha'),
    path('api/campanhas/editar/<int:campanha_id>/', apis_campanhas.api_editar_campanha, name='api_editar_campanha'),
    path('api/campanhas/deletar/<int:campanha_id>/', apis_campanhas.api_deletar_campanha, name='api_deletar_campanha'),
    path('api/campanhas/importar-csv/', apis_campanhas.api_importar_csv, name='api_importar_csv'),
    path('api/campanhas/download-modelo/', apis_campanhas.api_download_modelo, name='api_download_modelo'),
    
    # APIs Consulta
    path('api/consulta/buscar/', apis_consulta.api_buscar_clientes, name='api_buscar_clientes'),
    path('api/consulta/detalhes/<int:cliente_id>/', apis_consulta.api_detalhes_cliente, name='api_detalhes_cliente'),
    path('api/consulta/campanhas-ativas/', apis_consulta.api_listar_campanhas_ativas, name='api_campanhas_ativas'),
    path('api/consulta/adicionar-contato/<int:cliente_id>/', apis_consulta.api_adicionar_contato, name='api_adicionar_contato'),
    path('api/consulta/carteira-por-cpf/', apis_consulta_operacional.api_carteira_por_cpf, name='api_carteira_por_cpf'),
    path('api/consulta/simulacoes/', apis_consulta_operacional.api_get_simulacoes, name='api_get_simulacoes'),
    path('api/consulta/operacional/', apis_consulta_operacional.api_get_operacional, name='api_get_operacional'),
    path('api/consulta/container-novo-contrato/', apis_consulta_operacional.api_get_container_novo_contrato, name='api_container_novo_contrato'),
    
    # APIs CRM
    path('api/crm/adicionar-esteira/', apis_crm.api_adicionar_esteira, name='api_adicionar_esteira'),
    path('api/crm/kanban/', apis_crm.api_listar_kanban, name='api_listar_kanban'),
    path('api/crm/criar-tabulacao/', apis_crm.api_criar_tabulacao, name='api_criar_tabulacao'),
    path('api/crm/mover-card/', apis_crm.api_mover_card, name='api_mover_card'),
    path('api/crm/ficha-cliente/<str:cpf>/', apis_crm.api_ficha_cliente, name='api_ficha_cliente'),
    path('api/crm/listar-funcionarios/', apis_crm.api_listar_funcionarios, name='api_listar_funcionarios'),
    path('api/crm/listar-representantes/<str:tipo>/', apis_crm.api_listar_representantes, name='api_listar_representantes'),
    path('api/crm/listar-dias-disponiveis/', apis_crm.api_listar_dias_disponiveis, name='api_listar_dias_disponiveis'),
    path('api/crm/listar-horarios-disponiveis/', apis_crm.api_listar_horarios_disponiveis, name='api_listar_horarios_disponiveis'),
    
    # APIs Produtos
    path('api/produtos/listar/', apis_produtos.api_listar_produtos, name='api_listar_produtos'),
    path('api/produtos/criar/', apis_produtos.api_criar_produto, name='api_criar_produto'),
    path('api/produtos/editar/<int:produto_id>/', apis_produtos.api_editar_produto, name='api_editar_produto'),
    path('api/produtos/deletar/<int:produto_id>/', apis_produtos.api_deletar_produto, name='api_deletar_produto'),
    
    # APIs Metas
    path('api/metas/listar/', apis_metas.api_listar_metas, name='api_listar_metas'),
    path('api/metas/criar/', apis_metas.api_criar_meta, name='api_criar_meta'),
    path('api/metas/editar/<int:meta_id>/', apis_metas.api_editar_meta, name='api_editar_meta'),
    path('api/metas/deletar/<int:meta_id>/', apis_metas.api_deletar_meta, name='api_deletar_meta'),
    
    # APIs Ranking
    path('api/ranking/', apis_ranking.api_ranking, name='api_ranking'),
    path('api/ranking/metas-ativas/', apis_ranking.api_listar_metas_ativas, name='api_metas_ativas'),
    
    # APIs Responsáveis
    path('api/responsaveis/listar/', apis_responsaveis.api_listar_responsaveis, name='api_listar_responsaveis'),
    path('api/responsaveis/listar-usuarios/', apis_responsaveis.api_listar_usuarios_disponiveis, name='api_listar_usuarios_disponiveis'),
    path('api/responsaveis/criar/', apis_responsaveis.api_criar_responsavel, name='api_criar_responsavel'),
    path('api/responsaveis/editar/<int:responsavel_id>/', apis_responsaveis.api_editar_responsavel, name='api_editar_responsavel'),
    path('api/responsaveis/deletar/<int:responsavel_id>/', apis_responsaveis.api_deletar_responsavel, name='api_deletar_responsavel'),
    
    # Rota raiz por último (captura tudo que não foi capturado acima)
    path('', views.render_ranking, name='ranking'),
]

