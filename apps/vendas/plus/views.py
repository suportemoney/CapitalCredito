from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.seguranca.permissoes.decorators import controle_acess

from .permissoes_codigos import COD_SS_ESTEIRA, COD_SS_GERENCIADOR


@login_required(login_url='/')
@controle_acess(COD_SS_ESTEIRA)
def render_esteira(request):
    return render(request, 'plus/v2/esteira.html')


@login_required(login_url='/')
@controle_acess(COD_SS_GERENCIADOR)
def render_gerenciador(request):
    return render(request, 'plus/v2/gerenciador.html')
