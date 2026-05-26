# -*- coding: utf-8 -*-
"""Geração do par REFIN após Pago Cliente em contrato PORT (flag_port_mais_refin)."""
import re
from decimal import Decimal

from django.db import transaction

from apps.contratos_v2.fluxo_constants import (
    EtapaOperacional,
    EstadoSolicitacaoDigitacao,
    FaseContratoExecucao,
    SubStatusOperacional,
    TagFinanceiraContrato,
)
from apps.contratos_v2.fluxo_transicoes import aplicar_etapa_sub, sincronizar_fase_legada
from apps.contratos_v2.models import (
    ContratoDadosOperacionais,
    ContratoExecucao,
    ContratoPortado,
    HistoricoEventoDigitacao,
    HistoricoTransicaoContrato,
    PropostaDados,
    Produto,
    SolicitacaoDigitacao,
    TabelaCms,
)
from apps.contratos_v2.services.repasse_carteira import kwargs_snapshot_repasse_contrato
from apps.vendas.siape.services.carteira_operacional import adicionar_proposta_operacional_na_carteira

_REGEX_NUMERO_CONTRATO = re.compile(r'^[A-Z0-9\-\.\/]{1,30}$')


def titulo_produto_indica_port(titulo):
    """True se o título do produto indicar portabilidade (PORT no nome)."""
    return 'PORT' in (titulo or '').upper()


def _produto_do_contrato(ce):
    try:
        d = ce.dados_operacionais
        if d and getattr(d, 'produto', None):
            return d.produto
    except Exception:
        pass
    try:
        pd = ce.proposta_dados
        if pd and getattr(pd, 'produto', None):
            return pd.produto
    except Exception:
        pass
    return None


def contrato_exige_valor_saldo_pago_cliente(ce):
    """Pago Cliente exige Valor Saldo: produto com PORT no título, exceto Refin da Port."""
    prod = _produto_do_contrato(ce)
    if not prod:
        return False
    if getattr(prod, 'flag_refin_da_port', False):
        return False
    return titulo_produto_indica_port(prod.titulo)


def extrair_valor_saldo_de_extras(extras):
    """Lê valor_saldo do payload (nível raiz ou dentro de refin_port)."""
    if not isinstance(extras, dict):
        return None
    raw = extras.get('valor_saldo')
    if raw is None:
        rp = extras.get('refin_port')
        if isinstance(rp, dict):
            raw = rp.get('valor_saldo')
    return _dec_payload(raw)


def validar_valor_saldo_obrigatorio(extras, ce):
    """Retorna Decimal ou levanta ValueError se PORT exige saldo."""
    if not contrato_exige_valor_saldo_pago_cliente(ce):
        return None
    dec = extrair_valor_saldo_de_extras(extras)
    if dec is None:
        raise ValueError('Informe o Valor Saldo.')
    if dec < 0:
        raise ValueError('Valor Saldo não pode ser negativo.')
    return dec


def persistir_valor_saldo_contrato(ce, valor_saldo):
    """Grava valor_saldo na proposta e no snapshot operacional do contrato."""
    if valor_saldo is None or not ce.proposta_dados_id:
        return
    PropostaDados.objects.filter(pk=ce.proposta_dados_id).update(valor_saldo=valor_saldo)
    ContratoDadosOperacionais.objects.filter(contrato_execucao_id=ce.pk).update(
        valor_saldo=valor_saldo
    )


def produto_exige_refin_no_pago_cliente(ce):
    """True se o contrato PORT deve abrir modal REFIN ao confirmar Pago Cliente."""
    try:
        prod = ce.dados_operacionais.produto
    except Exception:
        prod = None
    if not prod and ce.proposta_dados_id:
        prod = ce.proposta_dados.produto
    return bool(prod and getattr(prod, 'flag_port_mais_refin', False))


def contrato_port_ja_tem_refin(ce_port):
    return ContratoExecucao.objects.filter(
        contrato_vinculo_port_id=ce_port.pk,
        status=True,
    ).exists()


def resolver_produto_refin_da_port():
    """Retorna Produto ativo único com flag_refin_da_port ou levanta ValueError."""
    qs = Produto.objects.filter(status=True, flag_refin_da_port=True).order_by('id')
    n = qs.count()
    if n == 0:
        raise ValueError(
            'Nenhum produto ativo com flag "Refin da Port". Cadastre em Catálogos → Produtos.'
        )
    if n > 1:
        titulos = ', '.join(qs.values_list('titulo', flat=True)[:5])
        raise ValueError(
            f'Mais de um produto "Refin da Port" ativo ({titulos}). Deixe apenas um.'
        )
    return qs.first()


