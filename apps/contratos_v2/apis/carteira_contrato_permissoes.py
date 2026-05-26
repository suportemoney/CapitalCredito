# -*- coding: utf-8 -*-
"""Regras de vínculo carteira SIAPE ↔ contrato (vendedor corrigindo pendências)."""
from django.db.models import Q

from apps.contratos_v2.fluxo_constants import EtapaOperacional
from apps.contratos_v2.models import ContratoExecucao, Pendencia


def contrato_vinculado_carteiras_responsavel(user, ce: ContratoExecucao) -> bool:
    """True se o contrato pertence a alguma carteira ativa do usuário (fluxo típico vendedor)."""
    from apps.vendas.siape.models import CarteiraClientes

    q_status = Q(status='ATIVO') | Q(status__isnull=True) | Q(status='')
    q_dono = Q(user_responsavel=user) | Q(user_repasse=user)

    if ce.cliente_dados_pessoais_id:
        if (
            CarteiraClientes.objects.filter(q_dono)
            .filter(q_status, cliente_operacional_id=ce.cliente_dados_pessoais_id)
            .exists()
        ):
            return True

    cids = list(
        CarteiraClientes.objects.filter(q_dono)
        .filter(q_status)
        .values_list('pk', flat=True)
    )
    if not cids:
        return False
    if ce.solicitacao_digitacao_id:
        sol = ce.solicitacao_digitacao
        cid = getattr(sol, 'carteira_clientes_id', None)
        if cid and cid in cids:
            return True
    pd = getattr(ce, 'proposta_dados', None)
    if pd and pd.solicitacao_origem_id:
        spc = pd.solicitacao_origem
        cid = getattr(spc, 'carteira_clientes_id', None)
        if cid and cid in cids:
            return True
    try:
        if ce.carteiras_siape.filter(pk__in=cids).exists():
            return True
    except Exception:
        pass
    return False


def pendencia_tipos_abertos(ce: ContratoExecucao):
    """Conjunto de tipos (strings) com pendência não resolvida."""
    return set(
        Pendencia.objects.filter(contrato_execucao=ce, resolvido=False).values_list('tipo', flat=True)
    )


def pode_visualizar_contrato_ficha_ou_midia(user, ce: ContratoExecucao) -> bool:
    """
    Leitura de ficha / lista de mídia-arquivos: CRM operacional (SCT189), supervisão (SCT201),
    pendência na carteira do vendedor ou consultor SIAPE (SCT16) com contrato na própria carteira.
    """
    from apps.seguranca.permissoes.utils import user_has_access

    if user_has_access(user, 'SCT189') or user_has_access(user, 'SCT201'):
        return True
    if vendedor_pode_acesso_pendencia_contrato(user, ce):
        return True
    if user_has_access(user, 'SCT16') and contrato_vinculado_carteiras_responsavel(user, ce):
        return True
    return False


def vendedor_pode_acesso_pendencia_contrato(user, ce: ContratoExecucao) -> bool:
    """Dono da carteira com contrato em PENDENCIAS e pendência aberta."""
    if ce.etapa_operacional != EtapaOperacional.PENDENCIAS:
        return False
    if not Pendencia.objects.filter(contrato_execucao=ce, resolvido=False).exists():
        return False
    return contrato_vinculado_carteiras_responsavel(user, ce)


def vendedor_pode_anexar_arquivo_pendencia(user, ce: ContratoExecucao) -> bool:
    if not vendedor_pode_acesso_pendencia_contrato(user, ce):
        return False
    return Pendencia.TIPO_FALTA_ARQUIVO in pendencia_tipos_abertos(ce)


def lojista_pode_acessar_proposta_dados(user, proposta_dados_id) -> bool:
    """CapitalCredito não usa loja INSS — apenas carteira SIAPE."""
    if user.is_superuser:
        return True
    if not proposta_dados_id:
        return False
    from apps.contratos_v2.models import PropostaDados
    from apps.vendas.siape.models import CarteiraClientes

    return PropostaDados.objects.filter(
        id=proposta_dados_id,
        carteiras_siape_propostas__user_responsavel=user,
    ).exists() or PropostaDados.objects.filter(
        id=proposta_dados_id,
        carteiras_siape_propostas__user_repasse=user,
    ).exists()


def lojista_pode_acessar_contrato(user, contrato) -> bool:
    if user.is_superuser:
        return True
    return lojista_pode_acessar_proposta_dados(user, getattr(contrato, 'proposta_dados_id', None))
