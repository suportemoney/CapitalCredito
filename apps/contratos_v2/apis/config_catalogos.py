# -*- coding: utf-8 -*-
"""APIs JSON para CRUD dos cat├ílogos (Banco, Conv├¬nio, Produto, Tabela CMS) ÔÇö permiss├úo SCT192."""
import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods

from apps.seguranca.permissoes.decorators import controle_acess

from apps.contratos_v2.models import Banco, Convenio, LogCatalogoContratos, Produto, TabelaCms
from apps.contratos_v2.services import catalogo_auditoria as audit


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return {}


def _dec(v):
    if v is None or v == '':
        return None
    try:
        return Decimal(str(v).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _normalizar_titulo(v):
    """Normaliza t├¡tulos removendo espa├ºos excedentes nas pontas e no meio."""
    return ' '.join((v or '').strip().split())


def _normalizar_cabecalho(v):
    return (v or '').replace('\ufeff', '').strip().lower()


def _iterar_csv_coluna_unica(texto, coluna_esperada):
    """
    Itera CSVs de coluna ├║nica aceitando:
    - com cabe├ºalho (ex.: produto)
    - sem cabe├ºalho (primeira linha j├í ├® valor)
    """
    linhas = texto.splitlines()
    if not linhas:
        return

    amostra = '\n'.join(linhas[:5]) or texto
    try:
        dialect = csv.Sniffer().sniff(amostra, delimiters=';,|\t')
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(texto), dialect=dialect)
    for idx, row in enumerate(reader, start=1):
        if not row or not any((c or '').strip() for c in row):
            yield idx, ''
            continue

        valor = (row[0] or '').strip()
        if idx == 1 and _normalizar_cabecalho(valor) == coluna_esperada:
            # ignora cabe├ºalho quando existir
            continue
        yield idx, valor


