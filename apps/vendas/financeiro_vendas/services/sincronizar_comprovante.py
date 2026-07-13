"""
Sincroniza ComprovanteTC de contratos_v2 para financeiro_vendas (ranking).
"""
from decimal import Decimal
import os

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction

from apps.vendas.financeiro_vendas.models import Classificador, ComprovanteTC, ContratoPagamento
from apps.vendas.siape.models import Produto as SiapeProduto


def _parse_dec(val):
    if val in (None, ''):
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def resolver_classificador_financeiro_por_cv_id(cv_id):
    """Mapeia ClassificacaoValor (siape) → Classificador (financeiro) pelo percentual."""
    from apps.vendas.siape.models import ClassificacaoValor

    if cv_id not in (None, ''):
        try:
            cv = ClassificacaoValor.objects.get(pk=int(cv_id))
            cl = Classificador.objects.filter(status=True, percentual=cv.percentual).order_by('titulo').first()
            if cl:
                return cl
            cl = Classificador.objects.filter(percentual=cv.percentual).order_by('titulo').first()
            if cl:
                return cl
        except (ClassificacaoValor.DoesNotExist, ValueError, TypeError):
            pass
    return Classificador.objects.filter(status=True).order_by('titulo').first()


def resolver_classificacao_valor_por_classificador_id(classificador_id):
    """
    Mapeia Classificador (financeiro_vendas) → ClassificacaoValor (siape) pelo percentual.
    Cria ClassificacaoValor espelhada quando não existir registro equivalente.
    """
    from apps.vendas.siape.models import ClassificacaoValor

    if classificador_id in (None, ''):
        return None
    try:
        cl = Classificador.objects.get(pk=int(classificador_id), status=True)
    except (Classificador.DoesNotExist, ValueError, TypeError):
        try:
            cl = Classificador.objects.get(pk=int(classificador_id))
        except (Classificador.DoesNotExist, ValueError, TypeError):
            return None

    cv = (
        ClassificacaoValor.objects.filter(status=True, percentual=cl.percentual).order_by('titulo').first()
        or ClassificacaoValor.objects.filter(percentual=cl.percentual).order_by('titulo').first()
    )
    if not cv:
        cv = ClassificacaoValor.objects.create(
            titulo=(cl.titulo or 'CLASSIFICADOR')[:120],
            percentual=cl.percentual,
            status=True,
        )
    return cv


def resolver_classificador_financeiro_de_rm_payload(rm_payload):
    """Resolve Classificador financeiro a partir do payload do modal Pago TC."""
    if not rm_payload:
        return Classificador.objects.filter(status=True).order_by('titulo').first()

    cl_raw = rm_payload.get('classificador_id')
    if cl_raw not in (None, ''):
        try:
            return Classificador.objects.get(pk=int(cl_raw), status=True)
        except (Classificador.DoesNotExist, ValueError, TypeError):
            try:
                return Classificador.objects.get(pk=int(cl_raw))
            except (Classificador.DoesNotExist, ValueError, TypeError):
                return None

    return resolver_classificador_financeiro_por_cv_id(rm_payload.get('classificacao_valor_id'))


def resolver_classificacao_valor_de_rm_payload(rm_payload):
    """Resolve ClassificacaoValor (RegisterMoney) a partir do payload do modal Pago TC."""
    if not rm_payload:
        return None

    cl_raw = rm_payload.get('classificador_id')
    if cl_raw not in (None, ''):
        return resolver_classificacao_valor_por_classificador_id(cl_raw)

    cv_raw = rm_payload.get('classificacao_valor_id')
    if cv_raw in (None, ''):
        return None
    from apps.vendas.siape.models import ClassificacaoValor

    try:
        return ClassificacaoValor.objects.get(pk=int(cv_raw), status=True)
    except (ClassificacaoValor.DoesNotExist, ValueError, TypeError):
        try:
            return ClassificacaoValor.objects.get(pk=int(cv_raw))
        except (ClassificacaoValor.DoesNotExist, ValueError, TypeError):
            return None


def _setor_por_user(user):
    if not user:
        return None
    if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
        dp = getattr(user.funcionario_profile, 'dados_profissionais', None)
        if dp and dp.setor_id:
            return dp.setor
    return None