def _dec_payload(v):
    if v is None or v == '':
        return None
    if isinstance(v, Decimal):
        return v
    s = str(v).strip()
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(',', '.')
    try:
        return Decimal(s)
    except Exception:
        return None


def _int_payload(v):
    if v is None or v == '':
        return None
    try:
        n = int(v)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def _kwargs_snapshot_tabela_cms(tab):
    if not tab:
        return {}
    tit = getattr(tab, 'titulo', None) or ''
    return {
        'tabela_cms_titulo_snapshot': tit[:200],
        'taxa_recebido_snapshot': tab.taxa_recebido,
        'taxa_repasse_snapshot': tab.taxa_repasse,
        'taxa_plastico_snapshot': tab.taxa_plastico,
    }


def _validar_refin_port_payload(ce_port, refin_port):
    if not isinstance(refin_port, dict):
        raise ValueError('Informe os dados do REFIN (modal Port + Refin).')
    numero = (refin_port.get('numero_contrato') or '').strip().upper()
    if not numero:
        raise ValueError('Informe o número do contrato REFIN.')
    if not _REGEX_NUMERO_CONTRATO.match(numero):
        raise ValueError(
            'Nº contrato REFIN inválido. Use apenas letras, números e -./ (até 30 caracteres).'
        )
    if ContratoExecucao.objects.filter(codigo=numero).exists():
        raise ValueError(f'Já existe contrato com o número {numero}.')
    try:
        tid = int(refin_port.get('tabela_cms_id'))
    except (TypeError, ValueError):
        raise ValueError('Selecione a tabela CMS do REFIN.')
    prod_refin = resolver_produto_refin_da_port()
    try:
        d_op = ce_port.dados_operacionais
        banco_id = d_op.banco_id
        convenio_id = d_op.convenio_id
    except Exception:
        pd = ce_port.proposta_dados
        banco_id = pd.banco_id
        convenio_id = pd.convenio_id
    try:
        tab = TabelaCms.objects.select_related('banco', 'convenio', 'produto').get(
            pk=tid,
            status=True,
            banco_id=banco_id,
            convenio_id=convenio_id,
            produto_id=prod_refin.id,
        )
    except TabelaCms.DoesNotExist:
        raise ValueError('Tabela CMS inválida para banco/convênio/produto REFIN.')
    prop = refin_port.get('proposta') if isinstance(refin_port.get('proposta'), dict) else {}
    return numero, tab, prod_refin, prop


def _clonar_contratos_portados(proposta_port, proposta_refin, ce_refin):
    for cp in ContratoPortado.objects.filter(proposta_dados=proposta_port):
        ContratoPortado.objects.create(
            proposta_dados=proposta_refin,
            contrato_execucao=ce_refin,
            banco_id=cp.banco_id,
            numero_contrato=cp.numero_contrato,
            valor_parcela=cp.valor_parcela,
            valor_af=cp.valor_af,
            valor_devedor_total=cp.valor_devedor_total,
            prazo_total=cp.prazo_total,
            prazo_restante=cp.prazo_restante,
        )


