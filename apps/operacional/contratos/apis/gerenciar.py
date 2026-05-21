"""
APIs para gerenciar bancos, convênios e operações (ativação)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Exists, OuterRef
# from apps.seguranca.permissoes.decorators import controle_acess
from apps.operacional.contratos.models import (
    Banco, Convenio, Operacao, BancoConvenio, 
    ConvenioOperacao, BancoConvenioOperacao, SchemaCampo
)
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# APIs para NOVO CONTRATO (Consultores) - Apenas schemas ativos por banco
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_get_bancos_ativos(request):
    """API GET para listar bancos que têm schemas ativos (para consultores)"""
    try:
        # Buscar bancos que têm pelo menos um BancoConvenioOperacao ativo
        bancos = Banco.objects.filter(
            status=True,
            schemas_ativos__ativo=True
        ).distinct().order_by('nome')
        
        data = [{
            'id': banco.id,
            'nome': banco.nome,
            'codigo': banco.codigo or '',
        } for banco in bancos]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar bancos ativos: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar bancos: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_convenios_por_banco(request):
    """API GET para listar convênios que têm schemas ativos para um banco (para consultores)"""
    try:
        banco_id = request.GET.get('banco_id')
        if not banco_id:
            return JsonResponse({'success': False, 'message': 'banco_id é obrigatório'}, status=400)
        
        # Buscar convênios que têm schemas ativos para este banco
        convenios = Convenio.objects.filter(
            operacoes_associadas__bancos_ativos__banco_id=banco_id,
            operacoes_associadas__bancos_ativos__ativo=True
        ).distinct().order_by('nome')
        
        data = [{
            'id': convenio.id,
            'nome': convenio.nome,
            'codigo': convenio.codigo or '',
        } for convenio in convenios]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar convênios por banco: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar convênios: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_operacoes_por_convenio(request):
    """API GET para listar operações que têm schemas ativos para banco+convênio (para consultores)"""
    try:
        banco_id = request.GET.get('banco_id')
        convenio_id = request.GET.get('convenio_id')
        
        if not banco_id or not convenio_id:
            return JsonResponse({'success': False, 'message': 'banco_id e convenio_id são obrigatórios'}, status=400)
        
        # Buscar schemas ativos para este banco+convênio
        bco_ativos = BancoConvenioOperacao.objects.filter(
            banco_id=banco_id,
            convenio_operacao__convenio_id=convenio_id,
            ativo=True
        ).select_related('convenio_operacao__operacao', 'convenio_operacao')
        
        data = [{
            'id': bco.convenio_operacao.operacao.id,
            'nome': bco.convenio_operacao.operacao.nome,
            'codigo': bco.convenio_operacao.operacao.codigo or '',
            'convenio_operacao_id': bco.convenio_operacao.id,  # ID do schema para usar no formulário
            'titulo_schema': bco.convenio_operacao.titulo or f"{bco.convenio_operacao.convenio.nome} - {bco.convenio_operacao.operacao.nome}",
        } for bco in bco_ativos]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar operações por convênio: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar operações: {str(e)}'}, status=500)


# =============================================================================
# APIs para GERENCIAR BANCOS (Admin/Operacional) - Hierarquia completa
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_get_bancos_todos(request):
    """API GET para listar TODOS os bancos ativos (para admin)"""
    try:
        bancos = Banco.objects.filter(status=True).order_by('nome')
        
        data = []
        for banco in bancos:
            # Contar convênios com schemas ativos para este banco
            convenios_ativos = Convenio.objects.filter(
                operacoes_associadas__bancos_ativos__banco=banco,
                operacoes_associadas__bancos_ativos__ativo=True
            ).distinct().count()
            
            data.append({
                'id': banco.id,
                'nome': banco.nome,
                'codigo': banco.codigo or '',
                'convenios_ativos': convenios_ativos,
            })
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar todos bancos: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar bancos: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_convenios_por_banco_admin(request):
    """API GET para listar convênios de um banco com info de schemas (para admin)"""
    try:
        banco_id = request.GET.get('banco_id')
        if not banco_id:
            return JsonResponse({'success': False, 'message': 'banco_id é obrigatório'}, status=400)
        
        # Buscar todos os convênios que têm schemas (independente de ativação)
        convenios = Convenio.objects.filter(
            operacoes_associadas__campos_schema__isnull=False
        ).distinct().order_by('nome')
        
        data = []
        for convenio in convenios:
            # Contar operações com schemas ativos para este banco+convênio
            operacoes_ativas = BancoConvenioOperacao.objects.filter(
                banco_id=banco_id,
                convenio_operacao__convenio=convenio,
                ativo=True
            ).count()
            
            # Verificar se tem pelo menos um schema definido
            tem_schemas = ConvenioOperacao.objects.filter(
                convenio=convenio,
                campos_schema__isnull=False
            ).exists()
            
            if tem_schemas:
                data.append({
                    'id': convenio.id,
                    'nome': convenio.nome,
                    'codigo': convenio.codigo or '',
                    'operacoes_ativas': operacoes_ativas,
                    'tem_schemas': tem_schemas,
                })
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar convênios para admin: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar convênios: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_operacoes_por_banco_convenio_admin(request):
    """API GET para listar operações de um banco+convênio com info de schemas (para admin)"""
    try:
        banco_id = request.GET.get('banco_id')
        convenio_id = request.GET.get('convenio_id')
        
        if not banco_id or not convenio_id:
            return JsonResponse({'success': False, 'message': 'banco_id e convenio_id são obrigatórios'}, status=400)
        
        # Buscar todas as operações que têm schemas para este convênio
        operacoes = Operacao.objects.filter(
            convenios_associados__convenio_id=convenio_id,
            convenios_associados__campos_schema__isnull=False
        ).distinct().order_by('nome')
        
        data = []
        for operacao in operacoes:
            # Verificar se está ativo para este banco
            bco_ativo = BancoConvenioOperacao.objects.filter(
                banco_id=banco_id,
                convenio_operacao__convenio_id=convenio_id,
                convenio_operacao__operacao=operacao,
                ativo=True
            ).select_related('convenio_operacao').first()
            
            # Contar schemas disponíveis para esta operação+convênio
            schemas_disponiveis = ConvenioOperacao.objects.filter(
                convenio_id=convenio_id,
                operacao=operacao,
                campos_schema__isnull=False
            ).distinct().count()
            
            data.append({
                'id': operacao.id,
                'nome': operacao.nome,
                'codigo': operacao.codigo or '',
                'ativo': bco_ativo is not None,
                'schema_ativo_id': bco_ativo.convenio_operacao.id if bco_ativo else None,
                'schema_ativo_titulo': bco_ativo.convenio_operacao.titulo if bco_ativo else None,
                'schemas_disponiveis': schemas_disponiveis,
            })
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar operações para admin: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar operações: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_schemas_por_operacao_admin(request):
    """API GET para listar schemas disponíveis para uma operação+convênio (para admin)"""
    try:
        banco_id = request.GET.get('banco_id')
        convenio_id = request.GET.get('convenio_id')
        operacao_id = request.GET.get('operacao_id')
        
        if not convenio_id or not operacao_id:
            return JsonResponse({'success': False, 'message': 'convenio_id e operacao_id são obrigatórios'}, status=400)
        
        # Buscar todos os schemas para esta combinação
        schemas = ConvenioOperacao.objects.filter(
            convenio_id=convenio_id,
            operacao_id=operacao_id,
            campos_schema__isnull=False
        ).distinct().annotate(campos_count=Count('campos_schema'))
        
        data = []
        for schema in schemas:
            # Verificar se está ativo para o banco específico (se banco_id informado)
            ativo_para_banco = False
            if banco_id:
                ativo_para_banco = BancoConvenioOperacao.objects.filter(
                    banco_id=banco_id,
                    convenio_operacao=schema,
                    ativo=True
                ).exists()
            
            data.append({
                'id': schema.id,
                'titulo': schema.titulo or f"{schema.convenio.nome} - {schema.operacao.nome}",
                'campos_count': schema.campos_count,
                'data_criacao': schema.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'ativo_para_banco': ativo_para_banco,
            })
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar schemas: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar schemas: {str(e)}'}, status=500)


# =============================================================================
# APIs para ATIVAÇÃO de schemas (Admin)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def api_post_ativar_banco_convenio_operacao(request):
    """API POST para ativar um schema específico para um banco"""
    try:
        banco_id = request.POST.get('banco_id')
        convenio_operacao_id = request.POST.get('convenio_operacao_id')  # ID do schema
        
        if not banco_id or not convenio_operacao_id:
            return JsonResponse({'success': False, 'message': 'banco_id e convenio_operacao_id são obrigatórios'}, status=400)
        
        banco = Banco.objects.get(id=banco_id)
        convenio_operacao = ConvenioOperacao.objects.get(id=convenio_operacao_id)
        
        # Criar ou atualizar BancoConvenio (associação banco-convênio)
        banco_convenio, _ = BancoConvenio.objects.get_or_create(
            banco=banco,
            convenio=convenio_operacao.convenio,
            defaults={'ativo': True}
        )
        if not banco_convenio.ativo:
            banco_convenio.ativo = True
            banco_convenio.save()
        
        # Criar ou atualizar BancoConvenioOperacao (ativação do schema)
        # O save() do model já cuida de desativar outros schemas do mesmo banco+convênio+operação
        bco, created = BancoConvenioOperacao.objects.get_or_create(
            banco=banco,
            convenio_operacao=convenio_operacao,
            defaults={'ativo': True}
        )
        if not created and not bco.ativo:
            bco.ativo = True
            bco.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Schema ativado com sucesso para {banco.nome}!',
            'data': {
                'banco_convenio_operacao_id': bco.id,
            }
        })
    except Banco.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Banco não encontrado'}, status=404)
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Schema não encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Erro ao ativar schema: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao ativar: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_post_desativar_banco_convenio_operacao(request):
    """API POST para desativar um schema para um banco"""
    try:
        banco_id = request.POST.get('banco_id')
        convenio_operacao_id = request.POST.get('convenio_operacao_id')
        
        if not banco_id or not convenio_operacao_id:
            return JsonResponse({'success': False, 'message': 'banco_id e convenio_operacao_id são obrigatórios'}, status=400)
        
        bco = BancoConvenioOperacao.objects.get(
            banco_id=banco_id,
            convenio_operacao_id=convenio_operacao_id
        )
        bco.ativo = False
        bco.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Schema desativado com sucesso!',
        })
    except BancoConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Associação não encontrada'}, status=404)
    except Exception as e:
        logger.error(f"Erro ao desativar schema: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao desativar: {str(e)}'}, status=500)


# =============================================================================
# APIs LEGADAS (mantidas para compatibilidade)
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_get_convenios_com_schemas(request):
    """API GET para listar convênios que têm schemas (distinct por convenio)"""
    try:
        convenios = Convenio.objects.filter(
            operacoes_associadas__campos_schema__isnull=False
        ).distinct().order_by('nome')
        
        data = [{
            'id': convenio.id,
            'nome': convenio.nome,
            'codigo': convenio.codigo or '',
        } for convenio in convenios]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar convênios com schemas: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar convênios com schemas: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_operacoes_com_schemas_por_convenio(request):
    """API GET para listar operações que têm schemas para um convênio"""
    try:
        convenio_id = request.GET.get('convenio_id')
        if not convenio_id:
            return JsonResponse({'success': False, 'message': 'convenio_id é obrigatório'}, status=400)
        
        operacoes = Operacao.objects.filter(
            convenios_associados__convenio_id=convenio_id,
            convenios_associados__campos_schema__isnull=False
        ).distinct().order_by('nome')
        
        data = [{
            'id': operacao.id,
            'nome': operacao.nome,
            'codigo': operacao.codigo or '',
        } for operacao in operacoes]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar operações com schemas: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar operações: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_titulos_schemas_por_convenio_operacao(request):
    """API GET para listar títulos de schemas (ConvenioOperacao) para um convenio+operação"""
    try:
        convenio_id = request.GET.get('convenio_id')
        operacao_id = request.GET.get('operacao_id')
        
        if not convenio_id or not operacao_id:
            return JsonResponse({'success': False, 'message': 'convenio_id e operacao_id são obrigatórios'}, status=400)
        
        schemas = ConvenioOperacao.objects.filter(
            convenio_id=convenio_id,
            operacao_id=operacao_id,
            campos_schema__isnull=False
        ).distinct().annotate(campos_count=Count('campos_schema')).order_by('-data_criacao')
        
        data = [{
            'id': co.id,
            'titulo': co.titulo or f"{co.convenio.nome} - {co.operacao.nome}",
            'campos_count': co.campos_count,
            'data_criacao': co.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for co in schemas]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Erro ao listar títulos de schemas: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar títulos de schemas: {str(e)}'}, status=500)
