# -*- coding: utf-8 -*-
"""Repasse de carteira SIAPE no fluxo operacional (CRM / Pago TC / RegisterMoney)."""


def _nome_user(user):
    if not user:
        return ''
    return (user.get_full_name() or user.username or '').strip()


def carteira_clientes_para_contrato_execucao(ce):
    """
    Carteira SIAPE ligada ao contrato: solicitação de digitação ou vínculos M2M.
    Espelha a lógica de fluxo_transicoes._carteira_clientes_para_contrato_execucao.
    """
    from apps.vendas.siape.models import CarteiraClientes

    sol = ce.solicitacao_digitacao if getattr(ce, 'solicitacao_digitacao_id', None) else None
    if sol and getattr(sol, 'carteira_clientes_id', None):
        return sol.carteira_clientes
    cart = CarteiraClientes.objects.filter(contratos_operacionais=ce).first()
    if cart:
        return cart
    if getattr(ce, 'proposta_dados_id', None):
        return CarteiraClientes.objects.filter(propostas_operacionais=ce.proposta_dados_id).first()
    return None


def kwargs_snapshot_repasse_contrato(carteira):
    """
    Campos para ContratoExecucao.objects.create quando a carteira tem repasse ativo.
    """
    if not carteira or not getattr(carteira, 'user_repasse_id', None):
        return {}
    return {
        'carteira_clientes_snapshot_id': carteira.id,
        'user_repasse_snapshot_id': carteira.user_repasse_id,
    }


def resolver_contexto_repasse_contrato(ce):
    """
    Contexto de repasse para Pago TC / RegisterMoney / modal CRM.

    Prioridade: snapshot no contrato > carteira da solicitação > M2M da carteira.
    """
    cart = None
    user_repasse_id = None
    user_responsavel_id = None

    snap_repasse_id = getattr(ce, 'user_repasse_snapshot_id', None)
    snap_cart_id = getattr(ce, 'carteira_clientes_snapshot_id', None)
    if snap_repasse_id:
        user_repasse_id = snap_repasse_id
        if snap_cart_id:
            cart = getattr(ce, 'carteira_clientes_snapshot', None)
            if cart is None:
                from apps.vendas.siape.models import CarteiraClientes

                cart = (
                    CarteiraClientes.objects.filter(pk=snap_cart_id)
                    .select_related('user_responsavel', 'user_repasse')
                    .first()
                )
        if cart:
            user_responsavel_id = cart.user_responsavel_id
        else:
            sol = ce.solicitacao_digitacao if getattr(ce, 'solicitacao_digitacao_id', None) else None
            if sol and getattr(sol, 'carteira_clientes_id', None):
                c2 = sol.carteira_clientes
                user_responsavel_id = getattr(c2, 'user_responsavel_id', None)
    else:
        sol = ce.solicitacao_digitacao if getattr(ce, 'solicitacao_digitacao_id', None) else None
        if sol and getattr(sol, 'carteira_clientes_id', None):
            cart = sol.carteira_clientes
        if not cart:
            cart = carteira_clientes_para_contrato_execucao(ce)
        if cart:
            user_repasse_id = cart.user_repasse_id
            user_responsavel_id = cart.user_responsavel_id

    ur = getattr(cart, 'user_responsavel', None) if cart else None
    ux = None
    if user_repasse_id:
        if cart and getattr(cart, 'user_repasse_id', None) == user_repasse_id:
            ux = getattr(cart, 'user_repasse', None)
        if ux is None:
            from django.contrib.auth.models import User

            ux = User.objects.filter(pk=user_repasse_id).first()

    nome_responsavel = _nome_user(ur)
    nome_repasse = _nome_user(ux)
    tem_repasse = bool(user_repasse_id and user_responsavel_id)

    destinatarios = []
    if tem_repasse:
        destinatarios = [
            {'user_id': user_responsavel_id, 'nome': nome_responsavel or '—', 'papel': 'responsável'},
            {'user_id': user_repasse_id, 'nome': nome_repasse or '—', 'papel': 'repasse'},
        ]
    elif user_responsavel_id:
        destinatarios = [
            {'user_id': user_responsavel_id, 'nome': nome_responsavel or '—', 'papel': 'responsável'},
        ]

    return {
        'tem_repasse': tem_repasse,
        'carteira_id': cart.id if cart else snap_cart_id,
        'user_responsavel_id': user_responsavel_id,
        'user_repasse_id': user_repasse_id,
        'nome_responsavel': nome_responsavel,
        'nome_repasse': nome_repasse,
        'destinatarios': destinatarios,
        'user_responsavel': ur,
        'user_repasse': ux,
    }


