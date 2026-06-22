from django.urls import path

from .views import render_esteira, render_gerenciador

from .apis.get_cliente import api_get_cliente_ficha
from .apis.get_esteira import (
    api_get_esteira_agendamentos,
    api_get_esteira_campanhas,
    api_get_esteira_controle,
    api_get_esteira_historico,
    api_get_esteira_kpis,
    api_get_esteira_pendente,
    api_get_esteira_proximo_cliente,
    api_get_esteira_status_choices,
)
from .apis.post_esteira import api_post_esteira_agendamento, api_post_esteira_tabulacao
from .apis.get_gerenciador import (
    api_get_gerenciador_campanhas,
    api_get_gerenciador_clientes,
    api_get_gerenciador_equipes,
    api_get_gerenciador_status,
    api_get_gerenciador_usuarios,
)
from .apis.get_gerenciador_overview import (
    api_get_gerenciador_agendamentos_campanha,
    api_get_gerenciador_campanha_detalhe,
    api_get_gerenciador_campanhas_enriquecidas,
    api_get_gerenciador_clientes_detalhe,
    api_get_gerenciador_kpis,
    api_get_gerenciador_ultima_importacao,
)
from .apis.get_gerenciador_equipe_filtros import api_get_gerenciador_equipe_filtros
from .apis.get_gerenciador_filtros import api_get_gerenciador_siape_filtros
from .apis.post_gerenciador import (
    api_post_gerenciador_campanha,
    api_post_gerenciador_campanha_atualizar,
    api_post_gerenciador_campanha_status,
    api_post_gerenciador_clientes,
    api_post_gerenciador_equipe,
    api_post_gerenciador_equipe_atualizar,
)
from .apis.post_gerenciador_campanhas import (
    api_post_gerenciador_siape_criar,
    api_post_gerenciador_siape_preview,
)
from .apis.post_importacao import (
    api_post_importacao_csv_confirmar,
    api_post_importacao_csv_preview,
)
from .apis.sse_gerenciador_preview import api_sse_gerenciador_siape_preview
from .apis.sse_gerenciador_criar import api_sse_gerenciador_siape_criar

app_name = 'plus'

urlpatterns = [
    path('esteira/', render_esteira, name='render_esteira'),
    path('gerenciador/', render_gerenciador, name='render_gerenciador'),

    path('api/get/cliente-ficha/', api_get_cliente_ficha, name='api_get_cliente_ficha_v2'),

    path('api/get/esteira/campanhas/', api_get_esteira_campanhas, name='api_get_esteira_campanhas_v2'),
    path('api/get/esteira/proximo-cliente/', api_get_esteira_proximo_cliente, name='api_get_esteira_proximo_cliente_v2'),
    path('api/get/esteira/pendente/', api_get_esteira_pendente, name='api_get_esteira_pendente_v2'),
    path('api/get/esteira/historico/', api_get_esteira_historico, name='api_get_esteira_historico_v2'),
    path('api/get/esteira/controle/', api_get_esteira_controle, name='api_get_esteira_controle_v2'),
    path('api/get/esteira/kpis/', api_get_esteira_kpis, name='api_get_esteira_kpis_v2'),
    path('api/get/esteira/agendamentos/', api_get_esteira_agendamentos, name='api_get_esteira_agendamentos_v2'),
    path('api/get/esteira/status-choices/', api_get_esteira_status_choices, name='api_get_esteira_status_v2'),

    path('api/post/tabulacao/', api_post_esteira_tabulacao, name='api_post_tabulacao_v2'),
    path('api/post/agendamento/', api_post_esteira_agendamento, name='api_post_agendamento_v2'),

    path('api/get/gerenciador/equipes/', api_get_gerenciador_equipes, name='api_get_gerenciador_equipes_v2'),
    path('api/get/gerenciador/equipe-filtros/', api_get_gerenciador_equipe_filtros, name='api_get_gerenciador_equipe_filtros_v2'),
    path('api/get/gerenciador/campanhas/', api_get_gerenciador_campanhas, name='api_get_gerenciador_campanhas_v2'),
    path('api/get/gerenciador/status/', api_get_gerenciador_status, name='api_get_gerenciador_status_v2'),
    path('api/get/gerenciador/clientes/', api_get_gerenciador_clientes, name='api_get_gerenciador_clientes_v2'),
    path('api/get/gerenciador/usuarios/', api_get_gerenciador_usuarios, name='api_get_gerenciador_usuarios_v2'),
    path('api/get/gerenciador/siape/filtros/', api_get_gerenciador_siape_filtros, name='api_get_gerenciador_siape_filtros_v2'),
    path('api/get/gerenciador/kpis/', api_get_gerenciador_kpis, name='api_get_gerenciador_kpis_v2'),
    path('api/get/gerenciador/campanhas-lista/', api_get_gerenciador_campanhas_enriquecidas, name='api_get_gerenciador_campanhas_lista_v2'),
    path('api/get/gerenciador/campanha-detalhe/', api_get_gerenciador_campanha_detalhe, name='api_get_gerenciador_campanha_detalhe_v2'),
    path('api/get/gerenciador/clientes-detalhe/', api_get_gerenciador_clientes_detalhe, name='api_get_gerenciador_clientes_detalhe_v2'),
    path('api/get/gerenciador/ultima-importacao/', api_get_gerenciador_ultima_importacao, name='api_get_gerenciador_ultima_importacao_v2'),
    path('api/get/gerenciador/agendamentos-campanha/', api_get_gerenciador_agendamentos_campanha, name='api_get_gerenciador_agendamentos_campanha_v2'),

    path('api/post/gerenciador/campanha/', api_post_gerenciador_campanha, name='api_post_gerenciador_campanha_v2'),
    path('api/post/gerenciador/equipe/', api_post_gerenciador_equipe, name='api_post_gerenciador_equipe_v2'),
    path('api/post/gerenciador/equipe-atualizar/', api_post_gerenciador_equipe_atualizar, name='api_post_gerenciador_equipe_atualizar_v2'),
    path('api/post/gerenciador/campanha-status/', api_post_gerenciador_campanha_status, name='api_post_gerenciador_campanha_status_v2'),
    path('api/post/gerenciador/campanha-atualizar/', api_post_gerenciador_campanha_atualizar, name='api_post_gerenciador_campanha_atualizar_v2'),
    path('api/post/gerenciador/clientes/', api_post_gerenciador_clientes, name='api_post_gerenciador_clientes_v2'),

    path('api/post/gerenciador/siape/preview/', api_post_gerenciador_siape_preview, name='api_post_gerenciador_siape_preview_v2'),
    path('api/sse/gerenciador/siape/preview/', api_sse_gerenciador_siape_preview, name='api_sse_gerenciador_siape_preview_v2'),
    path('api/sse/gerenciador/siape/criar/', api_sse_gerenciador_siape_criar, name='api_sse_gerenciador_siape_criar_v2'),
    path('api/post/gerenciador/siape/criar/', api_post_gerenciador_siape_criar, name='api_post_gerenciador_siape_criar_v2'),

    path('api/post/importacao-csv/preview/', api_post_importacao_csv_preview, name='api_post_importacao_preview_v2'),
    path('api/post/importacao-csv/confirmar/', api_post_importacao_csv_confirmar, name='api_post_importacao_confirmar_v2'),
]
