# -*- coding: utf-8 -*-
"""API de logos do catálogo Banco (contratos)."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.contratos_v2.models import Banco
from apps.contratos_v2.services import banco_logo as logo_svc


@login_required
@require_GET
def api_get_bancos_logos(request):
    """Mapa id → logo para cache no front (CRM, dashboards)."""
    itens = []
    for b in Banco.objects.filter(status=True).order_by('titulo'):
        itens.append({
            'id': b.id,
            'titulo': b.titulo,
            'codigo': b.codigo or '',
            'nome_curto': b.nome_curto or '',
            'logo_url': logo_svc.logo_url_absoluta(b, request),
            'icon_class': logo_svc.classe_icone_bancos_brasileiros(b.codigo, b.titulo),
        })
    return JsonResponse({'ok': True, 'bancos': itens})