def montar_defaults_refin_port(ce_port):
    """Defaults para modal REFIN (transições / endpoint dedicado)."""
    if not produto_exige_refin_no_pago_cliente(ce_port):
        return None
    refin_existe = contrato_port_ja_tem_refin(ce_port)
    try:
        prod_refin = resolver_produto_refin_da_port()
    except ValueError as exc:
        return {
            'port_mais_refin': True,
            'refin_ja_existe': refin_existe,
            'erro_config': str(exc),
        }
    try:
        d = ce_port.dados_operacionais
        banco_id = d.banco_id
        convenio_id = d.convenio_id
        banco_titulo = d.banco.titulo if d.banco_id else ''
        convenio_titulo = d.convenio.titulo if d.convenio_id else ''
        valor_parcela = d.valor_parcela
        prazo = d.prazo
        valor_af = d.valor_af
        valor_tc = d.valor_tc
        valor_liberado = d.valor_liberado
        valor_saldo = d.valor_saldo
    except Exception:
        pd = ce_port.proposta_dados
        banco_id = pd.banco_id
        convenio_id = pd.convenio_id
        banco_titulo = pd.banco.titulo if pd.banco_id else ''
        convenio_titulo = pd.convenio.titulo if pd.convenio_id else ''
        valor_parcela = pd.valor_parcela
        prazo = pd.prazo
        valor_af = pd.valor_af
        valor_tc = pd.valor_tc
        valor_liberado = pd.valor_liberado
        valor_saldo = pd.valor_saldo
    tabelas = list(
        TabelaCms.objects.filter(
            banco_id=banco_id,
            convenio_id=convenio_id,
            produto_id=prod_refin.id,
            status=True,
        ).values('id', 'titulo', 'classificador_banco').order_by('titulo')
    )
    portados = []
    if ce_port.proposta_dados_id:
        for cp in ContratoPortado.objects.filter(
            proposta_dados_id=ce_port.proposta_dados_id
        ).select_related('banco'):
            portados.append({
                'banco': cp.banco.titulo if cp.banco_id else '—',
                'numero_contrato': (cp.numero_contrato or '').strip(),
                'valor_parcela': str(cp.valor_parcela) if cp.valor_parcela is not None else '',
                'valor_af': str(cp.valor_af) if cp.valor_af is not None else '',
            })
    return {
        'port_mais_refin': True,
        'refin_ja_existe': refin_existe,
        'produto_refin_id': prod_refin.id,
        'produto_refin_titulo': prod_refin.titulo,
        'banco_id': banco_id,
        'convenio_id': convenio_id,
        'banco_titulo': banco_titulo,
        'convenio_titulo': convenio_titulo,
        'tabelas_cms': tabelas,
        'proposta_defaults': {
            'valor_parcela': str(valor_parcela) if valor_parcela is not None else '',
            'prazo': prazo,
            'valor_af': str(valor_af) if valor_af is not None else '',
            'valor_tc': str(valor_tc) if valor_tc is not None else '',
            'valor_liberado': str(valor_liberado) if valor_liberado is not None else '',
            'valor_saldo': str(valor_saldo) if valor_saldo is not None else '',
        },
        'exige_valor_saldo_port': contrato_exige_valor_saldo_pago_cliente(ce_port),
        'contratos_portados': portados,
    }


def vinculo_port_refin_dict(ce):
    """Resumo do vínculo PORT/REFIN para ficha e cards."""
    out = {'papel': None, 'contrato_id': None, 'contrato_codigo': None, 'proposta_codigo': None}
    if ce.contrato_vinculo_port_id:
        port = ce.contrato_vinculo_port
        out['papel'] = 'REFIN'
        out['contrato_id'] = port.id
        out['contrato_codigo'] = port.codigo or ''
        if port.proposta_dados_id:
            out['proposta_codigo'] = port.proposta_dados.codigo or ''
        return out
    filho = (
        ContratoExecucao.objects.filter(contrato_vinculo_port_id=ce.pk, status=True)
        .select_related('proposta_dados')
        .order_by('id')
        .first()
    )
    if filho:
        out['papel'] = 'PORT'
        out['contrato_id'] = filho.id
        out['contrato_codigo'] = filho.codigo or ''
        if filho.proposta_dados_id:
            out['proposta_codigo'] = filho.proposta_dados.codigo or ''
    return out


