"""
APIs para ranking SIAPE com podium
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, date
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import MetaSIAPE
from apps.vendas.financeiro_vendas.models import ContratoPagamento

@login_required
@controle_acess('SS24')
@require_http_methods(["GET"])
def api_ranking(request):
    """API GET para buscar ranking com podium"""
    try:
        meta_id = request.GET.get('meta_id', '').strip()
        
        if not meta_id:
            # Buscar meta ativa mais recente
            meta = MetaSIAPE.objects.filter(status=True).order_by('-data_criacao').first()
            if not meta:
                return JsonResponse({
                    'success': False,
                    'message': 'Nenhuma meta ativa encontrada. Crie uma meta primeiro.'
                })
        else:
            try:
                meta = MetaSIAPE.objects.get(id=meta_id, status=True)
            except MetaSIAPE.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Meta não encontrada ou inativa.'
                })
        
        # Calcular valores dos contratos no período da meta
        contratos = ContratoPagamento.objects.filter(
            status_ativo=True,
            valor_tc_acumulado__gt=0,
            data_pagamento__gte=meta.data_inicio,
            data_pagamento__lte=meta.data_final,
        ).select_related('user', 'classificador')
        
        # Agrupar por vendedor e calcular total
        ranking_data = {}
        for contrato in contratos:
            user_id = contrato.user.id
            if user_id not in ranking_data:
                funcionario_nome = None
                funcionario_foto = None
                if hasattr(contrato.user, 'funcionario_profile') and contrato.user.funcionario_profile:
                    funcionario_nome = contrato.user.funcionario_profile.nome_completo
                    if contrato.user.funcionario_profile.foto:
                        funcionario_foto = contrato.user.funcionario_profile.foto.url
                
                ranking_data[user_id] = {
                    'user_id': user_id,
                    'username': contrato.user.username,
                    'funcionario_nome': funcionario_nome or contrato.user.username,
                    'funcionario_foto': funcionario_foto,
                    'valor_total': 0,
                }
            
            # Ranking = TC pago acumulado × percentual do classificador
            percentual_classificador = float(contrato.classificador.percentual) / 100
            base_tc = float(contrato.valor_tc_acumulado or 0)
            valor_ranking = base_tc * percentual_classificador
            ranking_data[user_id]['valor_total'] += valor_ranking
        
        # Converter para lista e ordenar por valor_total (decrescente)
        ranking_list = list(ranking_data.values())
        ranking_list.sort(key=lambda x: x['valor_total'], reverse=True)
        
        # Pegar top 5
        top_5 = ranking_list[:5]
        
        # Calcular valor total geral
        valor_total_geral = sum(item['valor_total'] for item in ranking_list)
        
        # Calcular percentual da meta alcançado
        valor_meta = float(meta.valor_meta)
        percentual_meta = (valor_total_geral / valor_meta * 100) if valor_meta > 0 else 0
        
        return JsonResponse({
            'success': True,
            'data': {
                'meta': {
                    'id': meta.id,
                    'titulo': meta.titulo,
                    'valor_meta': float(meta.valor_meta),
                    'data_inicio': meta.data_inicio.strftime('%Y-%m-%d'),
                    'data_final': meta.data_final.strftime('%Y-%m-%d'),
                },
                'ranking': top_5,
                'valor_total_geral': valor_total_geral,
                'percentual_meta': percentual_meta,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao calcular ranking: {str(e)}'}, status=500)

@login_required
@controle_acess('SS24')
@require_http_methods(["GET"])
def api_listar_metas_ativas(request):
    """API GET para listar metas ativas para seleção"""
    try:
        metas = MetaSIAPE.objects.filter(status=True).order_by('-data_criacao')
        data = [{
            'id': meta.id,
            'titulo': meta.titulo,
            'valor_meta': float(meta.valor_meta),
            'data_inicio': meta.data_inicio.strftime('%Y-%m-%d'),
            'data_final': meta.data_final.strftime('%Y-%m-%d'),
        } for meta in metas]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar metas: {str(e)}'}, status=500)

