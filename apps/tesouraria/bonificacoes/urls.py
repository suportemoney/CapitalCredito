from django.urls import path
from . import views
from .apis import regras as apis_regras
from .apis import vinculos as apis_vinculos
from .apis import reducoes as apis_reducoes
from .apis import calculo as apis_calculo

app_name = 'bonificacoes'

urlpatterns = [
    path('', views.render_bonificacoes, name='index'),
    path('calc/', views.render_calc_bonificacoes, name='calc'),
    path('api/regras/', apis_regras.api_get_regras, name='api_get_regras'),
    path('api/regras/nova/', apis_regras.api_post_nova_regra, name='api_post_nova_regra'),
    path('api/regras/editar/', apis_regras.api_post_editar_regra, name='api_post_editar_regra'),
    path('api/regras/deletar/', apis_regras.api_post_deletar_regra, name='api_post_deletar_regra'),
    path('api/gatilhos/', apis_regras.api_get_gatilhos, name='api_get_gatilhos'),
    path('api/gatilhos/salvar/', apis_regras.api_post_gatilho, name='api_post_gatilho'),
    path('api/gatilhos/deletar/', apis_regras.api_post_deletar_gatilho, name='api_post_deletar_gatilho'),
    path('api/vinculos/', apis_vinculos.api_get_vinculos, name='api_get_vinculos'),
    path('api/vinculos/setores-empresas/', apis_vinculos.api_get_setores_empresas, name='api_get_setores_empresas'),
    path('api/vinculos/funcionarios/', apis_vinculos.api_get_funcionarios_simples, name='api_get_funcionarios_simples'),
    path('api/vinculos/regras/', apis_vinculos.api_get_regras_simples, name='api_get_regras_simples'),
    path('api/vinculos/salvar/', apis_vinculos.api_post_vinculo, name='api_post_vinculo'),
    path('api/vinculos/lote/', apis_vinculos.api_post_vinculos_lote, name='api_post_vinculos_lote'),
    path('api/vinculos/deletar/', apis_vinculos.api_post_deletar_vinculo, name='api_post_deletar_vinculo'),
    path('api/reducao-regras/', apis_reducoes.api_get_reducao_regras, name='api_get_reducao_regras'),
    path('api/reducao-regras/salvar/', apis_reducoes.api_post_reducao_regra, name='api_post_reducao_regra'),
    path('api/reducao-regras/deletar/', apis_reducoes.api_post_deletar_reducao_regra, name='api_post_deletar_reducao_regra'),
    path('api/reducoes-funcionario/', apis_reducoes.api_get_reducoes_funcionario, name='api_get_reducoes_funcionario'),
    path('api/reducoes-funcionario/nova/', apis_reducoes.api_post_reducao_funcionario, name='api_post_reducao_funcionario'),
    path('api/reducoes-funcionario/deletar/', apis_reducoes.api_post_deletar_reducao_funcionario, name='api_post_deletar_reducao_funcionario'),
    path('api/calculo/preview/', apis_calculo.api_get_preview_calculo, name='api_get_preview_calculo'),
    path('api/calculo/mes/', apis_calculo.api_get_calculo_mes, name='api_get_calculo_mes'),
    path('api/calculo/listar/', apis_calculo.api_get_calculos, name='api_get_calculos'),
    path('api/calculo/calcular/', apis_calculo.api_post_calcular_bonificacao, name='api_post_calcular_bonificacao'),
    path('api/calculo/calcular-lote/', apis_calculo.api_post_calcular_lote, name='api_post_calcular_lote'),
    path('api/calculo/deletar/', apis_calculo.api_post_deletar_calculo, name='api_post_deletar_calculo'),
]
