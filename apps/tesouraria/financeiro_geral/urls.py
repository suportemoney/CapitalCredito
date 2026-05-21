from django.urls import path
from . import views
from .apis import dashboard as apis_dashboard
from .apis import contas_pagar as apis_contas_pagar
from .apis import contas_receber as apis_contas_receber
from .apis import gerenciador as apis_gerenciador
from .apis import notificacoes as apis_notificacoes
from .apis import sse as apis_sse
from .apis import bonificacoes_pagar as apis_bonificacoes_pagar

app_name = 'financeiro_geral'

urlpatterns = [
    path('', views.render_index, name='index'),
    path('dashboard/', views.render_dashboard, name='dashboard'),
    path('contas-a-pagar/', views.render_contas_a_pagar, name='contas_a_pagar'),
    path('gerenciar/', views.render_gerenciar, name='gerenciar'),
    path('api/dashboard/', apis_dashboard.api_get_dashboard, name='api_get_dashboard'),
    path('api/contas-pagar/listar/', apis_contas_pagar.api_get_contas_pagar, name='api_get_contas_pagar'),
    path('api/contas-pagar/criar/', apis_contas_pagar.api_post_contas_pagar_criar, name='api_post_contas_pagar_criar'),
    path('api/contas-pagar/marcar-pago/', apis_contas_pagar.api_post_contas_pagar_marcar_pago, name='api_post_contas_pagar_marcar_pago'),
    path('api/contas-pagar/editar/', apis_contas_pagar.api_post_contas_pagar_editar, name='api_post_contas_pagar_editar'),
    path('api/bonificacoes-pagar/listar/', apis_bonificacoes_pagar.api_get_bonificacoes_pagar, name='api_get_bonificacoes_pagar'),
    path('api/bonificacoes-pagar/criar/', apis_bonificacoes_pagar.api_post_bonificacoes_pagar_criar, name='api_post_bonificacoes_pagar_criar'),
    path('api/bonificacoes-pagar/criar-ja-paga/', apis_bonificacoes_pagar.api_post_bonificacoes_pagar_criar_ja_paga, name='api_post_bonificacoes_pagar_criar_ja_paga'),
    path('api/bonificacoes-pagar/pagar-agora/', apis_bonificacoes_pagar.api_post_bonificacoes_pagar_pagar_agora, name='api_post_bonificacoes_pagar_pagar_agora'),
    path('api/bonificacoes-pagar/editar/', apis_bonificacoes_pagar.api_post_bonificacoes_pagar_editar, name='api_post_bonificacoes_pagar_editar'),
    path('api/bonificacoes-pagar/inativar/', apis_bonificacoes_pagar.api_post_bonificacoes_pagar_inativar, name='api_post_bonificacoes_pagar_inativar'),
    path('api/bonificacoes-pagar/comprovante-download/', apis_bonificacoes_pagar.api_get_bonificacao_comprovante_download, name='api_get_bonificacao_comprovante_download'),
    path('api/contas-receber/listar/', apis_contas_receber.api_get_contas_receber, name='api_get_contas_receber'),
    path('api/contas-receber/criar/', apis_contas_receber.api_post_contas_receber_criar, name='api_post_contas_receber_criar'),
    path('api/contas-receber/marcar-recebido/', apis_contas_receber.api_post_contas_receber_marcar_recebido, name='api_post_contas_receber_marcar_recebido'),
    path('api/gerenciador/categorias/', apis_gerenciador.api_get_categorias, name='api_get_categorias'),
    path('api/gerenciador/categorias/criar/', apis_gerenciador.api_post_categoria_criar, name='api_post_categoria_criar'),
    path('api/gerenciador/categorias/editar/', apis_gerenciador.api_post_categoria_editar, name='api_post_categoria_editar'),
    path('api/gerenciador/categorias/deletar/', apis_gerenciador.api_post_categoria_deletar, name='api_post_categoria_deletar'),
    path('api/gerenciador/subcategorias/', apis_gerenciador.api_get_subcategorias, name='api_get_subcategorias'),
    path('api/gerenciador/subcategorias/criar/', apis_gerenciador.api_post_subcategoria_criar, name='api_post_subcategoria_criar'),
    path('api/gerenciador/subcategorias/editar/', apis_gerenciador.api_post_subcategoria_editar, name='api_post_subcategoria_editar'),
    path('api/gerenciador/subcategorias/deletar/', apis_gerenciador.api_post_subcategoria_deletar, name='api_post_subcategoria_deletar'),
    path('api/gerenciador/tipos-beneficio/', apis_gerenciador.api_get_tipos_beneficio, name='api_get_tipos_beneficio'),
    path('api/gerenciador/tipos-beneficio/criar/', apis_gerenciador.api_post_tipo_beneficio_criar, name='api_post_tipo_beneficio_criar'),
    path('api/gerenciador/tipos-beneficio/editar/', apis_gerenciador.api_post_tipo_beneficio_editar, name='api_post_tipo_beneficio_editar'),
    path('api/gerenciador/tipos-beneficio/deletar/', apis_gerenciador.api_post_tipo_beneficio_deletar, name='api_post_tipo_beneficio_deletar'),
    path('api/notificacoes/contas/', apis_notificacoes.api_get_notificacoes_contas, name='api_get_notificacoes_contas'),
    path('api/notificacoes/count/', apis_notificacoes.api_get_notificacoes_count, name='api_get_notificacoes_count'),
    path('api/notificacoes/bonificacoes-usuario/', apis_notificacoes.api_get_bonificacoes_usuario, name='api_get_bonificacoes_usuario'),
    path('sse/notificacoes/contas/', apis_sse.sse_notificacoes_contas, name='sse_notificacoes_contas'),
]
