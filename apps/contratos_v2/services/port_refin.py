# -*- coding: utf-8 -*-
"""Geração do par REFIN após Pago Cliente em contrato PORT (flag_port_mais_refin)."""
import re
from decimal import Decimal

from django.db import transaction

from apps.contratos_v2.fluxo_constants import (
    EtapaOperacional,
    EstadoSolicitacaoDigitacao,
    SubStatusOperacional,
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


def titulo_produto_indica_refin(titulo):
    """True se o título do produto indicar refinanciamento (REFIN no nome)."""
    return 'REFIN' in (titulo or '').upper()


def produto_indica_portabilidade(prod):
    """
    True para ficha/PDF: produto PORT ou REFIN no título, tag Port+Refin ou Refin da Port.
    """
    if not prod:
        return False
    titulo = getattr(prod, 'titulo', None) or ''
    if titulo_produto_indica_port(titulo) or titulo_produto_indica_refin(titulo):
        return True
    if getattr(prod, 'flag_port_mais_refin', False):
        return True
    if getattr(prod, 'flag_refin_da_port', False):
        return True
    return False


def contrato_indica_portabilidade(ce):
    """Portabilidade efetiva na ficha/PDF: flag manual do contrato ou produto PORT/REFIN."""
    if getattr(ce, 'portabilidade', False):
        return True
    return any(produto_indica_portabilidade(p) for p in _iter_produtos_contrato(ce))


def exibe_valor_saldo_ficha_produto(prod):
    """
    (exibir, rótulo) do valor saldo na ficha/PDF.
    PORT no título ou produto Refin da Port (tag flag_refin_da_port).
    """
    if not prod:
        return False, 'Valor Saldo'
    if getattr(prod, 'flag_refin_da_port', False):
        return True, 'Valor de saldo port'
    if titulo_produto_indica_port(getattr(prod, 'titulo', None) or ''):
        return True, 'Valor Saldo'
    return False, 'Valor Saldo'


def resolver_valor_saldo_exibicao_ce(ce, valor_saldo_local=None):
    """
    Valor saldo para exibição: snapshot do contrato ou, no REFIN vinculado, do PORT pai.
    """
    if valor_saldo_local is not None:
        return str(valor_saldo_local)
    port_id = getattr(ce, 'contrato_vinculo_port_id', None)
    if not port_id:
        return ''
    try:
        port_ce = ContratoExecucao.objects.select_related(
            'dados_operacionais', 'proposta_dados'
        ).get(pk=port_id)
    except ContratoExecucao.DoesNotExist:
        return ''
    try:
        vs = port_ce.dados_operacionais.valor_saldo
        if vs is not None:
            return str(vs)
    except Exception:
        pass
    try:
        vs = port_ce.proposta_dados.valor_saldo
        if vs is not None:
            return str(vs)
    except Exception:
        pass
    return ''


def _produto_do_contrato(ce):
    """Primeiro produto encontrado (operacional, depois proposta)."""
    for prod in _iter_produtos_contrato(ce):
        return prod
    return None


def _iter_produtos_contrato(ce):
    """Produtos do snapshot operacional e da proposta (sem duplicar por id)."""
    produtos = []
    vistos = set()
    for attr in ('dados_operacionais', 'proposta_dados'):
        try:
            container = getattr(ce, attr, None)
            if not container:
                continue
            prod = getattr(container, 'produto', None)
            if not prod:
                continue
            pid = getattr(prod, 'pk', None) or getattr(prod, 'id', None)
            if pid is not None:
                if pid in vistos:
                    continue
                vistos.add(pid)
            produtos.append(prod)
        except Exception:
            continue
    return produtos


def _diagnostico_produtos_port_refin(ce):
    """Ids e flags dos produtos (suporte / API transicoes-disponiveis)."""
    prod_op = None
    prod_prop = None
    try:
        prod_op = ce.dados_operacionais.produto
    except Exception:
        pass
    try:
        if ce.proposta_dados_id:
            prod_prop = ce.proposta_dados.produto
    except Exception:
        pass
    return {
        'produto_op_id': getattr(prod_op, 'pk', None) or getattr(prod_op, 'id', None),
        'produto_prop_id': getattr(prod_prop, 'pk', None) or getattr(prod_prop, 'id', None),
        'flag_port_mais_refin_op': bool(
            prod_op and getattr(prod_op, 'flag_port_mais_refin', False)
        ),
        'flag_port_mais_refin_prop': bool(
            prod_prop and getattr(prod_prop, 'flag_port_mais_refin', False)
        ),
    }


def contrato_exige_valor_saldo_pago_cliente(ce):
    """Pago Cliente exige Valor Saldo: produto com PORT no título, exceto Refin da Port."""
    for prod in _iter_produtos_contrato(ce):
        if getattr(prod, 'flag_refin_da_port', False):
            continue
        if titulo_produto_indica_port(prod.titulo):
            return True
    return False


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
    """True se qualquer produto do contrato tiver flag Port + Refin."""
    return any(
        getattr(prod, 'flag_port_mais_refin', False) for prod in _iter_produtos_contrato(ce)
    )


def contrato_port_ja_tem_refin(ce_port):
    return ContratoExecucao.objects.filter(
        contrato_vinculo_port_id=ce_port.pk,
        status=True,
    ).exists()


def ce_exige_fluxo_port_refin_pago_cliente(ce):
    """Port + Refin pendente ao tabular como Pago Cliente (qualquer etapa de origem)."""
    return produto_exige_refin_no_pago_cliente(ce) and not contrato_port_ja_tem_refin(ce)


def _resolver_solicitante_user_par_port(pd_port, sol_port, fallback_user):
    """Mantém o mesmo solicitante (vendedor) do par PORT na proposta/solicitação REFIN."""
    if pd_port and getattr(pd_port, 'criado_por_id', None):
        return pd_port.criado_por
    if sol_port and getattr(sol_port, 'criado_por_id', None):
        return sol_port.criado_por
    return fallback_user


def processar_pago_cliente_port_refin_se_necessario(ce, user, observacao='', extras=None):
    """
    Se o contrato exige REFIN: valida payload, tabula PORT como Pago Cliente e cria o filho.
    Retorna True se tratou; False para seguir fluxo normal de Pago Cliente.
    Levanta ValueError em validação.
    """
    if not ce_exige_fluxo_port_refin_pago_cliente(ce):
        return False
    extras = extras or {}
    refin_port = extras.get('refin_port')
    if not refin_port:
        raise ValueError('Informe os dados do contrato REFIN (Port + Refin).')
    valor_saldo = validar_valor_saldo_obrigatorio(extras, ce)
    criar_refin_apos_pago_cliente(
        ce,
        refin_port,
        user,
        observacao=observacao,
        valor_saldo=valor_saldo,
    )
    return True


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
            **_diagnostico_produtos_port_refin(ce_port),
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
    diag = _diagnostico_produtos_port_refin(ce_port)
    return {
        'port_mais_refin': True,
        'refin_ja_existe': refin_existe,
        **diag,
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
    Confirma Pago Cliente no PORT e cria proposta + contrato REFIN em Digitação/Digitado.
    Retorna dict com ids/códigos ou levanta ValueError.
    """
    if not ce_port.status:
        raise ValueError('Contrato PORT inativo.')
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
    solicitante_user = _resolver_solicitante_user_par_port(pd_port, sol_port, user)

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
        criado_por=solicitante_user,
    )
    adicionar_proposta_operacional_na_carteira(carteira, pd_refin)

    sol_refin = SolicitacaoDigitacao.objects.create(
        proposta_dados=pd_refin,
        carteira_clientes=carteira,
        observacoes=f'REFIN gerado automaticamente a partir do contrato PORT {ce_port.codigo or ce_port.id}.',
        estado=EstadoSolicitacaoDigitacao.CONTRATO_GERADO,
        criado_por=solicitante_user,
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
        etapa_operacional=EtapaOperacional.DIGITACAO,
        sub_status_operacional=SubStatusOperacional.DIG_DIGITADO,
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
        etapa_nova=EtapaOperacional.DIGITACAO,
        sub_nova=SubStatusOperacional.DIG_DIGITADO,
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
