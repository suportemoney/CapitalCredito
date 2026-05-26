# -*- coding: utf-8 -*-
"""Resolução e cache de logos de bancos (Brandfetch / Logo.dev)."""
import logging
import os
import re
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# COMPE → domínio oficial (seed / match por código)
BANCO_DOMINIOS_COMPE = {
    '001': ('bb.com.br', 'BB'),
    '033': ('santander.com.br', 'Santander'),
    '041': ('banrisul.com.br', 'Banrisul'),
    '070': ('brb.com.br', 'BRB'),
    '077': ('bancointer.com.br', 'Inter'),
    '104': ('caixa.gov.br', 'Caixa'),
    '237': ('bradesco.com.br', 'Bradesco'),
    '260': ('nubank.com.br', 'Nubank'),
    '290': ('pagseguro.com', 'PagBank'),
    '336': ('c6bank.com.br', 'C6'),
    '341': ('itau.com.br', 'Itaú'),
    '422': ('safra.com.br', 'Safra'),
    '748': ('sicredi.com.br', 'Sicredi'),
    '756': ('sicoob.com.br', 'Sicoob'),
}

# Palavras-chave no título → (codigo, dominio, nome_curto)
BANCO_TITULO_ALIASES = (
    (r'banco\s*do\s*brasil|^bb\b', '001', 'bb.com.br', 'BB'),
    (r'bradesco', '237', 'bradesco.com.br', 'Bradesco'),
    (r'itau|itaú', '341', 'itau.com.br', 'Itaú'),
    (r'santander', '033', 'santander.com.br', 'Santander'),
    (r'caixa', '104', 'caixa.gov.br', 'Caixa'),
    (r'nubank', '260', 'nubank.com.br', 'Nubank'),
    (r'\binter\b', '077', 'bancointer.com.br', 'Inter'),
    (r'c6', '336', 'c6bank.com.br', 'C6'),
    (r'safra', '422', 'safra.com.br', 'Safra'),
    (r'\bbrb\b', '070', 'brb.com.br', 'BRB'),
    (r'banrisul', '041', 'banrisul.com.br', 'Banrisul'),
    (r'sicredi', '748', 'sicredi.com.br', 'Sicredi'),
    (r'sicoob', '756', 'sicoob.com.br', 'Sicoob'),
    (r'pagbank|pagseguro', '290', 'pagseguro.com', 'PagBank'),
)

# CDN icones-bancos-brasileiros (matheuscuba) — classes ibb-*
# https://github.com/matheuscuba/icones-bancos-brasileiros
COMPE_PARA_IBB = {
    '001': 'ibb-banco-brasil',
    '033': 'ibb-santander',
    '041': 'ibb-banrisul',
    '077': 'ibb-inter',
    '104': 'ibb-caixa',
    '237': 'ibb-bradesco',
    '260': 'ibb-nubank',
    '341': 'ibb-itau',
    '422': 'ibb-safra',
    '748': 'ibb-sicredi',
    '756': 'ibb-sicoob',
}

TITULO_PARA_IBB = (
    (r'banco\s*do\s*brasil|^bb\b', 'ibb-banco-brasil'),
    (r'bradesco', 'ibb-bradesco'),
    (r'itau|itaú', 'ibb-itau'),
    (r'santander', 'ibb-santander'),
    (r'caixa', 'ibb-caixa'),
    (r'nubank', 'ibb-nubank'),
    (r'\binter\b', 'ibb-inter'),
    (r'safra', 'ibb-safra'),
    (r'banrisul', 'ibb-banrisul'),
    (r'sicredi', 'ibb-sicredi'),
    (r'sicoob', 'ibb-sicoob'),
    (r'banestes', 'ibb-banestes'),
    (r'hsbc', 'ibb-hsbc'),
    (r'citi', 'ibb-citi-bank'),
    (r'banco\s*do\s*nordeste|bnb', 'ibb-banco-nordeste'),
    (r'banco\s*da\s*amazonia|basa', 'ibb-banco-amazonia'),
    (r'banco\s*de\s*brasilia|brb', 'ibb-banco-brasilia'),
    (r'original', 'ibb-original'),
)

CDN_ICONES_BANCOS_BR_CSS = (
    'https://cdn.jsdelivr.net/gh/matheuscuba/icones-bancos-brasileiros@1.1/dist/all.css'
)


def classe_icone_bancos_brasileiros(codigo=None, titulo=None):
    """Retorna classe CSS ibb-* do pacote matheuscuba, ou None."""
    cod = (codigo or '').strip()
    if cod:
        cod = cod.zfill(3)
        if cod in COMPE_PARA_IBB:
            return COMPE_PARA_IBB[cod]
    titulo_norm = (titulo or '').strip().lower()
    for pattern, cls in TITULO_PARA_IBB:
        if re.search(pattern, titulo_norm, re.I):
            return cls
    return None


def _provider_preferido():
    p = (getattr(settings, 'BANCO_LOGO_PROVIDER', None) or os.environ.get('BANCO_LOGO_PROVIDER') or 'logo_dev').strip().lower()
    return p if p in ('brandfetch', 'logo_dev') else 'logo_dev'


def _logo_dev_token():
    return (getattr(settings, 'LOGO_DEV_TOKEN', None) or os.environ.get('LOGO_DEV_TOKEN') or '').strip()