def _banco_dict(o, request=None):
    from apps.contratos_v2.services import banco_logo as logo_svc

    return {
        'id': o.id,
        'titulo': o.titulo,
        'codigo': o.codigo or '',
        'nome_curto': o.nome_curto or '',
        'dominio': o.dominio or '',
        'logo_url': logo_svc.logo_url_absoluta(o, request),
        'icon_class': logo_svc.classe_icone_bancos_brasileiros(o.codigo, o.titulo),
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


def _validar_flags_produto_mutuas(flag_port, flag_refin):
    if flag_port and flag_refin:
        return 'Um produto n├úo pode ter "Port + Refin" e "Refin da Port" ao mesmo tempo.'


def _aplicar_flags_produto(o, data):
    """Atualiza flags do produto a partir do JSON; retorna mensagem de erro ou None."""
    if 'flag_port_mais_refin' not in data and 'flag_refin_da_port' not in data:
        return None
    port = bool(data.get('flag_port_mais_refin', o.flag_port_mais_refin))
    refin = bool(data.get('flag_refin_da_port', o.flag_refin_da_port))
    err = _validar_flags_produto_mutuas(port, refin)
    if err:
        return err
    o.flag_port_mais_refin = port
    o.flag_refin_da_port = refin
    return None


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


@login_required
@controle_acess('SCT192')
@require_GET
def api_get_catalogo_dependencias(request):
    """Retorna quantas TabelaCms dependem de um Banco/Convenio/Produto.

    Usado pela UI de configura├º├úo para exibir um alerta antes de inativar
    um item do cat├ílogo ("Este banco ├® usado em N tabela(s) CMS ativa(s)").
    """
    tipo = (request.GET.get('tipo') or '').strip().lower()
    try:
        pk = int(request.GET.get('id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'id inv├ílido.'}, status=400)
    if tipo not in ('banco', 'convenio', 'produto'):
        return JsonResponse({'ok': False, 'erro': 'tipo deve ser banco, convenio ou produto.'}, status=400)
    campo = {'banco': 'banco_id', 'convenio': 'convenio_id', 'produto': 'produto_id'}[tipo]
    qs_total = TabelaCms.objects.filter(**{campo: pk})
    total = qs_total.count()
    ativas = qs_total.filter(status=True).count()
    return JsonResponse({
        'ok': True,
        'total': total,
        'ativas': ativas,
        'inativas': total - ativas,
    })


@login_required
@controle_acess('SCT192')
@require_GET
def api_get_config_resumo(request):
    """Lista completa dos cat├ílogos (inclui inativos) para a tela de configura├º├úo."""
    bancos = [_banco_dict(x) for x in Banco.objects.all().order_by('titulo')]
    convenios = [_convenio_dict(x) for x in Convenio.objects.all().order_by('titulo')]
    produtos = [_produto_dict(x) for x in Produto.objects.all().order_by('titulo')]
    tabelas = [
        _tabela_cms_dict(x)
        for x in TabelaCms.objects.select_related('banco', 'convenio', 'produto').order_by('-data_criacao')
    ]
    return JsonResponse({
        'ok': True,
        'bancos': bancos,
        'convenios': convenios,
        'produtos': produtos,
        'tabelas_cms': tabelas,
    })


@login_required
@controle_acess('SCT192')
@require_GET
def api_get_config_logs(request):
    """Lista logs de auditoria do cat├ílogo ÔÇö somente superusu├írios."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'erro': 'Acesso negado.'}, status=403)

    entidade = (request.GET.get('entidade') or '').strip().lower()
    acao = (request.GET.get('acao') or '').strip().lower()
    data_inicio = (request.GET.get('data_inicio') or '').strip()
    data_fim = (request.GET.get('data_fim') or '').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(100, max(10, int(request.GET.get('page_size', 50))))
    except (TypeError, ValueError):
        page_size = 50

    qs = LogCatalogoContratos.objects.select_related('usuario').order_by('-data')
    if entidade in dict(LogCatalogoContratos.ENTIDADE_CHOICES):
        qs = qs.filter(entidade=entidade)
    if acao in dict(LogCatalogoContratos.ACAO_CHOICES):
        qs = qs.filter(acao=acao)
    if data_inicio:
        qs = qs.filter(data__date__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data__date__lte=data_fim)

    total = qs.count()
    offset = (page - 1) * page_size
    logs = [audit.log_dict_entrada(x) for x in qs[offset:offset + page_size]]
    return JsonResponse({
        'ok': True,
        'logs': logs,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size if page_size else 1,
    })


def _log_apos_patch(request, entidade, instance, antes):
    depois = audit.snapshot(entidade, instance)
    acao = audit.inferir_acao_edicao(entidade, antes, depois)
    audit.registrar_log(
        request,
        acao=acao,
        entidade=entidade,
        registro_id=instance.id,
        registro_titulo=instance.titulo,
        antes=antes,
        depois=depois,
    )


# --- Banco ---


@login_required
@controle_acess('SCT192')
@require_http_methods(['POST'])
def api_post_banco(request):
    # Cria Banco com:
    # - normaliza├º├úo de t├¡tulo (espa├ºos colapsados, trim)
    # - guarda contra duplicata case-insensitive (iexact)
    # - reativa├º├úo autom├ítica quando o registro existente estiver inativo
    data = _json_body(request)
    titulo = _normalizar_titulo(data.get('titulo'))
    if not titulo:
        return JsonResponse({'ok': False, 'erro': 'T├¡tulo do banco ├® obrigat├│rio.'}, status=400)
    codigo = (data.get('codigo') or '').strip() or None
    status = bool(data.get('status', True))
    existente = Banco.objects.filter(titulo__iexact=titulo).first()
    if existente:
        antes = audit.snapshot('banco', existente)
        alterado = False
        if status and not existente.status:
            existente.status = True
            alterado = True
        if codigo and (existente.codigo or '') != codigo:
            existente.codigo = codigo
            alterado = True
        if alterado:
            existente.save()
            _log_apos_patch(request, 'banco', existente, antes)
        return JsonResponse({'ok': True, 'item': _banco_dict(existente), 'ja_existia': True})
    o = Banco.objects.create(titulo=titulo, codigo=codigo, status=status)
    audit.registrar_log(
        request,
        acao='criar',
        entidade='banco',
        registro_id=o.id,
        registro_titulo=o.titulo,
        depois=audit.snapshot('banco', o),
    )
    return JsonResponse({'ok': True, 'item': _banco_dict(o), 'ja_existia': False})


@login_required
@controle_acess('SCT192')
@require_http_methods(['PATCH', 'DELETE'])
def api_detail_banco(request, pk):
    o = get_object_or_404(Banco, pk=pk)
    if request.method == 'DELETE':
        antes = audit.snapshot('banco', o)
        o.status = False
        o.save(update_fields=['status'])
        depois = audit.snapshot('banco', o)
        audit.registrar_log(
            request,
            acao='inativar',
            entidade='banco',
            registro_id=o.id,
            registro_titulo=o.titulo,
            antes=antes,
            depois=depois,
        )
        return JsonResponse({'ok': True, 'soft': True})
    antes = audit.snapshot('banco', o)
    data = _json_body(request)
    if 'titulo' in data:
        t = _normalizar_titulo(data.get('titulo'))
        if not t:
            return JsonResponse({'ok': False, 'erro': 'T├¡tulo n├úo pode ser vazio.'}, status=400)
        # Impede colis├úo case-insensitive com outro registro.
        if Banco.objects.filter(titulo__iexact=t).exclude(pk=o.pk).exists():
            return JsonResponse({'ok': False, 'erro': 'J├í existe outro banco com este t├¡tulo.'}, status=400)
        o.titulo = t
    if 'codigo' in data:
        o.codigo = (data.get('codigo') or '').strip() or None
    if 'status' in data:
        o.status = bool(data['status'])
    o.save()
    _log_apos_patch(request, 'banco', o, antes)
    return JsonResponse({'ok': True, 'item': _banco_dict(o)})


# --- Conv├¬nio ---


@login_required
@controle_acess('SCT192')
@require_http_methods(['POST'])
def api_post_convenio(request):
    # Mesma regra de guarda contra duplicata aplicada em api_post_produto.
    data = _json_body(request)
    titulo = _normalizar_titulo(data.get('titulo'))
    if not titulo:
        return JsonResponse({'ok': False, 'erro': 'T├¡tulo do conv├¬nio ├® obrigat├│rio.'}, status=400)
    status = bool(data.get('status', True))
    existente = Convenio.objects.filter(titulo__iexact=titulo).first()
    if existente:
        antes = audit.snapshot('convenio', existente)
        if status and not existente.status:
            existente.status = True
            existente.save(update_fields=['status'])
            _log_apos_patch(request, 'convenio', existente, antes)
        return JsonResponse({'ok': True, 'item': _convenio_dict(existente), 'ja_existia': True})
    o = Convenio.objects.create(titulo=titulo, status=status)
    audit.registrar_log(
        request,
        acao='criar',
        entidade='convenio',
        registro_id=o.id,
        registro_titulo=o.titulo,
        depois=audit.snapshot('convenio', o),
    )
    return JsonResponse({'ok': True, 'item': _convenio_dict(o), 'ja_existia': False})


@login_required
@controle_acess('SCT192')
@require_http_methods(['PATCH', 'DELETE'])
def api_detail_convenio(request, pk):
    o = get_object_or_404(Convenio, pk=pk)
    if request.method == 'DELETE':
        antes = audit.snapshot('convenio', o)
        o.status = False
        o.save(update_fields=['status'])
        depois = audit.snapshot('convenio', o)
        audit.registrar_log(
            request,
            acao='inativar',
            entidade='convenio',
            registro_id=o.id,
            registro_titulo=o.titulo,
            antes=antes,
            depois=depois,
        )
        return JsonResponse({'ok': True, 'soft': True})
    antes = audit.snapshot('convenio', o)
    data = _json_body(request)
    if 'titulo' in data:
        t = _normalizar_titulo(data.get('titulo'))
        if not t:
            return JsonResponse({'ok': False, 'erro': 'T├¡tulo n├úo pode ser vazio.'}, status=400)
        if Convenio.objects.filter(titulo__iexact=t).exclude(pk=o.pk).exists():
            return JsonResponse({'ok': False, 'erro': 'J├í existe outro conv├¬nio com este t├¡tulo.'}, status=400)
        o.titulo = t
    if 'status' in data:
        o.status = bool(data['status'])
    o.save()
    _log_apos_patch(request, 'convenio', o, antes)
    return JsonResponse({'ok': True, 'item': _convenio_dict(o)})


# --- Produto ---


@login_required
@controle_acess('SCT192')
@require_http_methods(['POST'])
def api_post_produto(request):
    data = _json_body(request)
    titulo = _normalizar_titulo(data.get('titulo'))
    if not titulo:
        return JsonResponse({'ok': False, 'erro': 'T├¡tulo do produto ├® obrigat├│rio.'}, status=400)
    status = bool(data.get('status', True))
    flag_port = bool(data.get('flag_port_mais_refin', False))
    flag_refin = bool(data.get('flag_refin_da_port', False))
    err_flags = _validar_flags_produto_mutuas(flag_port, flag_refin)
    if err_flags:
        return JsonResponse({'ok': False, 'erro': err_flags}, status=400)
    existente = Produto.objects.filter(titulo__iexact=titulo).first()
    if existente:
        antes = audit.snapshot('produto', existente)
        upd = []
        if status and not existente.status:
            existente.status = True
            upd.append('status')
        if 'flag_port_mais_refin' in data or 'flag_refin_da_port' in data:
            existente.flag_port_mais_refin = flag_port
            existente.flag_refin_da_port = flag_refin
            upd.extend(['flag_port_mais_refin', 'flag_refin_da_port'])
        if upd:
            existente.save(update_fields=upd)
            _log_apos_patch(request, 'produto', existente, antes)
        return JsonResponse({'ok': True, 'item': _produto_dict(existente), 'ja_existia': True})

    o = Produto.objects.create(
        titulo=titulo,
        status=status,
        flag_port_mais_refin=flag_port,
        flag_refin_da_port=flag_refin,
    )
    audit.registrar_log(
        request,
        acao='criar',
        entidade='produto',
        registro_id=o.id,
        registro_titulo=o.titulo,
        depois=audit.snapshot('produto', o),
    )
    return JsonResponse({'ok': True, 'item': _produto_dict(o), 'ja_existia': False})


@login_required
@controle_acess('SCT192')
@require_http_methods(['PATCH', 'DELETE'])
def api_detail_produto(request, pk):
    o = get_object_or_404(Produto, pk=pk)
    if request.method == 'DELETE':
        antes = audit.snapshot('produto', o)
        o.status = False
        o.save(update_fields=['status'])
        depois = audit.snapshot('produto', o)
        audit.registrar_log(
            request,
            acao='inativar',
            entidade='produto',
            registro_id=o.id,
            registro_titulo=o.titulo,
            antes=antes,
            depois=depois,
        )
        return JsonResponse({'ok': True, 'soft': True})
    antes = audit.snapshot('produto', o)
    data = _json_body(request)
    if 'titulo' in data:
        t = _normalizar_titulo(data.get('titulo'))
        if not t:
            return JsonResponse({'ok': False, 'erro': 'T├¡tulo n├úo pode ser vazio.'}, status=400)
        if Produto.objects.filter(titulo__iexact=t).exclude(pk=o.pk).exists():
            return JsonResponse({'ok': False, 'erro': 'J├í existe outro produto com este t├¡tulo.'}, status=400)
        o.titulo = t
    if 'status' in data:
        o.status = bool(data['status'])
    err_flags = _aplicar_flags_produto(o, data)
    if err_flags:
        return JsonResponse({'ok': False, 'erro': err_flags}, status=400)
    o.save()
    _log_apos_patch(request, 'produto', o, antes)
    return JsonResponse({'ok': True, 'item': _produto_dict(o)})


# --- Tabela CMS ---


@login_required
@controle_acess('SCT192')
@require_http_methods(['POST'])
def api_post_tabela_cms(request):
    data = _json_body(request)
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return JsonResponse({'ok': False, 'erro': 'T├¡tulo da tabela ├® obrigat├│rio.'}, status=400)
    try:
        banco_id = int(data.get('banco_id'))
        convenio_id = int(data.get('convenio_id'))
        produto_id = int(data.get('produto_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'Informe banco, conv├¬nio e produto v├ílidos.'}, status=400)
    if not Banco.objects.filter(pk=banco_id).exists():
        return JsonResponse({'ok': False, 'erro': 'Banco n├úo encontrado.'}, status=400)
    if not Convenio.objects.filter(pk=convenio_id).exists():
        return JsonResponse({'ok': False, 'erro': 'Conv├¬nio n├úo encontrado.'}, status=400)
    if not Produto.objects.filter(pk=produto_id).exists():
        return JsonResponse({'ok': False, 'erro': 'Produto n├úo encontrado.'}, status=400)
    classificador = (data.get('classificador_banco') or 'M1').strip().upper()
    if classificador not in ('M1', 'M2', 'M3'):
        classificador = 'M1'
    o = TabelaCms(
        titulo=titulo,
        banco_id=banco_id,
        convenio_id=convenio_id,
        produto_id=produto_id,
        classificador_banco=classificador,
        taxa_recebido=_dec(data.get('taxa_recebido')),
        taxa_repasse=_dec(data.get('taxa_repasse')),
        taxa_plastico=_dec(data.get('taxa_plastico')),
        status=bool(data.get('status', True)),
    )
    o.save()
    o = TabelaCms.objects.select_related('banco', 'convenio', 'produto').get(pk=o.pk)
    audit.registrar_log(
        request,
        acao='criar',
        entidade='tabela_cms',
        registro_id=o.id,
        registro_titulo=o.titulo,
        depois=audit.snapshot('tabela_cms', o),
    )
    return JsonResponse({'ok': True, 'item': _tabela_cms_dict(o)})


@login_required
@controle_acess('SCT192')
@require_http_methods(['DELETE'])
def api_delete_banco(request, pk):
    """Exclui Banco definitivamente (SCT192)."""
    o = get_object_or_404(Banco, pk=pk)
    antes = audit.snapshot('banco', o)
    reg_id = o.id
    titulo = o.titulo
    try:
        o.delete()
    except ProtectedError:
        return JsonResponse({'ok': False, 'erro': 'Banco possui v├¡nculos. Inative-o em vez de excluir.'}, status=400)
    audit.registrar_log(
        request,
        acao='excluir',
        entidade='banco',
        registro_id=reg_id,
        registro_titulo=titulo,
        antes=antes,
        depois=None,
    )
    return JsonResponse({'ok': True})


@login_required
@controle_acess('SCT192')
@require_http_methods(['DELETE'])
def api_delete_convenio(request, pk):
    """Exclui Conv├¬nio definitivamente (SCT192)."""
    o = get_object_or_404(Convenio, pk=pk)
    antes = audit.snapshot('convenio', o)
    reg_id = o.id
    titulo = o.titulo
    try:
        o.delete()
    except ProtectedError:
        return JsonResponse({'ok': False, 'erro': 'Conv├¬nio possui v├¡nculos. Inative-o em vez de excluir.'}, status=400)
    audit.registrar_log(
        request,
        acao='excluir',
        entidade='convenio',
        registro_id=reg_id,
        registro_titulo=titulo,
        antes=antes,
        depois=None,
    )
    return JsonResponse({'ok': True})


@login_required
@controle_acess('SCT192')
@require_http_methods(['DELETE'])
def api_delete_produto(request, pk):
    """Exclui Produto definitivamente (SCT192)."""
    o = get_object_or_404(Produto, pk=pk)
    antes = audit.snapshot('produto', o)
    reg_id = o.id
    titulo = o.titulo
    try:
        o.delete()
    except ProtectedError:
        return JsonResponse({'ok': False, 'erro': 'Produto possui v├¡nculos. Inative-o em vez de excluir.'}, status=400)
    audit.registrar_log(
        request,
        acao='excluir',
        entidade='produto',
        registro_id=reg_id,
        registro_titulo=titulo,
        antes=antes,
        depois=None,
    )
    return JsonResponse({'ok': True})


@login_required
@controle_acess('SCT192')
@require_http_methods(['POST'])
def api_post_importar_csv(request):
    """Importa Bancos, Conv├¬nios ou Produtos a partir de arquivo CSV enviado via multipart.

    Par├ómetros POST:
        tipo    ÔÇö 'banco' | 'convenio' | 'produto'
        arquivo ÔÇö arquivo .csv

    Retorna { ok, criados, ignorados, erros } onde erros ├® lista de strings descritivas.
    """
    tipo = (request.POST.get('tipo') or '').strip().lower()
    if tipo not in ('banco', 'convenio', 'produto'):
        return JsonResponse({'ok': False, 'erro': "Par├ómetro 'tipo' inv├ílido. Use banco, convenio ou produto."}, status=400)

    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Nenhum arquivo enviado.'}, status=400)

    # l├¬ bytes e detecta BOM (utf-8-sig) ou tenta utf-8 ÔåÆ latin-1
    raw = arquivo.read()
    for enc in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
        try:
            texto = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return JsonResponse({'ok': False, 'erro': 'N├úo foi poss├¡vel decodificar o arquivo. Use UTF-8 ou Latin-1.'}, status=400)

    criados = 0
    ignorados = 0
    linhas_vazias = 0
    ja_existiam = 0
    erros = []

    if tipo == 'banco':
        # formato: codigo_banco;nome_banco  (separador ponto-e-v├¡rgula)
        reader = csv.DictReader(io.StringIO(texto), delimiter=';')
        for i, row in enumerate(reader, start=2):
            nome = (row.get('nome_banco') or '').strip()
            codigo = (row.get('codigo_banco') or '').strip()
            if not nome:
                erros.append(f'Linha {i}: nome_banco vazio ÔÇö ignorado.')
                ignorados += 1
                continue
            titulo = nome.upper()
            _, created = Banco.objects.get_or_create(
                titulo__iexact=titulo,
                defaults={'titulo': titulo, 'codigo': codigo or None, 'status': True},
            )
            if created:
                criados += 1
            else:
                ignorados += 1

    elif tipo == 'convenio':
        # formato: coluna ├║nica (com ou sem cabe├ºalho "convenio")
        for i, nome in _iterar_csv_coluna_unica(texto, 'convenio'):
            if not nome:
                linhas_vazias += 1
                ignorados += 1
                continue
            titulo = _normalizar_titulo(nome).upper()
            _, created = Convenio.objects.get_or_create(
                titulo__iexact=titulo,
                defaults={'titulo': titulo, 'status': True},
            )
            if created:
                criados += 1
            else:
                ja_existiam += 1
                ignorados += 1

    elif tipo == 'produto':
        # formato: coluna ├║nica (com ou sem cabe├ºalho "produto")
        for i, nome in _iterar_csv_coluna_unica(texto, 'produto'):
            if not nome:
                linhas_vazias += 1
                ignorados += 1
                continue
            titulo = _normalizar_titulo(nome).upper()
            _, created = Produto.objects.get_or_create(
                titulo__iexact=titulo,
                defaults={'titulo': titulo, 'status': True},
            )
            if created:
                criados += 1
            else:
                ja_existiam += 1
                ignorados += 1

    audit.registrar_log(
        request,
        acao='importar_csv',
        entidade=tipo,
        resumo=(
            f'Importa├º├úo CSV ({tipo}): {criados} criado(s), {ignorados} ignorado(s), '
            f'{ja_existiam} j├í existente(s).'
        ),
        depois={
            'tipo': tipo,
            'criados': criados,
            'ignorados': ignorados,
            'linhas_vazias': linhas_vazias,
            'ja_existiam': ja_existiam,
            'erros': erros[:50],
        },
    )
    return JsonResponse({
        'ok': True,
        'criados': criados,
        'ignorados': ignorados,
        'linhas_vazias': linhas_vazias,
        'ja_existiam': ja_existiam,
        'erros': erros,
    })


@login_required
@controle_acess('SCT192')
@require_http_methods(['PATCH', 'DELETE'])
def api_detail_tabela_cms(request, pk):
    o = get_object_or_404(TabelaCms.objects.select_related('banco', 'convenio', 'produto'), pk=pk)
    if request.method == 'DELETE':
        antes = audit.snapshot('tabela_cms', o)
        reg_id = o.id
        titulo = o.titulo
        try:
            o.delete()
            audit.registrar_log(
                request,
                acao='excluir',
                entidade='tabela_cms',
                registro_id=reg_id,
                registro_titulo=titulo,
                antes=antes,
                depois=None,
            )
            return JsonResponse({'ok': True})
        except ProtectedError:
            o.status = False
            o.save(update_fields=['status'])
            depois = audit.snapshot('tabela_cms', o)
            audit.registrar_log(
                request,
                acao='inativar',
                entidade='tabela_cms',
                registro_id=o.id,
                registro_titulo=o.titulo,
                antes=antes,
                depois=depois,
                resumo=f'Tabela CMS #{o.id}: exclus├úo bloqueada por v├¡nculos; inativada.',
            )
            return JsonResponse({'ok': True, 'soft': True})
    antes = audit.snapshot('tabela_cms', o)
    data = _json_body(request)
    if 'titulo' in data:
        t = (data.get('titulo') or '').strip()
        if not t:
            return JsonResponse({'ok': False, 'erro': 'T├¡tulo n├úo pode ser vazio.'}, status=400)
        o.titulo = t
    if 'banco_id' in data:
        try:
            bid = int(data['banco_id'])
            if not Banco.objects.filter(pk=bid).exists():
                return JsonResponse({'ok': False, 'erro': 'Banco n├úo encontrado.'}, status=400)
            o.banco_id = bid
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'erro': 'banco_id inv├ílido.'}, status=400)
    if 'convenio_id' in data:
        try:
            cid = int(data['convenio_id'])
            if not Convenio.objects.filter(pk=cid).exists():
                return JsonResponse({'ok': False, 'erro': 'Conv├¬nio n├úo encontrado.'}, status=400)
            o.convenio_id = cid
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'erro': 'convenio_id inv├ílido.'}, status=400)
    if 'produto_id' in data:
        try:
            pid = int(data['produto_id'])
            if not Produto.objects.filter(pk=pid).exists():
                return JsonResponse({'ok': False, 'erro': 'Produto n├úo encontrado.'}, status=400)
            o.produto_id = pid
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'erro': 'produto_id inv├ílido.'}, status=400)
    if 'taxa_recebido' in data:
        o.taxa_recebido = _dec(data.get('taxa_recebido'))
    if 'taxa_repasse' in data:
        o.taxa_repasse = _dec(data.get('taxa_repasse'))
    if 'taxa_plastico' in data:
        o.taxa_plastico = _dec(data.get('taxa_plastico'))
    if 'classificador_banco' in data:
        cls = (data.get('classificador_banco') or 'M1').strip().upper()
        if cls not in ('M1', 'M2', 'M3'):
            return JsonResponse({'ok': False, 'erro': 'Classificador inv├ílido (use M1, M2 ou M3).'}, status=400)
        o.classificador_banco = cls
    if 'status' in data:
        o.status = bool(data['status'])
    o.save()
    o = TabelaCms.objects.select_related('banco', 'convenio', 'produto').get(pk=o.pk)
    _log_apos_patch(request, 'tabela_cms', o, antes)
    return JsonResponse({'ok': True, 'item': _tabela_cms_dict(o)})
