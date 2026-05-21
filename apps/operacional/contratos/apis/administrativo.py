"""
APIs administrativas (CRUD completo + importação CSV) - apenas ADMIN
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
# from apps.seguranca.permissoes.decorators import controle_acess  # Permissão será configurada depois
from apps.operacional.contratos.models import Banco, Convenio, Operacao, BancoConvenio, ConvenioOperacao
import csv
import io

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["GET"])
def api_get_bancos(request):
    """API GET para listar todos os bancos"""
    try:
        bancos = Banco.objects.all().order_by('nome')
        data = [{
            'id': banco.id,
            'nome': banco.nome,
            'codigo': banco.codigo or '',
            'status': banco.status,
            'data_criacao': banco.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for banco in bancos]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar bancos: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_criar_banco(request):
    """API POST para criar banco"""
    try:
        nome = request.POST.get('nome', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        banco = Banco.objects.create(
            nome=nome,
            codigo=codigo if codigo else None,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Banco criado com sucesso!',
            'data': {
                'id': banco.id,
                'nome': banco.nome,
                'codigo': banco.codigo or '',
                'status': banco.status,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar banco: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_importar_bancos_csv(request):
    """API POST para importar bancos em lote via CSV"""
    try:
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Arquivo CSV é obrigatório'})
        
        arquivo = request.FILES['arquivo']
        file_content = arquivo.read().decode('utf-8-sig')  # utf-8-sig remove BOM se existir
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=';')
        
        criados = 0
        erros = []
        
        for row in csv_reader:
            try:
                nome = row.get('nome', '').strip()
                if not nome:
                    continue
                
                codigo = row.get('codigo', '').strip()
                
                banco, created = Banco.objects.get_or_create(
                    nome=nome,
                    defaults={'codigo': codigo if codigo else None, 'status': True}
                )
                
                if created:
                    criados += 1
                    
            except Exception as e:
                erros.append(f'Erro ao processar {nome}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'CSV processado: {criados} bancos criados',
            'data': {
                'criados': criados,
                'erros': erros,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao processar CSV: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["GET"])
def api_get_convenios(request):
    """API GET para listar todos os convênios"""
    try:
        convenios = Convenio.objects.all().order_by('nome')
        data = [{
            'id': convenio.id,
            'nome': convenio.nome,
            'codigo': convenio.codigo or '',
            'status': convenio.status,
            'data_criacao': convenio.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for convenio in convenios]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar convênios: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_criar_convenio(request):
    """API POST para criar convênio"""
    try:
        nome = request.POST.get('nome', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        convenio = Convenio.objects.create(
            nome=nome,
            codigo=codigo if codigo else None,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Convênio criado com sucesso!',
            'data': {
                'id': convenio.id,
                'nome': convenio.nome,
                'codigo': convenio.codigo or '',
                'status': convenio.status,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar convênio: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_importar_convenios_csv(request):
    """API POST para importar convênios em lote via CSV"""
    try:
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Arquivo CSV é obrigatório'})
        
        arquivo = request.FILES['arquivo']
        file_content = arquivo.read().decode('utf-8-sig')  # utf-8-sig remove BOM se existir
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=';')
        
        criados = 0
        erros = []
        
        for row in csv_reader:
            try:
                nome = row.get('nome', '').strip()
                if not nome:
                    continue
                
                codigo = row.get('codigo', '').strip()
                
                convenio, created = Convenio.objects.get_or_create(
                    nome=nome,
                    defaults={'codigo': codigo if codigo else None, 'status': True}
                )
                
                if created:
                    criados += 1
                    
            except Exception as e:
                erros.append(f'Erro ao processar {nome}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'CSV processado: {criados} convênios criados',
            'data': {
                'criados': criados,
                'erros': erros,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao processar CSV: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["GET"])
def api_get_operacoes(request):
    """API GET para listar todas as operações"""
    try:
        operacoes = Operacao.objects.all().order_by('nome')
        data = [{
            'id': operacao.id,
            'nome': operacao.nome,
            'codigo': operacao.codigo or '',
            'status': operacao.status,
            'data_criacao': operacao.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for operacao in operacoes]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar operações: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_criar_operacao(request):
    """API POST para criar operação"""
    try:
        nome = request.POST.get('nome', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        operacao = Operacao.objects.create(
            nome=nome,
            codigo=codigo if codigo else None,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Operação criada com sucesso!',
            'data': {
                'id': operacao.id,
                'nome': operacao.nome,
                'codigo': operacao.codigo or '',
                'status': operacao.status,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar operação: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_importar_operacoes_csv(request):
    """API POST para importar operações em lote via CSV"""
    try:
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Arquivo CSV é obrigatório'})
        
        arquivo = request.FILES['arquivo']
        file_content = arquivo.read().decode('utf-8-sig')  # utf-8-sig remove BOM se existir
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=';')
        
        criados = 0
        erros = []
        
        for row in csv_reader:
            try:
                nome = row.get('nome', '').strip()
                if not nome:
                    continue
                
                codigo = row.get('codigo', '').strip()
                
                operacao, created = Operacao.objects.get_or_create(
                    nome=nome,
                    defaults={'codigo': codigo if codigo else None, 'status': True}
                )
                
                if created:
                    criados += 1
                    
            except Exception as e:
                erros.append(f'Erro ao processar {nome}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'CSV processado: {criados} operações criadas',
            'data': {
                'criados': criados,
                'erros': erros,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao processar CSV: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["GET", "POST"])
def api_editar_banco(request, banco_id):
    """API para editar banco"""
    try:
        banco = Banco.objects.get(id=banco_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': banco.id,
                    'nome': banco.nome,
                    'codigo': banco.codigo or '',
                    'status': banco.status,
                }
            })
        
        nome = request.POST.get('nome', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        banco.nome = nome
        banco.codigo = codigo if codigo else None
        banco.status = status
        banco.save()
        
        return JsonResponse({'success': True, 'message': 'Banco atualizado com sucesso!'})
    except Banco.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Banco não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar banco: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_deletar_banco(request, banco_id):
    """API POST para deletar banco"""
    try:
        banco = Banco.objects.get(id=banco_id)
        
        # Verificar se há associações
        associacoes_count = BancoConvenio.objects.filter(banco=banco).count()
        if associacoes_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'Não é possível deletar o banco. Existem {associacoes_count} associação(ões) vinculada(s).'
            }, status=400)
        
        banco.delete()
        return JsonResponse({'success': True, 'message': 'Banco deletado com sucesso!'})
    except Banco.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Banco não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar banco: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["GET", "POST"])
def api_editar_convenio(request, convenio_id):
    """API para editar convênio"""
    try:
        convenio = Convenio.objects.get(id=convenio_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': convenio.id,
                    'nome': convenio.nome,
                    'codigo': convenio.codigo or '',
                    'status': convenio.status,
                }
            })
        
        nome = request.POST.get('nome', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        convenio.nome = nome
        convenio.codigo = codigo if codigo else None
        convenio.status = status
        convenio.save()
        
        return JsonResponse({'success': True, 'message': 'Convênio atualizado com sucesso!'})
    except Convenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar convênio: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_deletar_convenio(request, convenio_id):
    """API POST para deletar convênio"""
    try:
        convenio = Convenio.objects.get(id=convenio_id)
        
        # Verificar se há associações
        associacoes_count = BancoConvenio.objects.filter(convenio=convenio).count() + ConvenioOperacao.objects.filter(convenio=convenio).count()
        if associacoes_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'Não é possível deletar o convênio. Existem {associacoes_count} associação(ões) vinculada(s).'
            }, status=400)
        
        convenio.delete()
        return JsonResponse({'success': True, 'message': 'Convênio deletado com sucesso!'})
    except Convenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar convênio: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["GET", "POST"])
def api_editar_operacao(request, operacao_id):
    """API para editar operação"""
    try:
        operacao = Operacao.objects.get(id=operacao_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': operacao.id,
                    'nome': operacao.nome,
                    'codigo': operacao.codigo or '',
                    'status': operacao.status,
                }
            })
        
        nome = request.POST.get('nome', '').strip()
        codigo = request.POST.get('codigo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        operacao.nome = nome
        operacao.codigo = codigo if codigo else None
        operacao.status = status
        operacao.save()
        
        return JsonResponse({'success': True, 'message': 'Operação atualizada com sucesso!'})
    except Operacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Operação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar operação: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_deletar_operacao(request, operacao_id):
    """API POST para deletar operação"""
    try:
        operacao = Operacao.objects.get(id=operacao_id)
        
        # Verificar se há associações
        associacoes_count = ConvenioOperacao.objects.filter(operacao=operacao).count()
        if associacoes_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'Não é possível deletar a operação. Existem {associacoes_count} associação(ões) vinculada(s).'
            }, status=400)
        
        operacao.delete()
        return JsonResponse({'success': True, 'message': 'Operação deletada com sucesso!'})
    except Operacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Operação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar operação: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["GET"])
def api_get_bancos_convenios(request):
    """API GET para listar associações Banco-Convênio"""
    try:
        associacoes = BancoConvenio.objects.all().select_related('banco', 'convenio').order_by('banco__nome', 'convenio__nome')
        data = [{
            'id': bc.id,
            'banco_id': bc.banco.id,
            'banco_nome': bc.banco.nome,
            'convenio_id': bc.convenio.id,
            'convenio_nome': bc.convenio.nome,
            'ativo': bc.ativo,
            'data_ativacao': bc.data_ativacao.strftime('%d/%m/%Y %H:%M') if bc.data_ativacao else None,
        } for bc in associacoes]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar associações: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_associar_banco_convenio(request):
    """API POST para associar banco a convênio"""
    try:
        banco_id = request.POST.get('banco_id')
        convenio_id = request.POST.get('convenio_id')
        
        if not banco_id or not convenio_id:
            return JsonResponse({'success': False, 'message': 'banco_id e convenio_id são obrigatórios'})
        
        banco = Banco.objects.get(id=banco_id)
        convenio = Convenio.objects.get(id=convenio_id)
        
        bc, created = BancoConvenio.objects.get_or_create(
            banco=banco,
            convenio=convenio,
            defaults={'ativo': False}
        )
        
        if created:
            return JsonResponse({'success': True, 'message': 'Associação criada com sucesso!', 'data': {'id': bc.id}})
        else:
            return JsonResponse({'success': False, 'message': 'Associação já existe'}, status=400)
    except Banco.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Banco não encontrado'}, status=404)
    except Convenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao associar: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_desassociar_banco_convenio(request, banco_convenio_id):
    """API POST para remover associação banco-convênio"""
    try:
        bc = BancoConvenio.objects.get(id=banco_convenio_id)
        bc.delete()
        return JsonResponse({'success': True, 'message': 'Associação removida com sucesso!'})
    except BancoConvenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Associação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao remover associação: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_ativar_banco_convenio(request, banco_convenio_id):
    """API POST para ativar/desativar associação banco-convênio"""
    try:
        bc = BancoConvenio.objects.get(id=banco_convenio_id)
        ativo = request.POST.get('ativo', 'true').lower() == 'true'
        bc.ativo = ativo
        bc.save()
        
        status_text = 'ativada' if ativo else 'desativada'
        return JsonResponse({'success': True, 'message': f'Associação {status_text} com sucesso!', 'data': {'ativo': bc.ativo}})
    except BancoConvenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Associação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar associação: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["GET"])
def api_get_convenios_operacoes(request):
    """API GET para listar schemas (ConvenioOperacao)"""
    try:
        schemas = ConvenioOperacao.objects.all().select_related('convenio', 'operacao').order_by('convenio__nome', 'operacao__nome')
        data = [{
            'id': co.id,
            'titulo': co.titulo or f'{co.convenio.nome} - {co.operacao.nome}',
            'convenio_id': co.convenio.id,
            'convenio_nome': co.convenio.nome,
            'operacao_id': co.operacao.id,
            'operacao_nome': co.operacao.nome,
            'data_criacao': co.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for co in schemas]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar schemas: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_associar_convenio_operacao(request):
    """API POST para criar schema (ConvenioOperacao)"""
    try:
        convenio_id = request.POST.get('convenio_id')
        operacao_id = request.POST.get('operacao_id')
        titulo = request.POST.get('titulo', '').strip()
        
        if not convenio_id or not operacao_id:
            return JsonResponse({'success': False, 'message': 'convenio_id e operacao_id são obrigatórios'})
        
        convenio = Convenio.objects.get(id=convenio_id)
        operacao = Operacao.objects.get(id=operacao_id)
        
        # Criar novo schema (agora permite múltiplos por convênio+operação)
        co = ConvenioOperacao.objects.create(
            convenio=convenio,
            operacao=operacao,
            titulo=titulo if titulo else None
        )
        
        return JsonResponse({'success': True, 'message': 'Schema criado com sucesso!', 'data': {'id': co.id}})
    except Convenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio não encontrado'}, status=404)
    except Operacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Operação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar schema: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_desassociar_convenio_operacao(request, convenio_operacao_id):
    """API POST para remover associação convênio-operação"""
    try:
        co = ConvenioOperacao.objects.get(id=convenio_operacao_id)
        co.delete()
        return JsonResponse({'success': True, 'message': 'Associação removida com sucesso!'})
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Associação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao remover associação: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_ativar_convenio_operacao(request, convenio_operacao_id):
    """API POST para atualizar título do schema (ConvenioOperacao)
    
    NOTA: A ativação de schemas agora é feita por banco via BancoConvenioOperacao.
    Use a API api_post_ativar_banco_convenio_operacao em gerenciar.py
    """
    try:
        co = ConvenioOperacao.objects.get(id=convenio_operacao_id)
        titulo = request.POST.get('titulo', '').strip()
        
        if titulo:
            co.titulo = titulo
            co.save()
        
        return JsonResponse({'success': True, 'message': 'Schema atualizado com sucesso!'})
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Schema não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar schema: {str(e)}'}, status=500)
