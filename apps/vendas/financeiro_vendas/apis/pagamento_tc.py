# -*- coding: utf-8 -*-
"""APIs da página Pagamento TC (financeiro_vendas) — delega lógica ao contratos_v2."""
import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from apps.contratos_v2.apis.fluxo import (
    _montar_pago_tc_modal_defaults,
    _montar_registermoney_extra_supervisor_pago_tc,
    serialize_envios_comprovante_pagamento_vendedor,
)
from apps.contratos_v2.apis.acoes_crm import (
    RegisterMoney_has_for_ce,
    _contrato_tem_dados_operacionais,
    _decrementar_acumulado_rm,
    _json,
    _refresh_ce_e_relacionados_valor_tc,
    _registrar_comprovante_tc_sem_rm,
    _rm_payload_de_registermoney_post,
    _soma_comprovantes,
    _valor_est_json_registermoney_post,
    _valor_tc_do_contrato,
    _dec,
)
from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
from apps.contratos_v2.fluxo_transicoes import (
    PAPEL_OPERACIONAL,
    _registrar_historico,
    aplicar_etapa_sub,
    persistir_tc_modal_em_contrato_e_rm,
    sincronizar_register_money_dados_modal_pago_tc,
    transicao_por_acao,
    zerar_tc_modal_em_contrato,
)
from apps.contratos_v2.models import ComprovanteTC, ContratoExecucao, ContratoDadosOperacionais
from apps.seguranca.permissoes.decorators import controle_acess

logger = logging.getLogger(__name__)

COD_PAGAMENTO_TC = 'SCT52'

_SUBS_LISTA = (
    SubStatusOperacional.PG_PAGO_CLIENTE,
    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
    SubStatusOperacional.PG_PAGO_TC_TOTAL,
    SubStatusOperacional.PG_PAGO_TC,
)

_SUB_LABEL = dict(SubStatusOperacional.CHOICES)


def _ce_pagamento_tc_qs():
    return ContratoExecucao.objects.filter(
        status=True,
        etapa_operacional=EtapaOperacional.PAGAMENTO,
        sub_status_operacional__in=_SUBS_LISTA,
    ).select_related(
        'cliente_dados_pessoais',
        'dados_operacionais',
        'dados_operacionais__produto',
        'dados_operacionais__banco',
        'solicitacao_digitacao__criado_por',
        'solicitacao_digitacao__carteira_clientes__user_responsavel',
    )


def _nome_vendedor(ce):
    try:
        sol = ce.solicitacao_digitacao
        if sol and sol.carteira_clientes_id and sol.carteira_clientes.user_responsavel_id:
            u = sol.carteira_clientes.user_responsavel
            return (u.get_full_name() or u.username) if u else '—'
        if sol and sol.criado_por_id:
            u = sol.criado_por
            return (u.get_full_name() or u.username) if u else '—'
    except Exception:
        pass
    return '—'


def _fmt_dec(v):
    if v is None:
        return ''
    try:
        return str(Decimal(str(v)).quantize(Decimal('0.01')))
    except Exception:
        return str(v)


def _validar_ce_pagamento_tc(ce, permitir_parcial=False):
    if ce.etapa_operacional != EtapaOperacional.PAGAMENTO:
        return 'Contrato não está na etapa Pagamento.'
    subs_ok = {SubStatusOperacional.PG_PAGO_CLIENTE}
    if permitir_parcial:
        subs_ok.add(SubStatusOperacional.PG_PAGO_TC_PARCIAL)
    if ce.sub_status_operacional not in subs_ok:
        return 'Contrato não está em status compatível com esta ação.'
    return None


