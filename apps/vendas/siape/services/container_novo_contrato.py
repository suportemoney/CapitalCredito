# -*- coding: utf-8 -*-
"""Montagem do payload do container operacional (CX48) na consulta SIAPE."""
from django.contrib.auth.models import User

from apps.contratos_v2.apis.carteira_contrato_permissoes import vendedor_pode_acesso_pendencia_contrato
from apps.contratos_v2.fluxo_constants import (
    EstadoSolicitacaoDigitacao,
    EtapaOperacional,
    SubStatusOperacional,
)
from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor
from apps.contratos_v2.models import ContratoExecucao, PropostaDados, SolicitacaoDigitacao
from apps.vendas.siape.models import CarteiraClientes


def _label_choice(choices, value):
    if not value:
        return ''
    return dict(choices).get(value, value)


def _status_linha(contrato, solicitacao):
    if contrato:
        etapa = _label_choice(EtapaOperacional.CHOICES, contrato.etapa_operacional)
        sub = _label_choice(SubStatusOperacional.CHOICES, contrato.sub_status_operacional)
        return f'{etapa} · {sub}'.strip(' ·')
    if solicitacao:
        return _label_choice(EstadoSolicitacaoDigitacao.CHOICES, solicitacao.estado)
    return 'Aguardando contrato'


def _montar_item_proposta(user, carteira, pd, contrato, solicitacao):
    link_formalizacao = ''
    contrato_id = None
    contrato_codigo = ''
    etapa_operacional = ''
    sub_status_operacional = ''
    solicitacao_digitacao_id = None
    tem_pendencia = False
    exibir_botao_fazer_checagem = False
    exibir_botao_formalizar_checado = False
    exibir_botao_enviar_video = False
    exibir_btn_arquivos = False
    exibir_btn_sanar_pendencia = False

    if contrato:
        contrato_id = contrato.id
        contrato_codigo = contrato.codigo or ''
        etapa_operacional = contrato.etapa_operacional or ''
        sub_status_operacional = contrato.sub_status_operacional or ''
        link_formalizacao = (contrato.link_formalizacao or '').strip()
        solicitacao_digitacao_id = contrato.solicitacao_digitacao_id
        tem_pendencia = contrato.etapa_operacional == EtapaOperacional.PENDENCIAS
        exibir_btn_sanar_pendencia = vendedor_pode_acesso_pendencia_contrato(user, contrato)

        sub_com_link = sub_status_operacional in (
            SubStatusOperacional.DIG_LINK_DISPONIBILIZADO,
            SubStatusOperacional.FORM_LINK_DISPONIVEL,
        )
        sub_checado = sub_status_operacional in (
            SubStatusOperacional.DIG_CHECADO,
            SubStatusOperacional.FORM_CHECADO,
        )
        exibir_botao_fazer_checagem = bool(contrato_id and link_formalizacao and sub_com_link)
        exibir_botao_formalizar_checado = bool(contrato_id and link_formalizacao and sub_checado)
        exibir_botao_enviar_video = contrato_exibe_botao_enviar_video_vendedor(contrato)
        etapa_arq = contrato.etapa_operacional or ''
        exibir_btn_arquivos = etapa_arq not in (EtapaOperacional.PAGAMENTO, EtapaOperacional.CANCELADO)

    elif solicitacao:
        solicitacao_digitacao_id = solicitacao.id
        link_formalizacao = (solicitacao.link_formalizacao_pre or '').strip()
        tem_pendencia = solicitacao.estado == EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO
        exibir_btn_sanar_pendencia = tem_pendencia
        exibir_btn_arquivos = solicitacao.estado in (
            EstadoSolicitacaoDigitacao.PENDENTE_CORRECAO,
            EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
            EstadoSolicitacaoDigitacao.EM_DIGITACAO,
        )

    return {
        'proposta_id': pd.id,
        'proposta_codigo': pd.codigo or '',
        'banco': pd.banco.titulo if pd.banco_id else '',
        'produto': pd.produto.titulo if pd.produto_id else '',
        'contrato_id': contrato_id,
        'contrato_codigo': contrato_codigo,
        'etapa_operacional': etapa_operacional,
        'sub_status_operacional': sub_status_operacional,
        'status_linha': _status_linha(contrato, solicitacao),
        'link_formalizacao': link_formalizacao,
        'tem_pendencia': tem_pendencia,
        'solicitacao_digitacao_id': solicitacao_digitacao_id,
        'exibir_botao_fazer_checagem': exibir_botao_fazer_checagem,
        'exibir_botao_formalizar_checado': exibir_botao_formalizar_checado,
        'exibir_botao_enviar_video': exibir_botao_enviar_video,
        'exibir_btn_arquivos': exibir_btn_arquivos,
        'exibir_btn_sanar_pendencia': exibir_btn_sanar_pendencia,
        'acao_evoluir_checagem': 'vendedor_checado_formalizacao',
        'acao_evoluir_formalizado': 'vendedor_formalizado_desde_link',
    }


