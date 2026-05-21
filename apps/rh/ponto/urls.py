from django.urls import path
from . import views
from .apis import registro as apis_registro
from .apis import justificativas as apis_justificativas
from .apis import relatorio as apis_relatorio
from .apis import horario as apis_horario

app_name = 'ponto'

urlpatterns = [
    path('', views.render_index, name='index'),
    path('justificativas/', views.render_justificativas, name='justificativas'),
    path('relatorio/', views.render_relatorio, name='relatorio'),
    path('horario-trabalho/', views.render_horario_trabalho, name='horario_trabalho'),
    path('api/registro/registrar/', apis_registro.api_registrar_ponto, name='api_registrar_ponto'),
    path('api/registro/listar-dia/', apis_registro.api_listar_pontos_dia, name='api_listar_pontos_dia'),
    path('api/registro/ajustar-horario/', apis_registro.api_ajustar_horario, name='api_ajustar_horario'),
    path('api/justificativas/criar/', apis_justificativas.api_criar_justificativa, name='api_criar_justificativa'),
    path('api/justificativas/listar/', apis_justificativas.api_listar_justificativas, name='api_listar_justificativas'),
    path('api/relatorio/presenca/', apis_relatorio.api_relatorio_presenca, name='api_relatorio_presenca'),
    path('api/horario/configurar/', apis_horario.api_configurar_horario, name='api_configurar_horario'),
    path('api/horario/buscar/', apis_horario.api_buscar_configuracao, name='api_buscar_configuracao'),
]
