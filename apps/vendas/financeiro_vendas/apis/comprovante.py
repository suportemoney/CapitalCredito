"""
APIs de comprovante TC no financeiro vendas (registros legados e manuais).
"""
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction

from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.financeiro_vendas.models import ComprovanteTC, ContratoPagamento


def _dec(val):
    if val in (None, ''):
        return None
    try:
        return Decimal(str(val).replace(',', '.'))
    except Exception:
        return None


def _serializar_comprovante(request, comp):
    url = None
    if comp.arquivo:
        try:
            url = request.build_absolute_uri(comp.arquivo.url)
        except Exception:
            url = comp.arquivo.url
    return {
        'id': comp.id,
        'valor': float(comp.valor),
        'arquivo_url': url,
        'criado_por': comp.criado_por.username if comp.criado_por_id else '',
        'criado_em': comp.criado_em.isoformat() if comp.criado_em else '',
    }


@login_required
@controle_acess('SS27')
@require_http_methods(['GET'])
def api_listar_comprovantes_tc(request):
    """Lista comprovantes TC de um ContratoPagamento."""
    try:
        contrato_id = int(request.GET.get('contrato_pagamento_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'contrato_pagamento_id inválido'}, status=400)

    if not contrato_id:
        return JsonResponse({'success': False, 'message': 'contrato_pagamento_id obrigatório'}, status=400)

    try:
        cp = ContratoPagamento.objects.get(pk=contrato_id, status_ativo=True)
    except ContratoPagamento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)

    comps = (
        ComprovanteTC.objects.filter(contrato_pagamento=cp, status=True)
        .select_related('criado_por')
        .order_by('criado_em')
    )
    soma = sum((c.valor for c in comps), Decimal('0'))

    return JsonResponse({
        'success': True,
        'data': {
            'comprovantes': [_serializar_comprovante(request, c) for c in comps],
            'soma': float(soma),
            'valor_tc': float(cp.valor_tc or 0),
            'valor_tc_acumulado': float(cp.valor_tc_acumulado or 0),
        },
    })


@login_required
@controle_acess('SS27')
@require_http_methods(['POST'])
def api_upload_comprovante_tc(request):
    """Upload de comprovante TC em ContratoPagamento (legado / manual)."""
    try:
        contrato_id = int(request.POST.get('contrato_pagamento_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'contrato_pagamento_id inválido'}, status=400)

    valor = _dec(request.POST.get('valor'))
    arquivo = request.FILES.get('arquivo')

    if not contrato_id:
        return JsonResponse({'success': False, 'message': 'contrato_pagamento_id obrigatório'}, status=400)
    if valor is None or valor <= 0:
        return JsonResponse({'success': False, 'message': 'Valor inválido'}, status=400)
    if not arquivo:
        return JsonResponse({'success': False, 'message': 'Anexe o comprovante'}, status=400)

    try:
        cp = ContratoPagamento.objects.get(pk=contrato_id, status_ativo=True)
    except ContratoPagamento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)

    if cp.contrato_execucao_id:
        return JsonResponse({
            'success': False,
            'message': 'Contrato vinculado ao operacional — comprovante deve ser enviado pelo CRM (contratos v2).',
        }, status=400)

    try:
        with transaction.atomic():
            comp = ComprovanteTC.objects.create(
                contrato_pagamento=cp,
                valor=valor,
                arquivo=arquivo,
                criado_por=request.user,
            )
            cp.recalcular_tc_acumulado()
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao salvar comprovante: {str(e)}'}, status=500)

    return JsonResponse({
        'success': True,
        'message': 'Comprovante registrado com sucesso!',
        'data': {
            'comprovante_id': comp.id,
            'valor_tc_acumulado': float(cp.valor_tc_acumulado or 0),
            'valor_tc': float(cp.valor_tc or 0),
            'status': cp.status,
        },
    })


@login_required
@controle_acess('SS27')
@require_http_methods(['POST'])
def api_excluir_comprovante_tc(request):
    """Soft delete de comprovante TC manual (sem vínculo v2)."""
    try:
        contrato_id = int(request.POST.get('contrato_pagamento_id') or 0)
        comprovante_id = int(request.POST.get('comprovante_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'IDs inválidos'}, status=400)

    if not contrato_id or not comprovante_id:
        return JsonResponse({'success': False, 'message': 'contrato_pagamento_id e comprovante_id obrigatórios'}, status=400)

    try:
        cp = ContratoPagamento.objects.get(pk=contrato_id, status_ativo=True)
        comp = ComprovanteTC.objects.get(
            pk=comprovante_id,
            contrato_pagamento=cp,
            status=True,
        )
    except (ContratoPagamento.DoesNotExist, ComprovanteTC.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Registro não encontrado'}, status=404)

    if comp.comprovante_v2_id:
        return JsonResponse({
            'success': False,
            'message': 'Comprovante sincronizado do CRM — exclua pelo operacional (contratos v2).',
        }, status=400)

    with transaction.atomic():
        comp.status = False
        comp.save(update_fields=['status'])
        cp.recalcular_tc_acumulado()

    return JsonResponse({
        'success': True,
        'message': 'Comprovante excluído.',
        'data': {
            'valor_tc_acumulado': float(cp.valor_tc_acumulado or 0),
            'status': cp.status,
        },
    })