def _serializar_linha(ce):
    sub = ce.sub_status_operacional or ''
    d = None
    try:
        d = ce.dados_operacionais
    except Exception:
        d = None
    produto = ''
    banco = ''
    valor_af = None
    valor_tc = _valor_tc_do_contrato(ce)
    if d:
        if d.produto_id:
            produto = (d.produto.titulo or '')[:120]
        banco_obj = getattr(d, 'banco', None)
        if banco_obj is not None and hasattr(banco_obj, 'titulo'):
            banco = (banco_obj.titulo or '').strip()
        if d.valor_af is not None:
            valor_af = d.valor_af
    soma = _soma_comprovantes(ce)
    pode_pagar = sub == SubStatusOperacional.PG_PAGO_CLIENTE
    pode_comp = sub in (
        SubStatusOperacional.PG_PAGO_CLIENTE,
        SubStatusOperacional.PG_PAGO_TC_PARCIAL,
    )
    aba = 'aguardando'
    if sub == SubStatusOperacional.PG_PAGO_TC_PARCIAL:
        aba = 'parcial'
    elif sub in (SubStatusOperacional.PG_PAGO_TC_TOTAL, SubStatusOperacional.PG_PAGO_TC):
        aba = 'concluidos'
    cpf = ''
    nome = ''
    if ce.cliente_dados_pessoais_id:
        cpf = (ce.cliente_dados_pessoais.cpf or '').strip()
        nome = (
            getattr(ce.cliente_dados_pessoais, 'nome_completo', None)
            or getattr(ce.cliente_dados_pessoais, 'nome', None)
            or ''
        ).strip()
    return {
        'contrato_id': ce.id,
        'codigo': ce.codigo or '',
        'cliente_nome': nome or '—',
        'cpf': cpf,
        'vendedor': _nome_vendedor(ce),
        'produto': produto or '—',
        'banco': banco or '—',
        'valor_af': _fmt_dec(valor_af),
        'valor_tc': _fmt_dec(valor_tc),
        'tc_pago_acumulado': _fmt_dec(soma),
        'sub_status': sub,
        'sub_label': _SUB_LABEL.get(sub, sub),
        'pode_pagar_tc': pode_pagar,
        'pode_comprovante': pode_comp,
        'aba': aba,
    }


@login_required
@require_GET
@controle_acess(COD_PAGAMENTO_TC)
def api_listar_pagamento_tc(request):
    """Lista contratos v2 elegíveis para Pagamento TC."""
    try:
        itens = [_serializar_linha(ce) for ce in _ce_pagamento_tc_qs().order_by('-data_ultima_atualizacao', '-id')]
        return JsonResponse({'ok': True, 'itens': itens})
    except Exception as exc:
        logger.exception('api_listar_pagamento_tc')
        return JsonResponse({'ok': False, 'erro': 'Erro ao listar contratos.'}, status=500)


@login_required
@require_GET
@controle_acess(COD_PAGAMENTO_TC)
def api_modal_defaults_pagamento_tc(request):
    """Defaults do modal Pago TC para um contrato."""
    try:
        contrato_id = int(request.GET.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    if contrato_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)

    ce = get_object_or_404(_ce_pagamento_tc_qs(), pk=contrato_id)
    if ce.sub_status_operacional != SubStatusOperacional.PG_PAGO_CLIENTE:
        return JsonResponse({'ok': False, 'erro': 'Modal completo disponível apenas para Pago Cliente.'}, status=400)

    ptc = _montar_pago_tc_modal_defaults(ce)
    if not ptc:
        return JsonResponse({'ok': False, 'erro': 'Sem dados operacionais para o modal.'}, status=400)
    return JsonResponse({'ok': True, 'pago_tc_modal': ptc})


