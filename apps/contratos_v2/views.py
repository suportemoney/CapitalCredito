# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from apps.contratos_v2.permissoes_codigos import (
    COD_SS_CATALOGOS,
    COD_SS_ESTEIRA,
    COD_SS_RELATORIO_CMS,
)
from apps.seguranca.permissoes.decorators import controle_acess
from apps.rh.funcionarios.models import Funcionario


@login_required
@controle_acess(COD_SS_ESTEIRA)
def render_contratos_index(request):
    return redirect('contratos:crm_operacional_v2')


@login_required
@controle_acess(COD_SS_ESTEIRA)
def render_dashboard_operacional_v2(request):
    """Dashboard operacional com KPIs, produção e pendências."""
    return render(request, 'contratos/v2/dashboard_operacional.html', {
        'is_superuser': request.user.is_superuser or request.user.is_staff,
    })


@login_required
@controle_acess(COD_SS_ESTEIRA)
def render_crm_operacional_v2(request):
    return render(request, 'contratos/v2/crm_operacional.html', {'is_superuser': request.user.is_superuser or request.user.is_staff})


@login_required
@controle_acess(COD_SS_CATALOGOS)
def render_config_contratos_v2(request):
    try:
        func = Funcionario.objects.select_related('dados_profissionais__cargo').get(
            usuario=request.user, status=True
        )
        dp = getattr(func, 'dados_profissionais', None)
        cargo_nome = (
            (dp.cargo.nome or '').strip().upper() if dp and dp.cargo_id else ''
        )
        if 'VENDEDOR' in cargo_nome:
            return HttpResponseForbidden('Acesso negado.')
    except Funcionario.DoesNotExist:
        pass
    return render(request, 'contratos/v2/config.html', {'is_superuser': request.user.is_superuser or request.user.is_staff})


@login_required
@controle_acess(COD_SS_RELATORIO_CMS)
def render_relatorio_cms(request):
    """Relatório CMS (Financeiro — Jaci): tabela filtrável com pagamentos
    agrupados por contrato, permitindo marcar Pago CMS Empresa e ajustar
    percentual sobre AF (itens 10 e 11 do plano de atualização)."""
    return render(
        request,
        'contratos/v2/relatorio_cms.html',
        {'is_superuser': request.user.is_superuser or request.user.is_staff},
    )