def repasse_dict_esteira_ficha(ce_or_sol):
    """Campos JSON para esteira CRM e ficha (a partir de contrato ou solicitação)."""
    if hasattr(ce_or_sol, 'user_repasse_snapshot_id'):
        ce = ce_or_sol
    else:
        ce = getattr(ce_or_sol, 'contrato_execucao', None)
        if ce is None and hasattr(ce_or_sol, 'carteira_clientes'):
            ctx = resolver_contexto_repasse_contrato_from_carteira(ce_or_sol.carteira_clientes)
            return ctx
        if ce is None:
            return {
                'tem_repasse': False,
                'nome_repasse': '',
                'nome_responsavel_carteira': '',
                'solicitante_label': '',
            }
    ctx = resolver_contexto_repasse_contrato(ce)
    label = ''
    if ctx['tem_repasse']:
        resp = ctx['nome_responsavel'] or '—'
        rep = ctx['nome_repasse'] or '—'
        label = f'{resp} (repasse: {rep})'
    return {
        'tem_repasse': ctx['tem_repasse'],
        'nome_repasse': ctx['nome_repasse'],
        'nome_responsavel_carteira': ctx['nome_responsavel'],
        'solicitante_label': label,
    }


def resolver_contexto_repasse_contrato_from_carteira(carteira):
    """Contexto mínimo a partir só da carteira (solicitação ainda sem contrato)."""
    if not carteira or not getattr(carteira, 'user_repasse_id', None):
        ur = getattr(carteira, 'user_responsavel', None) if carteira else None
        return {
            'tem_repasse': False,
            'nome_repasse': '',
            'nome_responsavel_carteira': _nome_user(ur),
            'solicitante_label': '',
        }
    ur = carteira.user_responsavel
    ux = carteira.user_repasse
    nome_responsavel = _nome_user(ur)
    nome_repasse = _nome_user(ux)
    return {
        'tem_repasse': True,
        'nome_repasse': nome_repasse,
        'nome_responsavel_carteira': nome_responsavel,
        'solicitante_label': f'{nome_responsavel or "—"} (repasse: {nome_repasse or "—"})',
    }


def repasse_dict_ficha(carteira=None, ce=None, nome_solicitante_criador=''):
    """
    Payload JSON para Ficha do Registro e telas operacionais.
    Informa se há repasse, quem repassou o cliente e quem é o responsável/solicitante atual.
    """
    nome_criador = (nome_solicitante_criador or '').strip()
    if ce is not None:
        ctx = resolver_contexto_repasse_contrato(ce)
        nome_resp = ctx.get('nome_responsavel') or ''
        nome_rep = ctx.get('nome_repasse') or ''
        tem = bool(ctx.get('tem_repasse'))
    elif carteira is not None:
        ctx = resolver_contexto_repasse_contrato_from_carteira(carteira)
        nome_resp = ctx.get('nome_responsavel_carteira') or ''
        nome_rep = ctx.get('nome_repasse') or ''
        tem = bool(ctx.get('tem_repasse'))
    else:
        nome_resp = nome_rep = ''
        tem = False

    if tem:
        resumo = (
            f'Cliente em repasse: {nome_rep or "—"} repassou o cliente para '
            f'{nome_resp or "—"} (solicitante/responsável atual).'
        )
        if nome_criador and nome_criador != nome_resp:
            resumo += f' Solicitação registrada por {nome_criador}.'
    else:
        resumo = 'Esta carteira não possui repasse (vendedor único na negociação).'
        if nome_criador:
            resumo = f'Solicitante: {nome_criador}. Sem repasse de carteira.'

    return {
        'tem_repasse': tem,
        'nome_responsavel': nome_resp,
        'nome_repasse': nome_rep,
        'nome_solicitante_criador': nome_criador,
        'resumo': resumo,
    }
