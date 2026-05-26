# -*- coding: utf-8 -*-
"""Registro de auditoria para mutações nos catálogos de contratos."""
from apps.contratos_v2.models import LogCatalogoContratos, TabelaCms


def _banco_dict(o):
    return {
        'id': o.id,
        'titulo': o.titulo,
        'codigo': o.codigo or '',
        'status': o.status,
        'data_criacao': o.data_criacao.isoformat() if o.data_criacao else None,
    }


def _convenio_dict(o):
    return {
        'id': o.id,
        'titulo': o.titulo,
        'status': o.status,
        'data_criacao': o.data_criacao.isoformat() if o.data_criacao else None,
    }


def _produto_dict(o):
    return {
        'id': o.id,
        'titulo': o.titulo,
        'status': o.status,
        'flag_port_mais_refin': bool(getattr(o, 'flag_port_mais_refin', False)),
        'flag_refin_da_port': bool(getattr(o, 'flag_refin_da_port', False)),
        'data_criacao': o.data_criacao.isoformat() if o.data_criacao else None,
    }


def _tabela_cms_dict(o):
    return {
        'id': o.id,
        'titulo': o.titulo,
        'banco_id': o.banco_id,
        'convenio_id': o.convenio_id,
        'produto_id': o.produto_id,
        'banco_titulo': o.banco.titulo if o.banco_id else '',
        'convenio_titulo': o.convenio.titulo if o.convenio_id else '',
        'produto_titulo': o.produto.titulo if o.produto_id else '',
        'classificador_banco': o.classificador_banco or 'M1',
        'taxa_recebido': str(o.taxa_recebido) if o.taxa_recebido is not None else None,
        'taxa_repasse': str(o.taxa_repasse) if o.taxa_repasse is not None else None,
        'taxa_plastico': str(o.taxa_plastico) if o.taxa_plastico is not None else None,
        'status': o.status,
        'data_criacao': o.data_criacao.isoformat() if o.data_criacao else None,
        'data_ultima_atualizacao': o.data_ultima_atualizacao.isoformat() if o.data_ultima_atualizacao else None,
    }

ENTIDADE_LABEL = {
    'banco': 'Banco',
    'convenio': 'Convênio',
    'produto': 'Produto',
    'tabela_cms': 'Tabela CMS',
}

CAMPOS_ROTULO = {
    'banco': {'titulo': 'título', 'codigo': 'código', 'status': 'status'},
    'convenio': {'titulo': 'título', 'status': 'status'},
    'produto': {
        'titulo': 'título',
        'status': 'status',
        'flag_port_mais_refin': 'Port + Refin',
        'flag_refin_da_port': 'Refin da Port',
    },
    'tabela_cms': {
        'titulo': 'título',
        'banco_id': 'banco',
        'convenio_id': 'convênio',
        'produto_id': 'produto',
        'banco_titulo': 'banco',
        'convenio_titulo': 'convênio',
        'produto_titulo': 'produto',
        'classificador_banco': 'classificador',
        'taxa_recebido': 'taxa recebido',
        'taxa_repasse': 'taxa repasse',
        'taxa_plastico': 'taxa plástico',
        'status': 'status',
    },
}


def snapshot(entidade, instance):
    """Serializa instância do catálogo para JSON de auditoria."""
    if instance is None:
        return None
    if entidade == 'banco':
        return _banco_dict(instance)
    if entidade == 'convenio':
        return _convenio_dict(instance)
    if entidade == 'produto':
        return _produto_dict(instance)
    if entidade == 'tabela_cms':
        if not hasattr(instance, 'banco_id') or instance.banco_id is None:
            instance = (
                TabelaCms.objects.select_related('banco', 'convenio', 'produto')
                .filter(pk=instance.pk)
                .first()
                or instance
            )
        return _tabela_cms_dict(instance)
    return None


def _fmt_valor(v):
    if v is None:
        return '—'
    if isinstance(v, bool):
        return 'ativo' if v else 'inativo'
    return str(v)


def diff_resumo(entidade, antes, depois, registro_id=None):
    """Monta resumo legível das diferenças entre dois snapshots."""
    label_ent = ENTIDADE_LABEL.get(entidade, entidade)
    prefix = f'{label_ent}'
    if registro_id:
        prefix += f' #{registro_id}'
    titulo = (depois or antes or {}).get('titulo') or ''
    if titulo:
        prefix += f' "{titulo}"'

    if not antes and depois:
        return f'{prefix}: criado.'
    if antes and not depois:
        return f'{prefix}: removido.'
    if not antes or not depois:
        return prefix

    rotulos = CAMPOS_ROTULO.get(entidade, {})
    partes = []
    chaves = set(antes.keys()) | set(depois.keys())
    for chave in sorted(chaves):
        va = antes.get(chave)
        vd = depois.get(chave)
        if va == vd:
            continue
        rot = rotulos.get(chave, chave)
        partes.append(f'{rot} "{_fmt_valor(va)}" → "{_fmt_valor(vd)}"')
    if not partes:
        return f'{prefix}: alterado.'
    return f'{prefix}: ' + '; '.join(partes)


def inferir_acao_edicao(entidade, antes, depois):
    """Se só status mudou, classifica como inativar ou reativar."""
    if not antes or not depois:
        return 'editar'
    rotulos = CAMPOS_ROTULO.get(entidade, {})
    alterados = []
    for chave in set(antes.keys()) | set(depois.keys()):
        if antes.get(chave) != depois.get(chave):
            alterados.append(chave)
    if alterados == ['status']:
        if depois.get('status') is False:
            return 'inativar'
        if depois.get('status') is True and antes.get('status') is False:
            return 'reativar'
    return 'editar'


def registrar_log(
    request,
    *,
    acao,
    entidade,
    registro_id=None,
    registro_titulo='',
    antes=None,
    depois=None,
    resumo='',
):
    """Persiste linha de auditoria."""
    if not resumo:
        resumo = diff_resumo(entidade, antes, depois, registro_id)
    titulo = registro_titulo or ''
    if not titulo:
        titulo = (depois or antes or {}).get('titulo') or ''
    usuario = getattr(request, 'user', None)
    if usuario and not getattr(usuario, 'is_authenticated', False):
        usuario = None
    return LogCatalogoContratos.objects.create(
        acao=acao,
        entidade=entidade,
        registro_id=registro_id,
        registro_titulo=(titulo or '')[:200],
        usuario=usuario if usuario and usuario.is_authenticated else None,
        dados_antes=antes,
        dados_depois=depois,
        resumo=resumo[:4000] if resumo else '',
    )


def log_dict_entrada(log):
    """Payload JSON para listagem na API."""
    u = log.usuario
    return {
        'id': log.id,
        'acao': log.acao,
        'acao_display': log.get_acao_display(),
        'entidade': log.entidade,
        'entidade_display': log.get_entidade_display(),
        'registro_id': log.registro_id,
        'registro_titulo': log.registro_titulo,
        'usuario_id': u.id if u else None,
        'usuario_nome': u.get_full_name() or u.username if u else 'Sistema',
        'usuario_username': u.username if u else '',
        'data': log.data.isoformat() if log.data else None,
        'resumo': log.resumo,
        'dados_antes': log.dados_antes,
        'dados_depois': log.dados_depois,
    }