def _siape_produto_id_por_contratos_produto(produto_contratos):
    from apps.contratos_v2.fluxo_transicoes import _siape_produto_id_por_contratos_produto as _map

    pid = _map(produto_contratos)
    if pid:
        return SiapeProduto.objects.filter(pk=pid).first()
    return None


def _valor_tc_de_rm_payload(rm_payload, ce):
    from apps.contratos_v2.apis.acoes_crm import _valor_tc_do_contrato

    if rm_payload:
        v = _parse_dec(rm_payload.get('valor_est') or rm_payload.get('valor_est_tc'))
        if v is not None and v > 0:
            return v
    return _valor_tc_do_contrato(ce)


def _copiar_arquivo_comprovante(comp_v2, nome_destino):
    if not comp_v2.arquivo:
        return None
    comp_v2.arquivo.open('rb')
    try:
        conteudo = comp_v2.arquivo.read()
    finally:
        comp_v2.arquivo.close()
    base = os.path.basename(comp_v2.arquivo.name)
    return ContentFile(conteudo, name=nome_destino or base)


def _dados_base_contrato_pagamento(ce, rm_payload=None):
    from apps.contratos_v2.services.repasse_carteira import resolver_contexto_repasse_contrato

    cpf = ''
    if ce.cliente_dados_pessoais_id:
        cpf = (ce.cliente_dados_pessoais.cpf or '').strip()
    nome = ''
    if ce.cliente_dados_pessoais_id:
        nome = (ce.cliente_dados_pessoais.nome or '').strip()

    d = None
    try:
        d = ce.dados_operacionais
    except Exception:
        d = None

    produto = None
    banco = ''
    valor_af = Decimal('0')
    if d:
        produto = _siape_produto_id_por_contratos_produto(d.produto)
        banco_obj = getattr(d, 'banco', None)
        if banco_obj is not None and hasattr(banco_obj, 'titulo'):
            banco = (banco_obj.titulo or '').strip()
        else:
            banco = (getattr(d, 'banco', '') or '').strip()
            if hasattr(banco, 'titulo'):
                banco = (banco.titulo or '').strip()
        if d.valor_af is not None:
            valor_af = Decimal(str(d.valor_af))

    if rm_payload and rm_payload.get('af') not in (None, ''):
        af_rm = _parse_dec(rm_payload.get('af'))
        if af_rm is not None:
            valor_af = af_rm

    valor_tc = _valor_tc_de_rm_payload(rm_payload, ce)
    classificador = resolver_classificador_financeiro_de_rm_payload(rm_payload)
    if not classificador:
        raise ValueError('Nenhum classificador financeiro disponível para sync do ranking.')

    if not produto:
        produto = SiapeProduto.objects.filter(status=True).order_by('nome').first()
    if not produto:
        raise ValueError('Produto SIAPE não encontrado para sync do ranking.')

    from django.utils import timezone as tz

    ctx_rep = resolver_contexto_repasse_contrato(ce)
    data_contrato = None
    if getattr(ce, 'data_criacao', None):
        data_contrato = ce.data_criacao.date()
    if not data_contrato and d and getattr(d, 'data_contrato', None):
        data_contrato = d.data_contrato
    if not data_contrato:
        data_contrato = tz.now().date()

    return {
        'cliente_cpf': cpf,
        'cliente_nome': nome or 'CLIENTE',
        'produto': produto,
        'banco': banco or 'N/I',
        'valor_af': valor_af,
        'valor_repasse': valor_tc,
        'valor_tc': valor_tc,
        'classificador': classificador,
        'data_contrato': data_contrato,
        'ctx_rep': ctx_rep,
    }