@transaction.atomic
def criar_refin_apos_pago_cliente(ce_port, refin_port, user, observacao='', valor_saldo=None):
    """
    Confirma Pago Cliente no PORT e cria proposta + contrato REFIN em PG_PAGO_CLIENTE.
    Retorna dict com ids/códigos ou levanta ValueError.
    """
    if not ce_port.status:
        raise ValueError('Contrato PORT inativo.')
    if ce_port.etapa_operacional != EtapaOperacional.PAGAMENTO:
        raise ValueError('Contrato não está em Pagamento.')
    if ce_port.sub_status_operacional != SubStatusOperacional.PG_AGUARDANDO_CLIENTE:
        raise ValueError('Exige sub-status Aguardando Pagamento Cliente.')
    if not produto_exige_refin_no_pago_cliente(ce_port):
        raise ValueError('Produto não exige geração de REFIN.')
    if contrato_port_ja_tem_refin(ce_port):
        raise ValueError('Contrato REFIN já foi gerado para este PORT.')

    numero, tab, prod_refin, prop = _validar_refin_port_payload(ce_port, refin_port)

    if valor_saldo is None:
        extras_saldo = {}
        if isinstance(refin_port, dict) and refin_port.get('valor_saldo') is not None:
            extras_saldo['valor_saldo'] = refin_port.get('valor_saldo')
        valor_saldo = validar_valor_saldo_obrigatorio(extras_saldo, ce_port)

    sol_port = ce_port.solicitacao_digitacao
    if not sol_port or not sol_port.carteira_clientes_id:
        raise ValueError('Contrato PORT sem carteira vinculada.')
    carteira = sol_port.carteira_clientes
    pd_port = ce_port.proposta_dados

    ok, msg = aplicar_etapa_sub(
        ce_port,
        EtapaOperacional.PAGAMENTO,
        SubStatusOperacional.PG_PAGO_CLIENTE,
        user,
        observacao or 'Pago Cliente',
        inner_atomic=False,
    )
    if not ok:
        raise ValueError(msg or 'Falha ao registrar Pago Cliente no PORT.')

    if valor_saldo is not None:
        persistir_valor_saldo_contrato(ce_port, valor_saldo)

    pd_refin = PropostaDados.objects.create(
        cliente_dados_pessoais_id=ce_port.cliente_dados_pessoais_id,
        banco_id=tab.banco_id,
        convenio_id=tab.convenio_id,
        produto_id=prod_refin.id,
        tabela_cms_id=tab.id,
        valor_parcela=_dec_payload(prop.get('valor_parcela')),
        prazo=_int_payload(prop.get('prazo')),
        coeficiente=_dec_payload(prop.get('coeficiente')),
        valor_af=_dec_payload(prop.get('valor_af')),
        valor_tc=_dec_payload(prop.get('valor_tc')),
        valor_liberado=_dec_payload(prop.get('valor_liberado')),
        valor_saldo=valor_saldo,
        proposta_vinculo_port_id=pd_port.id,
        criado_por=user,
    )
    adicionar_proposta_operacional_na_carteira(carteira, pd_refin)

    sol_refin = SolicitacaoDigitacao.objects.create(
        proposta_dados=pd_refin,
        carteira_clientes=carteira,
        observacoes=f'REFIN gerado automaticamente a partir do contrato PORT {ce_port.codigo or ce_port.id}.',
        estado=EstadoSolicitacaoDigitacao.CONTRATO_GERADO,
        criado_por=user,
    )
    HistoricoEventoDigitacao.objects.create(
        solicitacao=sol_refin,
        estado_anterior='',
        estado_novo=EstadoSolicitacaoDigitacao.CONTRATO_GERADO,
        usuario=user,
    )

    snap_kw = kwargs_snapshot_repasse_contrato(carteira)
    if not snap_kw and getattr(ce_port, 'user_repasse_snapshot_id', None):
        snap_kw = {
            'carteira_clientes_snapshot_id': ce_port.carteira_clientes_snapshot_id,
            'user_repasse_snapshot_id': ce_port.user_repasse_snapshot_id,
        }
    ce_refin = ContratoExecucao.objects.create(
        codigo=numero,
        proposta_dados=pd_refin,
        cliente_dados_pessoais_id=ce_port.cliente_dados_pessoais_id,
        solicitacao_digitacao=sol_refin,
        contrato_vinculo_port_id=ce_port.id,
        etapa_operacional=EtapaOperacional.PAGAMENTO,
        sub_status_operacional=SubStatusOperacional.PG_PAGO_CLIENTE,
        fase=FaseContratoExecucao.CLIENTE_PAGO,
        tag_financeira=TagFinanceiraContrato.PAGO_CLIENTE,
        flag_video_enviado=bool(ce_port.flag_video_enviado),
        **snap_kw,
    )
    ContratoDadosOperacionais.objects.create(
        contrato_execucao=ce_refin,
        banco=tab.banco,
        convenio=tab.convenio,
        produto=tab.produto,
        tabela_cms=tab,
        valor_parcela=pd_refin.valor_parcela,
        prazo=pd_refin.prazo,
        valor_af=pd_refin.valor_af,
        valor_tc=pd_refin.valor_tc,
        valor_liberado=pd_refin.valor_liberado,
        valor_saldo=valor_saldo,
        **_kwargs_snapshot_tabela_cms(tab),
    )
    sincronizar_fase_legada(ce_refin)

    HistoricoTransicaoContrato.objects.create(
        contrato_execucao=ce_refin,
        etapa_anterior=EtapaOperacional.DIGITACAO,
        sub_anterior=SubStatusOperacional.DIG_AGUARDANDO,
        etapa_nova=EtapaOperacional.PAGAMENTO,
        sub_nova=SubStatusOperacional.PG_PAGO_CLIENTE,
        usuario=user,
        observacao=f'REFIN criado vinculado ao PORT {ce_port.codigo or ce_port.id}.',
    )

    _clonar_contratos_portados(pd_port, pd_refin, ce_refin)

    return {
        'contrato_port_id': ce_port.id,
        'contrato_refin_id': ce_refin.id,
        'contrato_refin_codigo': ce_refin.codigo,
        'proposta_refin_codigo': pd_refin.codigo,
        'solicitacao_refin_id': sol_refin.id,
    }