def _brandfetch_key():
    return (getattr(settings, 'BRANDFETCH_API_KEY', None) or os.environ.get('BRANDFETCH_API_KEY') or '').strip()


def _normalizar_dominio(dominio):
    d = (dominio or '').strip().lower()
    d = re.sub(r'^https?://', '', d)
    d = d.split('/')[0]
    return d


def url_logo_dev(dominio):
    token = _logo_dev_token()
    dom = _normalizar_dominio(dominio)
    if not dom:
        return None
    base = f'https://img.logo.dev/{quote(dom)}'
    if token:
        return f'{base}?token={quote(token)}'
    return base


def url_brandfetch(dominio):
    key = _brandfetch_key()
    dom = _normalizar_dominio(dominio)
    if not dom or not key:
        return None
    return f'https://cdn.brandfetch.io/{quote(dom)}?c={quote(key)}'


def resolver_logo_url(dominio):
    """Retorna URL remota do logo; tenta provedor preferido e depois o alternativo."""
    dom = _normalizar_dominio(dominio)
    if not dom:
        return None
    pref = _provider_preferido()
    ordem = (
        (url_logo_dev, url_brandfetch) if pref == 'logo_dev' else (url_brandfetch, url_logo_dev)
    )
    for fn in ordem:
        url = fn(dom)
        if url:
            return url
    return None


def _baixar_imagem(url, timeout=15):
    if not url:
        return None, None
    try:
        r = requests.get(url, timeout=timeout, headers={'User-Agent': 'MoneyConsig/1.0'})
        if r.status_code != 200 or not r.content:
            return None, None
        ctype = (r.headers.get('Content-Type') or '').lower()
        ext = 'png'
        if 'jpeg' in ctype or 'jpg' in ctype:
            ext = 'jpg'
        elif 'webp' in ctype:
            ext = 'webp'
        elif 'svg' in ctype:
            ext = 'svg'
        return r.content, ext
    except Exception:
        logger.exception('banco_logo: falha ao baixar %s', url)
        return None, None


def sincronizar_logo_banco(banco, forcar=False):
    """
    Busca logo remoto e grava em banco.logo.
    Retorna (ok: bool, mensagem: str).
    """
    dom = _normalizar_dominio(banco.dominio)
    if not dom:
        return False, 'Banco sem domínio cadastrado.'
    if banco.logo and not forcar:
        return True, 'Logo local já existe.'
    remota = resolver_logo_url(dom)
    if not remota:
        return False, 'Não foi possível montar URL do logo (verifique tokens no .env).'
    conteudo, ext = _baixar_imagem(remota)
    if not conteudo:
        return False, 'Falha ao baixar imagem do logo.'
    nome = f'banco_{banco.pk or "novo"}_{dom.replace(".", "_")}.{ext}'
    banco.logo_url = remota
    banco.logo.save(nome, ContentFile(conteudo), save=False)
    banco.save(update_fields=['logo', 'logo_url'])
    return True, 'Logo sincronizado.'


def logo_url_absoluta(banco, request=None):
    """URL para exibição no front (absoluta se request informado)."""
    if not banco:
        return None
    rel = banco.logo_exibicao_url
    if not rel:
        return None
    if request and rel.startswith('/'):
        return request.build_absolute_uri(rel)
    return rel


def payload_banco(banco, request=None):
    """Dict padronizado para APIs (CRM, catálogo)."""
    if not banco:
        return {
            'banco_id': None,
            'banco': '—',
            'banco_codigo': '',
            'banco_nome_curto': '—',
            'banco_logo_url': None,
            'banco_icon_class': None,
        }
    return {
        'banco_id': banco.id,
        'banco': banco.titulo or '—',
        'banco_codigo': banco.codigo or '',
        'banco_nome_curto': (banco.nome_curto or banco.titulo or '—'),
        'banco_logo_url': logo_url_absoluta(banco, request),
        'banco_icon_class': classe_icone_bancos_brasileiros(banco.codigo, banco.titulo),
    }


def aplicar_dominio_por_codigo_ou_titulo(banco, salvar=True):
    """Preenche codigo, dominio e nome_curto a partir do mapa COMPE ou título."""
    alterou = False
    cod = (banco.codigo or '').strip().zfill(3) if banco.codigo else ''
    if cod in BANCO_DOMINIOS_COMPE:
        dom, curto = BANCO_DOMINIOS_COMPE[cod]
        if not banco.dominio:
            banco.dominio = dom
            alterou = True
        if not banco.nome_curto:
            banco.nome_curto = curto
            alterou = True
    titulo_norm = (banco.titulo or '').strip().lower()
    for pattern, codigo, dominio, curto in BANCO_TITULO_ALIASES:
        if re.search(pattern, titulo_norm, re.I):
            if not banco.codigo:
                banco.codigo = codigo
                alterou = True
            if not banco.dominio:
                banco.dominio = dominio
                alterou = True
            if not banco.nome_curto:
                banco.nome_curto = curto
                alterou = True
            break
    if salvar and alterou:
        banco.save(update_fields=['codigo', 'dominio', 'nome_curto'])
    return alterou


def aplicar_dominios_todos_bancos():
    """Atualiza domínios em todos os bancos ativos do catálogo."""
    from apps.contratos_v2.models import Banco

    n = 0
    for b in Banco.objects.filter(status=True):
        if aplicar_dominio_por_codigo_ou_titulo(b):
            n += 1
    return n