def _get_or_create_contrato_pagamento(ce, user, flag_repasse, dados_base):
    from apps.rh.admin.models import Setor

    setor = _setor_por_user(user)
    if not setor:
        setor = Setor.objects.filter(status=True).order_by('nome').first()
    if not setor:
        raise ValueError('Setor não encontrado para sync do ranking.')

    defaults = {
        'setor': setor,
        'cliente_cpf': dados_base['cliente_cpf'],
        'cliente_nome': dados_base['cliente_nome'],
        'produto': dados_base['produto'],
        'banco': dados_base['banco'],
        'valor_af': dados_base['valor_af'],
        'valor_repasse': dados_base['valor_repasse'],
        'valor_tc': dados_base['valor_tc'],
        'classificador': dados_base['classificador'],
        'data_contrato': dados_base['data_contrato'],
        'flag_repasse': flag_repasse,
        'status': 'A_PAGAR',
        'status_ativo': True,
    }

    cp, created = ContratoPagamento.objects.get_or_create(
        contrato_execucao=ce,
        user=user,
        defaults=defaults,
    )
    if not created:
        update_fields = []
        for campo in ('valor_tc', 'valor_repasse', 'valor_af', 'banco', 'classificador'):
            novo = defaults.get(campo)
            if novo is not None and getattr(cp, campo) != novo:
                setattr(cp, campo, novo)
                update_fields.append(campo)
        if update_fields:
            cp.save(update_fields=update_fields + ['data_atualizacao'])
    return cp


def _destinatarios_sync(ce, dados_base):
    ctx = dados_base['ctx_rep']
    destinos = []
    if ctx.get('tem_repasse') and ctx.get('user_responsavel_id') and ctx.get('user_repasse_id'):
        ur = User.objects.filter(pk=ctx['user_responsavel_id']).first()
        ux = User.objects.filter(pk=ctx['user_repasse_id']).first()
        if ur:
            destinos.append((ur, True))
        if ux:
            destinos.append((ux, True))
    else:
        user = ctx.get('user_responsavel')
        if not user and ctx.get('user_responsavel_id'):
            user = User.objects.filter(pk=ctx['user_responsavel_id']).first()
        if not user and ce.solicitacao_digitacao_id:
            user = ce.solicitacao_digitacao.criado_por
        if user:
            destinos.append((user, False))
    return destinos


@transaction.atomic
def sincronizar_comprovante_v2_para_ranking(comp_v2, ce, rm_payload=None):
    """
    Espelha um ComprovanteTC de contratos_v2 nos registros de ranking (financeiro_vendas).
    Idempotente por (comprovante_v2_id, contrato_pagamento).
    """
    if ComprovanteTC.objects.filter(comprovante_v2_id=comp_v2.id).exists():
        return

    dados_base = _dados_base_contrato_pagamento(ce, rm_payload)
    destinos = _destinatarios_sync(ce, dados_base)
    if not destinos:
        raise ValueError('Nenhum destinatário para sync do ranking.')

    valor_total = Decimal(str(comp_v2.valor))
    tem_repasse = len(destinos) > 1
    arquivo_copia = _copiar_arquivo_comprovante(comp_v2, f'sync_v2_{comp_v2.id}_{os.path.basename(comp_v2.arquivo.name)}')

    for user, flag_repasse in destinos:
        cp = _get_or_create_contrato_pagamento(ce, user, flag_repasse, dados_base)
        if ComprovanteTC.objects.filter(comprovante_v2_id=comp_v2.id, contrato_pagamento=cp).exists():
            continue

        valor_linha = valor_total
        if tem_repasse:
            valor_linha = (valor_total / Decimal('2')).quantize(Decimal('0.01'))

        comp_fin = ComprovanteTC(
            contrato_pagamento=cp,
            valor=valor_linha,
            criado_por=comp_v2.criado_por,
            comprovante_v2_id=comp_v2.id,
        )
        if arquivo_copia:
            comp_fin.arquivo.save(arquivo_copia.name, arquivo_copia, save=False)
        comp_fin.save()
        cp.recalcular_tc_acumulado()


@transaction.atomic
def excluir_comprovante_v2_do_ranking(comp_v2_id):
    """Soft-delete dos comprovantes financeiros espelhados de um ComprovanteTC v2."""
    comps = list(
        ComprovanteTC.objects.filter(comprovante_v2_id=comp_v2_id, status=True)
        .select_related('contrato_pagamento')
    )
    if not comps:
        return

    cps_afetados = set()
    for comp in comps:
        comp.status = False
        comp.save(update_fields=['status'])
        cps_afetados.add(comp.contrato_pagamento_id)

    for cp_id in cps_afetados:
        cp = ContratoPagamento.objects.get(pk=cp_id)
        cp.recalcular_tc_acumulado()