@login_required
@require_POST
@controle_acess(COD_PAGAMENTO_TC)
def api_salvar_dados_pagamento_tc(request):
    """Salva TC, classificador e loja sem evoluir sub-status."""
    data = _json(request)
    try:
        contrato_id = int(data.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    if contrato_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        err_st = _validar_ce_pagamento_tc(ce, permitir_parcial=False)
        if err_st:
            return JsonResponse({'ok': False, 'erro': err_st}, status=400)

        rm_dict, err_rm = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
        if err_rm:
            return JsonResponse({'ok': False, 'erro': err_rm}, status=400)
        if not rm_dict:
            return JsonResponse({'ok': False, 'erro': 'Dados do modal inválidos.'}, status=400)

        soma = _soma_comprovantes(ce)
        valor_est = rm_dict.get('valor_est') or Decimal('0')
        valor_tc_antes = _valor_tc_do_contrato(ce)
        observacao = (data.get('observacao') or '').strip() or 'Ajuste dados Pago TC (financeiro)'
        tc_zerado = False

        with transaction.atomic():
            if valor_est > 0:
                ok_p, err_p = persistir_tc_modal_em_contrato_e_rm(ce, valor_est, soma)
                if not ok_p:
                    raise RuntimeError(err_p or 'Falha ao persistir Valor TC.')
            elif valor_tc_antes > 0:
                ok_z, err_z = zerar_tc_modal_em_contrato(ce)
                if not ok_z:
                    raise RuntimeError(err_z or 'Falha ao zerar Valor TC.')
                tc_zerado = True
                observacao = (data.get('observacao') or '').strip() or 'Zerar Valor TC (financeiro)'

            af = rm_dict.get('af')
            if af is not None and _contrato_tem_dados_operacionais(ce):
                d = ce.dados_operacionais
                d.valor_af = af
                d.save(update_fields=['valor_af'])
            if af is not None and ce.proposta_dados_id:
                pd = ce.proposta_dados
                pd.valor_af = af
                pd.save(update_fields=['valor_af'])

            ok_rm, err_sync = sincronizar_register_money_dados_modal_pago_tc(ce, rm_dict)
            if not ok_rm:
                raise RuntimeError(err_sync or 'Falha ao sincronizar RegisterMoney.')

            _registrar_historico(
                ce,
                ce.etapa_operacional,
                ce.sub_status_operacional,
                ce.etapa_operacional,
                ce.sub_status_operacional,
                request.user,
                observacao[:500],
            )

        _refresh_ce_e_relacionados_valor_tc(ce)
        valor_tc_resp = _valor_tc_do_contrato(ce)
        return JsonResponse({
            'ok': True,
            'valor_tc': str(valor_tc_resp),
            'valor_est_tc': str(valor_tc_resp),
            'soma_acumulada': str(_soma_comprovantes(ce)),
            'sub_status': str(ce.sub_status_operacional or ''),
            'tc_zerado': tc_zerado,
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except Exception:
        logger.exception('api_salvar_dados_pagamento_tc contrato_id=%s', contrato_id)
        return JsonResponse({'ok': False, 'erro': 'Erro ao salvar dados.'}, status=500)


@login_required
@require_GET
@controle_acess(COD_PAGAMENTO_TC)
def api_comprovantes_pagamento_tc(request):
    """Lista comprovantes TC de um contrato."""
    contrato_id = request.GET.get('contrato_id')
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    ce = get_object_or_404(_ce_pagamento_tc_qs(), pk=int(contrato_id))
    itens = [
        {
            'id': c.id,
            'valor': str(c.valor),
            'arquivo_url': c.arquivo.url if c.arquivo else None,
            'criado_por': c.criado_por.username,
            'criado_em': c.criado_em.isoformat() if c.criado_em else None,
        }
        for c in ComprovanteTC.objects.filter(contrato_execucao=ce, status=True)
        .select_related('criado_por')
        .order_by('criado_em')
    ]
    envios_vendedor = serialize_envios_comprovante_pagamento_vendedor(request, ce)
    return JsonResponse({
        'ok': True,
        'comprovantes': itens,
        'envios_vendedor': envios_vendedor,
        'soma': str(_soma_comprovantes(ce)),
        'valor_tc': str(_valor_tc_do_contrato(ce)),
        'sub_status': str(ce.sub_status_operacional or ''),
    })


@login_required
@require_POST
@controle_acess(COD_PAGAMENTO_TC)
def api_upload_comprovante_pagamento_tc(request):
    """Upload de comprovante TC (delega ao fluxo v2 + sync ranking)."""
    try:
        contrato_id = int(request.POST.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    valor = _dec(request.POST.get('valor'))
    arquivo = request.FILES.get('arquivo')
    if valor is None or valor <= 0:
        return JsonResponse({'ok': False, 'erro': 'Valor inválido.'}, status=400)
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Anexe o comprovante.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        err_st = _validar_ce_pagamento_tc(ce, permitir_parcial=True)
        if err_st:
            return JsonResponse({'ok': False, 'erro': err_st}, status=400)

        rm_raw = request.POST.get('registermoney')
        novo_tc_modal = _valor_est_json_registermoney_post(rm_raw)
        valor_tc_pre = _valor_tc_do_contrato(ce)
        if valor_tc_pre <= 0 and (novo_tc_modal is None or novo_tc_modal <= 0):
            return JsonResponse(
                {
                    'ok': False,
                    'erro': 'Contrato sem valor de TC — informe o Valor TC no modal antes do comprovante.',
                },
                status=400,
            )

        rm_payload = None
        if not RegisterMoney_has_for_ce(ce) and (
            valor_tc_pre > 0 or (novo_tc_modal is not None and novo_tc_modal > 0)
        ):
            rm_payload, err_rm = _rm_payload_de_registermoney_post(rm_raw, ce)
            if err_rm:
                return JsonResponse({'ok': False, 'erro': err_rm}, status=400)

        comp, soma, valor_tc, total_atingido = _registrar_comprovante_tc_sem_rm(
            ce,
            valor,
            arquivo,
            request.user,
            observacao_extra=f'Comprovante TC (financeiro) — R$ {valor}',
            novo_tc_modal=novo_tc_modal,
            rm_payload=rm_payload,
        )
        ce.refresh_from_db()
        return JsonResponse({
            'ok': True,
            'comprovante_id': comp.id,
            'soma_acumulada': str(soma),
            'valor_tc': str(valor_tc),
            'total_atingido': total_atingido,
            'sub_status': str(ce.sub_status_operacional or ''),
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except Exception:
        logger.exception('api_upload_comprovante_pagamento_tc contrato_id=%s', contrato_id)
        return JsonResponse({'ok': False, 'erro': 'Erro ao registrar comprovante.'}, status=500)


@login_required
@require_POST
@controle_acess(COD_PAGAMENTO_TC)
def api_excluir_comprovante_pagamento_tc(request):
    """Exclusão de comprovante TC."""
    data = _json(request)
    try:
        contrato_id = int(data.get('contrato_id') or 0)
        comprovante_id = int(data.get('comprovante_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id ou comprovante_id inválido.'}, status=400)
    if contrato_id <= 0 or comprovante_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id e comprovante_id obrigatórios.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        err_st = _validar_ce_pagamento_tc(ce, permitir_parcial=True)
        if err_st and ce.sub_status_operacional not in (
            SubStatusOperacional.PG_PAGO_TC_PARCIAL,
            SubStatusOperacional.PG_PAGO_CLIENTE,
        ):
            return JsonResponse({'ok': False, 'erro': err_st}, status=400)

        comp = get_object_or_404(
            ComprovanteTC,
            pk=comprovante_id,
            contrato_execucao_id=contrato_id,
            status=True,
        )
        valor_excluido = comp.valor
        sub_antes = ce.sub_status_operacional
        observacao = (data.get('observacao') or '').strip() or f'Exclusão comprovante TC — R$ {valor_excluido}'

        with transaction.atomic():
            comp.status = False
            comp.save(update_fields=['status'])

            from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
                excluir_comprovante_v2_do_ranking,
            )

            excluir_comprovante_v2_do_ranking(comp.id)

            if RegisterMoney_has_for_ce(ce):
                _decrementar_acumulado_rm(ce, valor_excluido)

            soma = _soma_comprovantes(ce)
            valor_tc = _valor_tc_do_contrato(ce)
            if soma <= 0:
                if sub_antes in (
                    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
                    SubStatusOperacional.PG_PAGO_TC_TOTAL,
                    SubStatusOperacional.PG_PAGO_TC,
                ):
                    novo_sub = SubStatusOperacional.PG_AGUARDANDO_TC
                else:
                    novo_sub = SubStatusOperacional.PG_PAGO_CLIENTE
            elif valor_tc > 0:
                novo_sub = (
                    SubStatusOperacional.PG_PAGO_TC_TOTAL
                    if soma >= valor_tc
                    else SubStatusOperacional.PG_PAGO_TC_PARCIAL
                )
            else:
                novo_sub = ce.sub_status_operacional

            if novo_sub != ce.sub_status_operacional:
                ok, msg = aplicar_etapa_sub(
                    ce,
                    EtapaOperacional.PAGAMENTO,
                    novo_sub,
                    request.user,
                    observacao=observacao[:500],
                    sincronizar_legado=True,
                    inner_atomic=False,
                )
                if not ok:
                    raise RuntimeError(msg or 'Falha ao atualizar sub-status após exclusão.')
            else:
                _registrar_historico(
                    ce,
                    ce.etapa_operacional,
                    sub_antes,
                    ce.etapa_operacional,
                    ce.sub_status_operacional,
                    request.user,
                    observacao[:500],
                )

        ce.refresh_from_db()
        return JsonResponse({
            'ok': True,
            'soma_acumulada': str(_soma_comprovantes(ce)),
            'valor_tc': str(_valor_tc_do_contrato(ce)),
            'sub_status': str(ce.sub_status_operacional or ''),
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato ou comprovante não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except Exception:
        logger.exception(
            'api_excluir_comprovante_pagamento_tc contrato_id=%s comprovante_id=%s',
            contrato_id,
            comprovante_id,
        )
        return JsonResponse({'ok': False, 'erro': 'Erro ao excluir comprovante.'}, status=500)


@login_required
@require_POST
@controle_acess(COD_PAGAMENTO_TC)
def api_confirmar_pagamento_tc(request):
    """Confirma Pago TC (operacional_pago_tc) a partir de PG_PAGO_CLIENTE."""
    data = _json(request)
    try:
        contrato_id = int(data.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    if contrato_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        if ce.sub_status_operacional != SubStatusOperacional.PG_PAGO_CLIENTE:
            return JsonResponse(
                {'ok': False, 'erro': 'Confirmação disponível apenas para contratos em Pago Cliente.'},
                status=400,
            )

        rm_dict, err_rm = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
        if err_rm:
            return JsonResponse({'ok': False, 'erro': err_rm}, status=400)

        observacao = (data.get('observacao') or '').strip() or 'Pago TC confirmado (financeiro)'

        if rm_dict is not None:
            novo_tc_ev = rm_dict.get('valor_est')
            if novo_tc_ev is not None and novo_tc_ev > 0:
                from apps.contratos_v2.fluxo_transicoes import (
                    _soma_comprovantes_tc_ativos,
                    valor_tc_efetivo_para_fluxo,
                )

                soma_ev = _soma_comprovantes_tc_ativos(ce)
                atual_ev = valor_tc_efetivo_para_fluxo(ce)
                if atual_ev.quantize(Decimal('0.01')) != novo_tc_ev.quantize(Decimal('0.01')):
                    ok_pe, err_pe = persistir_tc_modal_em_contrato_e_rm(ce, novo_tc_ev, soma_ev)
                    if not ok_pe:
                        return JsonResponse({'ok': False, 'erro': err_pe}, status=400)
                    ce.refresh_from_db()
                    if ContratoDadosOperacionais.objects.filter(contrato_execucao_id=ce.pk).exists():
                        ce.dados_operacionais.refresh_from_db()
                    if ce.proposta_dados_id:
                        ce.proposta_dados.refresh_from_db()
            elif novo_tc_ev is not None and novo_tc_ev <= 0 and _valor_tc_do_contrato(ce) > 0:
                ok_z, err_z = zerar_tc_modal_em_contrato(ce)
                if not ok_z:
                    return JsonResponse({'ok': False, 'erro': err_z}, status=400)
                ce.refresh_from_db()

        extras = {'registermoney': rm_dict} if rm_dict else None
        ok, msg = transicao_por_acao(
            ce,
            request.user,
            PAPEL_OPERACIONAL,
            'operacional_pago_tc',
            observacao=observacao,
            extras=extras,
        )
        if not ok:
            return JsonResponse({'ok': False, 'erro': msg}, status=400)

        ce.refresh_from_db()
        return JsonResponse({
            'ok': True,
            'sub_status': str(ce.sub_status_operacional or ''),
            'valor_tc': str(_valor_tc_do_contrato(ce)),
            'soma_acumulada': str(_soma_comprovantes(ce)),
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    except Exception:
        logger.exception('api_confirmar_pagamento_tc contrato_id=%s', contrato_id)
        return JsonResponse({'ok': False, 'erro': 'Erro ao confirmar Pago TC.'}, status=500)