def _resolver_contrato_solicitacao(carteira, pd):
    contrato = (
        ContratoExecucao.objects.filter(proposta_dados=pd, status=True)
        .order_by('-data_ultima_atualizacao')
        .first()
    )
    solicitacao = None
    if not contrato:
        solicitacao = (
            SolicitacaoDigitacao.objects.filter(
                proposta_dados=pd,
                carteira_clientes=carteira,
            )
            .exclude(estado__in=(
                EstadoSolicitacaoDigitacao.CANCELADA,
                EstadoSolicitacaoDigitacao.CONTRATO_GERADO,
            ))
            .order_by('-data_criacao')
            .first()
        )
    return contrato, solicitacao


def _nome_cpf_cliente_carteira(carteira, pd):
    cliente = carteira.cliente if carteira else None
    nome = (cliente.nome if cliente else '') or ''
    cpf = (cliente.cpf if cliente else '') or ''
    if not nome and pd.cliente_dados_pessoais_id:
        dp = pd.cliente_dados_pessoais
        nome = (dp.nome_completo or '') if dp else nome
        cpf = (dp.cpf or '') if dp else cpf
    return nome, cpf


def _status_carteira_resumo(carteira):
    parts = []
    tab = (carteira.tabulacao_operacional or '').strip()
    tag = (carteira.tag_status_operacional or '').strip()
    st = (carteira.status_comercial or '').strip()
    if tab:
        parts.append(tab)
    if tag:
        parts.append(tag)
    if st:
        parts.append(st)
    return ' · '.join(parts) if parts else ''


def montar_container_novo_contrato(carteira: CarteiraClientes, user: User) -> dict:
    """Retorna payload JSON do container para a carteira do vendedor logado."""
    cliente = carteira.cliente
    cliente_nome = (cliente.nome if cliente else '') or ''
    cliente_cpf = (cliente.cpf if cliente else '') or ''

    propostas = (
        PropostaDados.objects.filter(
            carteiras_siape_propostas=carteira,
            criado_por=user,
        )
        .select_related('banco', 'produto', 'convenio')
        .order_by('-data_criacao')
    )

    itens = []
    for pd in propostas:
        contrato, solicitacao = _resolver_contrato_solicitacao(carteira, pd)
        itens.append(_montar_item_proposta(user, carteira, pd, contrato, solicitacao))

    tabulacao = (carteira.tabulacao_operacional or '').strip()
    tag_status = (carteira.tag_status_operacional or '').strip()
    status_comercial = (carteira.status_comercial or '').strip()

    return {
        'ok': True,
        'modo': 'carteira',
        'carteira_id': carteira.id,
        'cliente_nome': cliente_nome,
        'cliente_cpf': cliente_cpf,
        'tabulacao_operacional': tabulacao,
        'tag_status_operacional': tag_status,
        'status_comercial': status_comercial,
        'tag_proposta_container': (carteira.tag_proposta_container or '').strip(),
        'sub_status_propostas_comercial': (carteira.sub_status_propostas_comercial or '').strip(),
        'itens': itens,
    }


def montar_container_todas_propostas(user: User, limite: int = 100) -> dict:
    """Lista todas as propostas do vendedor logado (sem filtro de cliente)."""
    propostas = (
        PropostaDados.objects.filter(
            criado_por=user,
            carteiras_siape_propostas__user_responsavel=user,
        )
        .select_related('banco', 'produto', 'convenio', 'cliente_dados_pessoais')
        .distinct()
        .order_by('-data_criacao')[:limite]
    )

    itens = []
    for pd in propostas:
        carteira = (
            CarteiraClientes.objects.filter(
                user_responsavel=user,
                propostas_operacionais=pd,
            )
            .select_related('cliente')
            .order_by('-id')
            .first()
        )
        if not carteira:
            continue
        contrato, solicitacao = _resolver_contrato_solicitacao(carteira, pd)
        item = _montar_item_proposta(user, carteira, pd, contrato, solicitacao)
        nome, cpf = _nome_cpf_cliente_carteira(carteira, pd)
        item['cliente_nome'] = nome
        item['cliente_cpf'] = cpf
        item['carteira_id'] = carteira.id
        item['carteira_status'] = _status_carteira_resumo(carteira)
        itens.append(item)

    return {
        'ok': True,
        'modo': 'todas',
        'carteira_id': None,
        'cliente_nome': '',
        'cliente_cpf': '',
        'tabulacao_operacional': '',
        'tag_status_operacional': '',
        'status_comercial': '',
        'tag_proposta_container': '',
        'sub_status_propostas_comercial': '',
        'itens': itens,
    }
