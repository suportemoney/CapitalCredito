"""
APIs para contratos (CRUD, kanban, anexos, SSE)
"""
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
import time
import os
# from apps.seguranca.permissoes.decorators import controle_acess  # Permissão será configurada depois
from apps.operacional.contratos.models import (
    ContratoOperacional, TabulacaoContrato, AnexoContrato,
    Banco, ConvenioOperacao
)
import json

# Configurações do SSE
SSE_CACHE_KEY = 'contratos_sse_last_update'
SSE_TIMEOUT = 30  # segundos

@login_required
@require_http_methods(["GET"])
def api_get_kanban(request):
    """API GET para retornar contratos organizados por tabulação (modo CRM)"""
    try:
        # Vendedor vê apenas seus contratos, operacional vê todos
        # Filtrar apenas contratos finalizados (não rascunhos)
        if request.user.is_superuser or hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL':
            contratos = ContratoOperacional.objects.filter(is_rascunho=False)
        else:
            contratos = ContratoOperacional.objects.filter(vendedor=request.user, is_rascunho=False)
        
        tabulacoes = TabulacaoContrato.objects.filter(status=True).order_by('ordem')
        
        data = {}
        for tab in tabulacoes:
            contratos_tab = contratos.filter(status_tabulacao=tab)
            data[tab.id] = {
                'id': tab.id,
                'nome': tab.nome,
                'cor': tab.cor,
                'ordem': tab.ordem,
                'contratos': [{
                    'id': contrato.id,
                    'numero_serie': contrato.numero_serie,
                    'cliente_nome': contrato.dados_contrato.get('dados_pessoais', {}).get('nome_completo', '') or contrato.dados_contrato.get('dados_pessoais', {}).get('nome', 'N/A') if isinstance(contrato.dados_contrato, dict) else 'N/A',
                    'banco_nome': contrato.banco.nome,
                    'convenio_nome': contrato.convenio_operacao.convenio.nome,
                    'operacao_nome': contrato.convenio_operacao.operacao.nome,
                    'vendedor_nome': contrato.vendedor.get_full_name() or contrato.vendedor.username,
                    'valor_operacao': contrato.dados_contrato.get('operacao', {}).get('valor_operacao', 'N/A') if isinstance(contrato.dados_contrato, dict) else 'N/A',
                    'link_formalizacao': contrato.link_formalizacao or '',
                    'cliente_formalizou': contrato.cliente_formalizou,
                    'observacoes_incompleto': contrato.observacoes_incompleto or '',
                    'video_cliente': contrato.video_cliente.url if contrato.video_cliente else None,
                    'tabulacao_id': tab.id,
                    'tabulacao_nome': tab.nome,
                    'tabulacao_cor': tab.cor,
                    'data_criacao': contrato.data_criacao.strftime('%d/%m/%Y %H:%M'),
                } for contrato in contratos_tab]
            }
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar kanban: {str(e)}'}, status=500)

@login_required
@require_http_methods(["GET"])
def api_get_contratos_tabela(request):
    """API GET para retornar contratos em formato de tabela (modo tabela)"""
    try:
        # Apenas operacional vê todos
        # Filtrar apenas contratos finalizados (não rascunhos)
        contratos = ContratoOperacional.objects.filter(is_rascunho=False)
        
        # Filtros
        banco_id = request.GET.get('banco_id')
        convenio_id = request.GET.get('convenio_id')
        operacao_id = request.GET.get('operacao_id')
        vendedor_id = request.GET.get('vendedor_id')
        tabulacao_id = request.GET.get('tabulacao_id')
        
        if banco_id:
            contratos = contratos.filter(banco_id=banco_id)
        if convenio_id:
            contratos = contratos.filter(convenio_operacao__convenio_id=convenio_id)
        if operacao_id:
            contratos = contratos.filter(convenio_operacao__operacao_id=operacao_id)
        if vendedor_id:
            contratos = contratos.filter(vendedor_id=vendedor_id)
        if tabulacao_id:
            contratos = contratos.filter(status_tabulacao_id=tabulacao_id)
        
        contratos = contratos.select_related('banco', 'convenio_operacao', 'vendedor', 'status_tabulacao').order_by('-data_criacao')
        
        data = [{
            'id': contrato.id,
            'numero_serie': contrato.numero_serie,
            'cliente_nome': contrato.dados_contrato.get('dados_pessoais', {}).get('nome_completo', '') or contrato.dados_contrato.get('dados_pessoais', {}).get('nome', 'N/A') if isinstance(contrato.dados_contrato, dict) else 'N/A',
            'cpf': contrato.dados_contrato.get('dados_pessoais', {}).get('cpf', '') if isinstance(contrato.dados_contrato, dict) else '',
            'banco_nome': contrato.banco.nome,
            'convenio_nome': contrato.convenio_operacao.convenio.nome,
            'operacao_nome': contrato.convenio_operacao.operacao.nome,
            'vendedor': contrato.vendedor.get_full_name() or contrato.vendedor.username,
            'tabulacao_id': contrato.status_tabulacao.id,
            'tabulacao_nome': contrato.status_tabulacao.nome,
            'tabulacao_cor': contrato.status_tabulacao.cor,
            'link_formalizacao': contrato.link_formalizacao or '',
            'observacoes_incompleto': contrato.observacoes_incompleto or '',
            'video_cliente': contrato.video_cliente.url if contrato.video_cliente else None,
            'data_criacao': contrato.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for contrato in contratos]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar contratos: {str(e)}'}, status=500)

@login_required
@require_http_methods(["GET"])
def api_get_contrato(request, contrato_id):
    """API GET para retalhar detalhes de um contrato"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Verificar permissão: vendedor só vê seus próprios contratos
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        cliente_nome = contrato.dados_contrato.get('dados_pessoais', {}).get('nome_completo', '') or contrato.dados_contrato.get('dados_pessoais', {}).get('nome', 'N/A') if isinstance(contrato.dados_contrato, dict) else 'N/A'
        data = {
            'id': contrato.id,
            'numero_serie': contrato.numero_serie,
            'cliente_nome': cliente_nome,
            'banco_id': contrato.banco.id,
            'banco_nome': contrato.banco.nome,
            'convenio_operacao_id': contrato.convenio_operacao.id,
            'convenio_nome': contrato.convenio_operacao.convenio.nome,
            'operacao_nome': contrato.convenio_operacao.operacao.nome,
            'vendedor_id': contrato.vendedor.id,
            'vendedor_nome': contrato.vendedor.get_full_name() or contrato.vendedor.username,
            'operador_id': contrato.operador.id if contrato.operador else None,
            'operador_nome': contrato.operador.get_full_name() or contrato.operador.username if contrato.operador else None,
            'status_tabulacao_id': contrato.status_tabulacao.id,
            'status_tabulacao': contrato.status_tabulacao.nome,
            'status_tabulacao_cor': contrato.status_tabulacao.cor,
            'dados_contrato': contrato.dados_contrato,
            'link_formalizacao': contrato.link_formalizacao or '',
            'cliente_formalizou': contrato.cliente_formalizou,
            'observacoes_incompleto': contrato.observacoes_incompleto or '',
            'video_cliente': contrato.video_cliente.url if contrato.video_cliente else '',
            'data_formalizacao': contrato.data_formalizacao.strftime('%d/%m/%Y %H:%M') if contrato.data_formalizacao else None,
            'data_liberacao': contrato.data_liberacao.strftime('%d/%m/%Y %H:%M') if contrato.data_liberacao else None,
            'data_pagamento': contrato.data_pagamento.strftime('%d/%m/%Y %H:%M') if contrato.data_pagamento else None,
            'observacoes': contrato.observacoes or '',
            'data_criacao': contrato.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'data_atualizacao': contrato.data_atualizacao.strftime('%d/%m/%Y %H:%M'),
        }
        
        return JsonResponse({'success': True, 'data': data})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar contrato: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_novo_contrato(request):
    """API POST para criar novo contrato"""
    try:
        from django.core.files.storage import default_storage
        import os
        
        # Aceitar tanto JSON quanto FormData
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            banco_id = data.get('banco_id')
            convenio_operacao_id = data.get('convenio_operacao_id')
            dados_contrato = data.get('dados_contrato', {})
        else:
            banco_id = request.POST.get('banco_id')
            convenio_operacao_id = request.POST.get('convenio_operacao_id')
            dados_contrato = {}
            import re
            for key, value in request.POST.items():
                if key not in ['banco_id', 'convenio_operacao_id', 'csrfmiddlewaretoken']:
                    if '__' in key:
                        category, field = key.split('__', 1)
                        # Ignorar fakepaths
                        valor_str = str(value) if value else ''
                        if 'fakepath' in valor_str.lower() or re.match(r'^[A-Z]:\\', valor_str, re.IGNORECASE):
                            print(f"[DEBUG] Removendo fakepath de {category}.{field}: {valor_str}")
                            continue
                        
                        if category not in dados_contrato:
                            dados_contrato[category] = {}
                        dados_contrato[category][field] = value
        
        # Remover fakepaths dos dados JSON também
        if isinstance(dados_contrato, dict):
            import re
            dados_limpos = {}
            for categoria, campos in dados_contrato.items():
                if isinstance(campos, dict):
                    campos_limpos = {}
                    for campo, valor in campos.items():
                        valor_str = str(valor) if valor else ''
                        if 'fakepath' in valor_str.lower() or re.match(r'^[A-Z]:\\', valor_str, re.IGNORECASE):
                            print(f"[DEBUG] Removendo fakepath de {categoria}.{campo}: {valor_str}")
                            continue
                        campos_limpos[campo] = valor
                    dados_limpos[categoria] = campos_limpos
                else:
                    dados_limpos[categoria] = campos
            dados_contrato = dados_limpos
        
        if not banco_id or not convenio_operacao_id:
            return JsonResponse({'success': False, 'message': 'banco_id e convenio_operacao_id são obrigatórios'}, status=400)
        
        banco = Banco.objects.get(id=banco_id)
        convenio_operacao = ConvenioOperacao.objects.get(id=convenio_operacao_id)
        
        # Buscar primeira tabulação (Enviado)
        tabulacao_inicial = TabulacaoContrato.objects.filter(status=True).order_by('ordem').first()
        if not tabulacao_inicial:
            return JsonResponse({'success': False, 'message': 'Nenhuma tabulação encontrada'}, status=400)
        
        contrato = ContratoOperacional.objects.create(
            banco=banco,
            convenio_operacao=convenio_operacao,
            vendedor=request.user,
            status_tabulacao=tabulacao_inicial,
            dados_contrato=dados_contrato,
        )
        
        # Processar arquivos enviados
        for key, file in request.FILES.items():
            if '__' in key:
                category, field = key.split('__', 1)
                if category not in contrato.dados_contrato:
                    contrato.dados_contrato[category] = {}
                
                # Criar diretório para o contrato
                file_dir = f'contratos/{contrato.id}/documentos/'
                file_name = f'{field}_{file.name}'
                file_path = os.path.join(file_dir, file_name)
                
                # Salvar arquivo
                saved_path = default_storage.save(file_path, file)
                contrato.dados_contrato[category][field] = f'/media/{saved_path}'
        
        # Salvar contrato se houve arquivos
        if request.FILES:
            contrato.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Contrato criado com sucesso!',
            'data': {'id': contrato.id}
        })
    except Banco.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Banco não encontrado'}, status=404)
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio+Operação não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar contrato: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_mover_contrato(request):
    """API POST para mover contrato entre tabulações"""
    try:
        # Aceitar tanto JSON quanto FormData
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            contrato_id = data.get('contrato_id') or data.get('contratoId')
            nova_tabulacao_id = data.get('nova_tabulacao_id') or data.get('tabulacao_id')
        else:
            contrato_id = request.POST.get('contrato_id')
            nova_tabulacao_id = request.POST.get('nova_tabulacao_id') or request.POST.get('tabulacao_id')
        
        if not contrato_id or not nova_tabulacao_id:
            return JsonResponse({'success': False, 'message': 'contrato_id e nova_tabulacao_id são obrigatórios'}, status=400)
        
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        tabulacao = TabulacaoContrato.objects.get(id=nova_tabulacao_id)
        
        # Verificar permissão: vendedor só pode mover seus próprios contratos e apenas algumas transições
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        contrato.status_tabulacao = tabulacao
        contrato.save()
        
        return JsonResponse({'success': True, 'message': 'Contrato movido com sucesso!'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except TabulacaoContrato.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tabulação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao mover contrato: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_mover_contratos_massa(request):
    """API POST para mover múltiplos contratos entre tabulações (apenas OPERACIONAL)"""
    try:
        # Aceitar tanto JSON quanto FormData
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            contrato_ids = data.get('contrato_ids', [])
            nova_tabulacao_id = data.get('nova_tabulacao_id') or data.get('tabulacao_id')
        else:
            contrato_ids = request.POST.getlist('contrato_ids[]')
            nova_tabulacao_id = request.POST.get('nova_tabulacao_id') or request.POST.get('tabulacao_id')
        
        if not contrato_ids or not nova_tabulacao_id:
            return JsonResponse({'success': False, 'message': 'contrato_ids e nova_tabulacao_id são obrigatórios'}, status=400)
        
        # Apenas operacional pode mover em massa
        if not request.user.is_superuser:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        tabulacao = TabulacaoContrato.objects.get(id=nova_tabulacao_id)
        contratos = ContratoOperacional.objects.filter(id__in=contrato_ids)
        
        atualizados = 0
        for contrato in contratos:
            contrato.status_tabulacao = tabulacao
            contrato.save()
            atualizados += 1
        
        return JsonResponse({'success': True, 'message': f'{atualizados} contrato(s) movido(s) com sucesso!'})
    except TabulacaoContrato.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tabulação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao mover contratos: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_atualizar_contrato(request, contrato_id):
    """API POST para atualizar dados do contrato (edição de incompleto)"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Verificar permissão
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        # Verificar se veio dados_contrato como JSON string
        dados_json = request.POST.get('dados_contrato')
        finalizar = request.POST.get('finalizar', 'false').lower() == 'true'
        
        # Remover fakepaths antes do merge
        import re
        
        if dados_json:
            # Formato novo - JSON com dados completos
            novos_dados = json.loads(dados_json)
            
            # Remover fakepaths dos novos dados
            novos_dados_limpos = {}
            for categoria, campos in novos_dados.items():
                if isinstance(campos, dict):
                    campos_limpos = {}
                    for campo, valor in campos.items():
                        valor_str = str(valor) if valor else ''
                        # Ignorar fakepaths
                        if 'fakepath' in valor_str.lower() or re.match(r'^[A-Z]:\\', valor_str, re.IGNORECASE):
                            print(f"[DEBUG] Removendo fakepath de {categoria}.{campo}: {valor_str}")
                            continue
                        campos_limpos[campo] = valor
                    novos_dados_limpos[categoria] = campos_limpos
                else:
                    novos_dados_limpos[categoria] = campos
            
            # Mesclar com dados existentes (preservar arquivos já salvos)
            dados_contrato = contrato.dados_contrato.copy() if isinstance(contrato.dados_contrato, dict) else {}
            
            for categoria, campos in novos_dados_limpos.items():
                if categoria not in dados_contrato:
                    dados_contrato[categoria] = {}
                if isinstance(campos, dict):
                    for campo, valor in campos.items():
                        # Não sobrescrever arquivos existentes (que começam com /media/)
                        if campo in dados_contrato[categoria] and isinstance(dados_contrato[categoria][campo], str):
                            if dados_contrato[categoria][campo].startswith('/media/'):
                                # Manter arquivo existente se o novo valor não é uma URL válida
                                if not (valor and isinstance(valor, str) and valor.startswith('/media/')):
                                    continue  # Manter arquivo existente
                        dados_contrato[categoria][campo] = valor
            
            contrato.dados_contrato = dados_contrato
        else:
            # Formato antigo - campos individuais no POST
            dados_contrato = contrato.dados_contrato.copy() if isinstance(contrato.dados_contrato, dict) else {}
            
            for key, value in request.POST.items():
                if key not in ['csrfmiddlewaretoken', 'dados_contrato', 'finalizar']:
                    if '__' in key:
                        category, field = key.split('__', 1)
                        # Ignorar fakepaths
                        valor_str = str(value) if value else ''
                        if 'fakepath' in valor_str.lower() or re.match(r'^[A-Z]:\\', valor_str, re.IGNORECASE):
                            print(f"[DEBUG] Removendo fakepath de {category}.{field}: {valor_str}")
                            continue
                        
                        if category not in dados_contrato:
                            dados_contrato[category] = {}
                        dados_contrato[category][field] = value
            
            contrato.dados_contrato = dados_contrato
        
        # Processar arquivos enviados (sobrescrevem valores antigos)
        if request.FILES:
            if not isinstance(contrato.dados_contrato, dict):
                contrato.dados_contrato = {}
            
            for key, file in request.FILES.items():
                if '__' in key:
                    category, field = key.split('__', 1)
                    if category not in contrato.dados_contrato:
                        contrato.dados_contrato[category] = {}
                    
                    # Salvar arquivo
                    from django.core.files.storage import default_storage
                    import os
                    
                    # Criar diretório para o contrato
                    file_dir = f'contratos/{contrato.id}/documentos/'
                    file_name = f'{field}_{file.name}'
                    file_path = os.path.join(file_dir, file_name)
                    
                    # Deletar arquivo antigo se existir
                    if field in contrato.dados_contrato[category]:
                        url_antiga = contrato.dados_contrato[category][field]
                        if url_antiga and url_antiga.startswith('/media/'):
                            try:
                                path_antigo = url_antiga.replace('/media/', '')
                                if default_storage.exists(path_antigo):
                                    default_storage.delete(path_antigo)
                                    print(f"[DEBUG] Arquivo antigo deletado: {path_antigo}")
                            except Exception as e:
                                print(f"[DEBUG] Erro ao deletar arquivo antigo: {e}")
                    
                    # Salvar novo arquivo
                    saved_path = default_storage.save(file_path, file)
                    contrato.dados_contrato[category][field] = f'/media/{saved_path}'
                    print(f"[DEBUG] Arquivo salvo: {contrato.dados_contrato[category][field]}")
        
        # Se finalizar, mover para CONTRATOS ENVIADOS
        if finalizar:
            try:
                tabulacao_enviados = TabulacaoContrato.objects.get(nome__iexact='CONTRATOS ENVIADOS')
                contrato.status_tabulacao = tabulacao_enviados
                contrato.observacoes_incompleto = None  # Limpar observações de incompleto
                contrato.is_rascunho = False
            except TabulacaoContrato.DoesNotExist:
                pass  # Se não encontrar a tabulação, mantém a atual
        
        contrato.save()
        
        mensagem = 'Contrato atualizado e reenviado para análise!' if finalizar else 'Contrato atualizado com sucesso!'
        return JsonResponse({'success': True, 'message': mensagem})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Erro ao processar dados JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar contrato: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_atualizar_link_formalizacao(request, contrato_id):
    """API POST para atualizar link de formalização (apenas OPERACIONAL)"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Apenas operacional pode atualizar link
        if not request.user.is_superuser:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        link_formalizacao = request.POST.get('link_formalizacao', '').strip()
        contrato.link_formalizacao = link_formalizacao if link_formalizacao else None
        contrato.save()
        
        return JsonResponse({'success': True, 'message': 'Link de formalização atualizado com sucesso!'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar link: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_cliente_formalizou(request, contrato_id):
    """API POST para vendedor informar que cliente formalizou"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Apenas o vendedor do contrato pode informar
        if not request.user.is_superuser and contrato.vendedor != request.user:
            return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        cliente_formalizou = request.POST.get('cliente_formalizou', 'false').lower() == 'true'
        contrato.cliente_formalizou = cliente_formalizou
        
        if cliente_formalizou and not contrato.data_formalizacao:
            contrato.data_formalizacao = timezone.now()
        
        contrato.save()
        
        status_text = 'formalizou' if cliente_formalizou else 'não formalizou'
        return JsonResponse({'success': True, 'message': f'Informação atualizada: cliente {status_text}'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar: {str(e)}'}, status=500)

@login_required
@require_http_methods(["GET"])
def api_get_anexos_contrato(request, contrato_id):
    """API GET para listar anexos de um contrato"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Verificar permissão
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        anexos = AnexoContrato.objects.filter(contrato=contrato).order_by('-data_criacao')
        data = [{
            'id': anexo.id,
            'titulo': anexo.titulo or anexo.arquivo.name,
            'tipo_documento': anexo.tipo_documento or '',
            'arquivo_url': anexo.arquivo.url,
            'data_criacao': anexo.data_criacao.strftime('%d/%m/%Y %H:%M'),
        } for anexo in anexos]
        
        return JsonResponse({'success': True, 'data': data})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar anexos: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_upload_anexo(request, contrato_id):
    """API POST para fazer upload de anexo ao contrato"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Verificar permissão
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Arquivo é obrigatório'})
        
        arquivo = request.FILES['arquivo']
        titulo = request.POST.get('titulo', '').strip()
        tipo_documento = request.POST.get('tipo_documento', '').strip()
        
        anexo = AnexoContrato.objects.create(
            contrato=contrato,
            arquivo=arquivo,
            titulo=titulo if titulo else None,
            tipo_documento=tipo_documento if tipo_documento else None,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Anexo enviado com sucesso!',
            'data': {
                'id': anexo.id,
                'titulo': anexo.titulo or anexo.arquivo.name,
                'arquivo_url': anexo.arquivo.url,
            }
        })
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao enviar anexo: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_post_deletar_anexo(request, anexo_id):
    """API POST para deletar anexo"""
    try:
        anexo = AnexoContrato.objects.get(id=anexo_id)
        contrato = anexo.contrato
        
        # Verificar permissão
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        anexo.delete()
        return JsonResponse({'success': True, 'message': 'Anexo deletado com sucesso!'})
    except AnexoContrato.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Anexo não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar anexo: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_post_salvar_pagina(request):
    """API POST para salvar página do contrato (sistema de rascunho/wizard)
    
    Fluxo:
    1. Primeira página: cria contrato como rascunho
    2. Páginas intermediárias: atualiza rascunho
    3. Última página: finaliza contrato (is_rascunho=False)
    """
    try:
        from django.core.files.storage import default_storage
        import os
        
        print(f"\n{'#'*80}")
        print(f"[DEBUG api_post_salvar_pagina] ========== INÍCIO DA REQUISIÇÃO ==========")
        print(f"[DEBUG api_post_salvar_pagina] request.method: {request.method}")
        print(f"[DEBUG api_post_salvar_pagina] request.content_type: {request.content_type}")
        print(f"[DEBUG api_post_salvar_pagina] request.user: {request.user}")
        print(f"[DEBUG api_post_salvar_pagina] {'#'*80}\n")
        
        # Aceitar JSON ou FormData
        if request.content_type == 'application/json':
            print(f"[DEBUG api_post_salvar_pagina] Processando como JSON")
            data = json.loads(request.body)
        else:
            print(f"[DEBUG api_post_salvar_pagina] Processando como FormData/Multipart")
            data = request.POST.dict()
            print(f"[DEBUG api_post_salvar_pagina] request.POST keys: {list(data.keys())}")
            # Converter dados_pagina de string para dict se necessário
            if 'dados_pagina' in data and isinstance(data['dados_pagina'], str):
                data['dados_pagina'] = json.loads(data['dados_pagina'])
        
        contrato_id = data.get('contrato_id')  # None se é primeira página
        banco_id = data.get('banco_id')
        convenio_operacao_id = data.get('convenio_operacao_id')
        pagina_atual = int(data.get('pagina_atual', 1))
        total_paginas = int(data.get('total_paginas', 1))
        dados_pagina = data.get('dados_pagina', {})
        
        print(f"[DEBUG api_post_salvar_pagina] contrato_id: {contrato_id}")
        print(f"[DEBUG api_post_salvar_pagina] banco_id: {banco_id}")
        print(f"[DEBUG api_post_salvar_pagina] convenio_operacao_id: {convenio_operacao_id}")
        print(f"[DEBUG api_post_salvar_pagina] pagina_atual: {pagina_atual}")
        print(f"[DEBUG api_post_salvar_pagina] total_paginas: {total_paginas}")
        print(f"[DEBUG api_post_salvar_pagina] dados_pagina keys: {list(dados_pagina.keys()) if isinstance(dados_pagina, dict) else 'NÃO É DICT'}")
        
        # Remover campos de arquivo dos dados_pagina que contêm fakepath ANTES do merge
        import re
        dados_pagina_limpo = {}
        for categoria, campos in dados_pagina.items():
            if isinstance(campos, dict):
                campos_limpos = {}
                for campo, valor in campos.items():
                    # Se o valor é uma string com fakepath ou caminho Windows, ignorar
                    valor_str = str(valor) if valor else ''
                    if 'fakepath' in valor_str.lower() or re.match(r'^[A-Z]:\\', valor_str, re.IGNORECASE):
                        print(f"[DEBUG] Removendo fakepath de {categoria}.{campo}: {valor_str}")
                        continue  # Não incluir no merge - será substituído pelo arquivo processado
                    campos_limpos[campo] = valor
                dados_pagina_limpo[categoria] = campos_limpos
            else:
                dados_pagina_limpo[categoria] = campos
        dados_pagina = dados_pagina_limpo
        
        if contrato_id:
            # Atualizar contrato existente (rascunho)
            contrato = ContratoOperacional.objects.get(id=contrato_id)
            
            # Verificar se pertence ao usuário
            if contrato.vendedor != request.user and not request.user.is_superuser:
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
            
            # Merge dos dados existentes com dados da página atual (sem fakepaths)
            dados_existentes = contrato.dados_contrato.copy() if isinstance(contrato.dados_contrato, dict) else {}
            for categoria, campos in dados_pagina.items():
                if categoria not in dados_existentes:
                    dados_existentes[categoria] = {}
                if isinstance(campos, dict):
                    for campo, valor in campos.items():
                        # Não sobrescrever arquivos existentes com strings vazias
                        if campo in dados_existentes.get(categoria, {}):
                            valor_existente = dados_existentes[categoria][campo]
                            # Se o valor existente é uma URL de arquivo e o novo valor é vazio, manter o existente
                            if isinstance(valor_existente, str) and valor_existente.startswith('/media/') and not valor:
                                print(f"[DEBUG] Preservando arquivo existente {categoria}.{campo}: {valor_existente}")
                                continue
                        dados_existentes[categoria][campo] = valor
                else:
                    dados_existentes[categoria] = campos
            
            contrato.dados_contrato = dados_existentes
        else:
            # Criar novo contrato (primeira página)
            if not banco_id or not convenio_operacao_id:
                return JsonResponse({
                    'success': False, 
                    'message': 'banco_id e convenio_operacao_id são obrigatórios na primeira página'
                }, status=400)
            
            banco = Banco.objects.get(id=banco_id)
            convenio_operacao = ConvenioOperacao.objects.get(id=convenio_operacao_id)
            
            # Buscar primeira tabulação
            tabulacao_inicial = TabulacaoContrato.objects.filter(status=True).order_by('ordem').first()
            if not tabulacao_inicial:
                return JsonResponse({'success': False, 'message': 'Nenhuma tabulação encontrada'}, status=400)
            
            contrato = ContratoOperacional(
                banco=banco,
                convenio_operacao=convenio_operacao,
                vendedor=request.user,
                status_tabulacao=tabulacao_inicial,
                dados_contrato=dados_pagina,
                is_rascunho=True,
                pagina_atual=pagina_atual,
            )
        
        # Verificar se está finalizando (pode vir como parâmetro ou ser última página)
        finalizar_param = data.get('finalizar', False)
        if isinstance(finalizar_param, str):
            finalizar_param = finalizar_param.lower() == 'true'
        
        # Verificar se é última página
        is_finalizar = finalizar_param or (pagina_atual >= total_paginas)
        
        if is_finalizar:
            # Finaliza o contrato
            contrato.is_rascunho = False
            contrato.pagina_atual = 0  # 0 indica completo
            mensagem = 'Contrato enviado com sucesso!'
        else:
            # Ainda é rascunho, avança para próxima página
            contrato.is_rascunho = True
            contrato.pagina_atual = pagina_atual + 1
            mensagem = f'Página {pagina_atual} salva! Avançando para página {pagina_atual + 1}.'
        
        # Salvar contrato primeiro para ter o ID (se novo)
        contrato.save()
        
        # IMPORTANTE: Processar arquivos APENAS quando finalizar o contrato
        print(f"[DEBUG api_post_salvar_pagina] is_finalizar: {is_finalizar}")
        print(f"[DEBUG api_post_salvar_pagina] request.FILES: {list(request.FILES.keys())}")
        print(f"[DEBUG api_post_salvar_pagina] Quantidade de arquivos: {len(request.FILES)}")
        print(f"[DEBUG api_post_salvar_pagina] Content-Type: {request.content_type}")
        print(f"[DEBUG api_post_salvar_pagina] Contrato ID: {contrato.id}")
        print(f"[DEBUG api_post_salvar_pagina] is_rascunho: {contrato.is_rascunho}")
        
        # Garantir que dados_contrato existe e é um dict
        if not isinstance(contrato.dados_contrato, dict):
            contrato.dados_contrato = {}
        
        dados_contrato = contrato.dados_contrato.copy()
        arquivos_processados = False
        arquivos_agrupados = {}
        
        # Processar arquivos SEMPRE que forem enviados (criar AnexoContrato e atualizar JSON)
        print(f"\n{'='*80}")
        print(f"[DEBUG api_post_salvar_pagina] ========== VERIFICANDO ARQUIVOS ==========")
        print(f"[DEBUG api_post_salvar_pagina] request.method: {request.method}")
        print(f"[DEBUG api_post_salvar_pagina] request.content_type: {request.content_type}")
        print(f"[DEBUG api_post_salvar_pagina] request.POST keys: {list(request.POST.keys())}")
        print(f"[DEBUG api_post_salvar_pagina] request.FILES: {request.FILES}")
        print(f"[DEBUG api_post_salvar_pagina] len(request.FILES): {len(request.FILES)}")
        print(f"[DEBUG api_post_salvar_pagina] request.FILES.keys(): {list(request.FILES.keys())}")
        
        # Detalhar cada arquivo recebido
        if request.FILES:
            print(f"[DEBUG api_post_salvar_pagina] 📁 ARQUIVOS RECEBIDOS ({len(request.FILES)}):")
            for key, file in request.FILES.items():
                print(f"[DEBUG api_post_salvar_pagina]   - key: '{key}'")
                print(f"[DEBUG api_post_salvar_pagina]     name: {file.name}")
                print(f"[DEBUG api_post_salvar_pagina]     size: {file.size} bytes")
                print(f"[DEBUG api_post_salvar_pagina]     content_type: {file.content_type}")
        else:
            print(f"[DEBUG api_post_salvar_pagina] ⚠️ NENHUM ARQUIVO RECEBIDO!")
        print(f"{'='*80}\n")
        
        if request.FILES:
            # Agrupar arquivos por categoria__campo (para tratar MULTIFILE)
            arquivos_agrupados = {}
            for key, file in request.FILES.items():
                print(f"[DEBUG api_post_salvar_pagina] Arquivo recebido: key={key}, file.name={file.name}, file.size={file.size}")
                if '__' in key:
                    if key not in arquivos_agrupados:
                        arquivos_agrupados[key] = []
                    arquivos_agrupados[key].append(file)
                else:
                    print(f"[DEBUG api_post_salvar_pagina] ⚠️ AVISO: Arquivo com key '{key}' não tem formato categoria__campo")
            
            # Processar arquivos agrupados
            for key, files in arquivos_agrupados.items():
                category, field = key.split('__', 1)
                if category not in dados_contrato:
                    dados_contrato[category] = {}
                
                print(f"[DEBUG api_post_salvar_pagina] Processando {len(files)} arquivo(s) para {category}.{field}")
                
                if len(files) == 1:
                    # FILE - arquivo único
                    file = files[0]
                    file_dir = f'contratos/{contrato.id}/documentos/'
                    file_name = f'{field}_{file.name}'
                    
                    try:
                        print(f"[DEBUG api_post_salvar_pagina] Tentando salvar arquivo único: {file.name} (size: {file.size})")
                        print(f"[DEBUG api_post_salvar_pagina] Contrato ID: {contrato.id}, file_name: {file_name}")
                        
                        # Criar registro AnexoContrato e salvar arquivo diretamente
                        anexo = AnexoContrato(
                            contrato=contrato,
                            titulo=f"{category} - {field}",
                            tipo_documento=field
                        )
                        # Salvar arquivo no campo arquivo do AnexoContrato
                        anexo.arquivo.save(file_name, file, save=False)
                        anexo.save()
                        
                        url_salva = f'/media/{anexo.arquivo.name}'
                        dados_contrato[category][field] = url_salva
                        arquivos_processados = True
                        print(f"[DEBUG api_post_salvar_pagina] ✅ Arquivo único salvo: {url_salva} (AnexoContrato ID: {anexo.id})")
                    except Exception as e:
                        import traceback
                        print(f"[DEBUG api_post_salvar_pagina] ❌ Erro ao salvar arquivo: {str(e)}")
                        print(f"[DEBUG api_post_salvar_pagina] Traceback: {traceback.format_exc()}")
                else:
                    # MULTIFILE - array de arquivos
                    urls_array = []
                    for idx, file in enumerate(files):
                        file_dir = f'contratos/{contrato.id}/documentos/'
                        file_name = f'{field}_{idx+1}_{file.name}'
                        
                        try:
                            print(f"[DEBUG api_post_salvar_pagina] Tentando salvar arquivo {idx+1}/{len(files)}: {file.name} (size: {file.size})")
                            print(f"[DEBUG api_post_salvar_pagina] Contrato ID: {contrato.id}, file_name: {file_name}")
                            
                            # Criar registro AnexoContrato e salvar arquivo diretamente
                            anexo = AnexoContrato(
                                contrato=contrato,
                                titulo=f"{category} - {field} ({idx+1})",
                                tipo_documento=field
                            )
                            # Salvar arquivo no campo arquivo do AnexoContrato
                            anexo.arquivo.save(file_name, file, save=False)
                            anexo.save()
                            
                            url_salva = f'/media/{anexo.arquivo.name}'
                            urls_array.append(url_salva)
                            arquivos_processados = True
                            print(f"[DEBUG api_post_salvar_pagina] ✅ Arquivo {idx+1}/{len(files)} salvo: {url_salva} (AnexoContrato ID: {anexo.id})")
                        except Exception as e:
                            import traceback
                            print(f"[DEBUG api_post_salvar_pagina] ❌ Erro ao salvar arquivo {idx+1}: {str(e)}")
                            print(f"[DEBUG api_post_salvar_pagina] Traceback: {traceback.format_exc()}")
                    
                    if urls_array:
                        dados_contrato[category][field] = urls_array
                        print(f"[DEBUG api_post_salvar_pagina] ✅ {len(urls_array)} arquivo(s) salvos em array para {category}.{field}")
            
            if arquivos_processados:
                # Atualizar dados do contrato com URLs dos arquivos
                contrato.dados_contrato = dados_contrato
                contrato.save(update_fields=['dados_contrato'])
                print(f"\n{'='*80}")
                print(f"[DEBUG api_post_salvar_pagina] ✅ dados_contrato atualizado com arquivos")
                print(f"[DEBUG api_post_salvar_pagina] === RESUMO DOS ARQUIVOS SALVOS ===")
                for categoria, campos in dados_contrato.items():
                    if isinstance(campos, dict):
                        for campo, valor in campos.items():
                            if isinstance(valor, str) and valor.startswith('/media/'):
                                print(f"  ✅ {categoria}.{campo} = {valor}")
                            elif isinstance(valor, list) and len(valor) > 0 and isinstance(valor[0], str) and valor[0].startswith('/media/'):
                                print(f"  ✅ {categoria}.{campo} = [{len(valor)} arquivo(s)]")
                                for url in valor:
                                    print(f"     - {url}")
                print(f"{'='*80}\n")
            else:
                print(f"\n{'='*80}")
                print(f"[DEBUG api_post_salvar_pagina] ⚠️ ATENÇÃO: Nenhum arquivo foi processado com sucesso")
                print(f"[DEBUG api_post_salvar_pagina] Total de arquivos recebidos: {len(request.FILES)}")
                print(f"[DEBUG api_post_salvar_pagina] Arquivos agrupados: {len(arquivos_agrupados)}")
                print(f"[DEBUG api_post_salvar_pagina] arquivos_agrupados: {arquivos_agrupados}")
                print(f"{'='*80}\n")
        else:
            print(f"\n{'='*80}")
            print(f"[DEBUG api_post_salvar_pagina] ℹ️ Nenhum arquivo enviado nesta requisição")
            print(f"[DEBUG api_post_salvar_pagina] Contrato ID: {contrato.id}")
            print(f"[DEBUG api_post_salvar_pagina] Página: {pagina_atual}/{total_paginas}")
            print(f"[DEBUG api_post_salvar_pagina] is_rascunho: {contrato.is_rascunho}")
            print(f"[DEBUG api_post_salvar_pagina] is_finalizar: {is_finalizar}")
            print(f"{'='*80}\n")
        
        response_data = {
            'success': True,
            'message': mensagem,
            'data': {
                'contrato_id': contrato.id,
                'is_rascunho': contrato.is_rascunho,
                'pagina_atual': contrato.pagina_atual,
                'proxima_pagina': contrato.pagina_atual if contrato.is_rascunho else None,
                'finalizado': not contrato.is_rascunho,
                'arquivos_processados': arquivos_processados,
                'total_arquivos_recebidos': len(request.FILES) if request.FILES else 0,
            }
        }
        
        print(f"\n{'='*80}")
        print(f"[DEBUG api_post_salvar_pagina] ========== RESPOSTA ==========")
        print(f"[DEBUG api_post_salvar_pagina] {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        print(f"{'='*80}\n")
        
        return JsonResponse(response_data)
    except Banco.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Banco não encontrado'}, status=404)
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio+Operação não encontrado'}, status=404)
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao salvar página: {str(e)}'}, status=500)


# ==================== APIS SSE ====================

def _notificar_atualizacao():
    """Notifica que houve atualização para os clientes SSE"""
    cache.set(SSE_CACHE_KEY, timezone.now().timestamp(), timeout=60)


@login_required
@require_http_methods(["GET"])
def api_sse_contratos(request):
    """API SSE para atualizações em tempo real dos contratos
    
    Mesmo padrão usado em apps/vendas/siape/
    """
    def event_stream():
        ultima_verificacao = time.time()
        
        # Enviar evento inicial com todos os contratos
        yield f"data: {json.dumps({'etapa': 'conectado', 'mensagem': 'Conexão SSE estabelecida'})}\n\n"
        
        while True:
            try:
                # Verificar se há atualizações no cache
                ultima_atualizacao = cache.get(SSE_CACHE_KEY, 0)
                
                if ultima_atualizacao > ultima_verificacao:
                    # Houve atualização, buscar dados
                    ultima_verificacao = time.time()
                    
                    # Buscar contratos atualizados recentemente (últimos 5 segundos)
                    limite = timezone.now() - timezone.timedelta(seconds=5)
                    
                    # Filtra por usuário se não for operacional/superuser
                    if request.user.is_superuser or (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                        contratos_atualizados = ContratoOperacional.objects.filter(
                            data_atualizacao__gte=limite,
                            is_rascunho=False
                        )
                    else:
                        contratos_atualizados = ContratoOperacional.objects.filter(
                            data_atualizacao__gte=limite,
                            vendedor=request.user,
                            is_rascunho=False
                        )
                    
                    for contrato in contratos_atualizados:
                        cliente_nome = contrato.dados_contrato.get('dados_pessoais', {}).get('nome', 'N/A') if isinstance(contrato.dados_contrato, dict) else 'N/A'
                        cpf = contrato.dados_contrato.get('dados_pessoais', {}).get('cpf', '') if isinstance(contrato.dados_contrato, dict) else ''
                        
                        dados = {
                            'etapa': 'atualizado',
                            'contrato': {
                                'id': contrato.id,
                                'cliente_nome': cliente_nome,
                                'cpf': cpf,
                                'banco_nome': contrato.banco.nome,
                                'convenio_nome': contrato.convenio_operacao.convenio.nome,
                                'operacao_nome': contrato.convenio_operacao.operacao.nome,
                                'vendedor_nome': contrato.vendedor.get_full_name() or contrato.vendedor.username,
                                'tabulacao_id': contrato.status_tabulacao.id,
                                'tabulacao_nome': contrato.status_tabulacao.nome,
                                'tabulacao_cor': contrato.status_tabulacao.cor,
                                'link_formalizacao': contrato.link_formalizacao or '',
                                'cliente_formalizou': contrato.cliente_formalizou,
                                'observacoes_incompleto': contrato.observacoes_incompleto or '',
                                'video_cliente': contrato.video_cliente.url if contrato.video_cliente else None,
                                'data_atualizacao': contrato.data_atualizacao.strftime('%d/%m/%Y %H:%M'),
                            }
                        }
                        yield f"data: {json.dumps(dados)}\n\n"
                
                # Heartbeat a cada 15 segundos para manter conexão ativa
                yield f"data: {json.dumps({'etapa': 'heartbeat', 'timestamp': time.time()})}\n\n"
                time.sleep(2)  # Verificar a cada 2 segundos
                
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'etapa': 'erro', 'mensagem': str(e)})}\n\n"
                break
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_http_methods(["GET"])
def api_get_tabulacoes(request):
    """API GET para listar todas as tabulações"""
    try:
        tabulacoes = TabulacaoContrato.objects.filter(status=True).order_by('ordem')
        data = [{
            'id': tab.id,
            'nome': tab.nome,
            'ordem': tab.ordem,
            'cor': tab.cor,
        } for tab in tabulacoes]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar tabulações: {str(e)}'}, status=500)


# ==================== APIS DE AÇÕES ESPECÍFICAS ====================

@login_required
@require_http_methods(["POST"])
def api_post_marcar_incompleto(request, contrato_id):
    """API POST para marcar contrato como incompleto com observações (apenas OPERACIONAL)"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Apenas operacional pode marcar como incompleto
        if not request.user.is_superuser:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        observacoes = request.POST.get('observacoes', '').strip()
        if not observacoes:
            return JsonResponse({'success': False, 'message': 'Observações são obrigatórias'}, status=400)
        
        # Buscar tabulação "INCOMPLETO"
        tabulacao_incompleto = TabulacaoContrato.objects.filter(nome__iexact='INCOMPLETO').first()
        if not tabulacao_incompleto:
            tabulacao_incompleto = TabulacaoContrato.objects.filter(ordem=2).first()
        
        if not tabulacao_incompleto:
            return JsonResponse({'success': False, 'message': 'Tabulação INCOMPLETO não encontrada'}, status=400)
        
        contrato.observacoes_incompleto = observacoes
        contrato.status_tabulacao = tabulacao_incompleto
        contrato.save()
        
        # Notificar SSE
        _notificar_atualizacao()
        
        return JsonResponse({'success': True, 'message': 'Contrato marcado como incompleto!'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_post_informar_link_formalizacao(request, contrato_id):
    """API POST para operacional informar link de formalização"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Apenas operacional pode informar link
        if not request.user.is_superuser:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        link = request.POST.get('link_formalizacao', '').strip()
        if not link:
            return JsonResponse({'success': False, 'message': 'Link é obrigatório'}, status=400)
        
        # Buscar tabulação "LINK DE FORMALIZACAO"
        tabulacao_link = TabulacaoContrato.objects.filter(nome__icontains='LINK DE FORMALIZACAO').first()
        if not tabulacao_link:
            tabulacao_link = TabulacaoContrato.objects.filter(ordem=3).first()
        
        if not tabulacao_link:
            return JsonResponse({'success': False, 'message': 'Tabulação não encontrada'}, status=400)
        
        contrato.link_formalizacao = link
        contrato.status_tabulacao = tabulacao_link
        contrato.save()
        
        # Notificar SSE
        _notificar_atualizacao()
        
        return JsonResponse({'success': True, 'message': 'Link de formalização informado!'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_post_confirmar_assinatura(request, contrato_id):
    """API POST para consultor confirmar que cliente assinou no link"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Consultor só pode confirmar assinatura dos seus contratos
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        # Verificar se tem link de formalização
        if not contrato.link_formalizacao:
            return JsonResponse({'success': False, 'message': 'Contrato não possui link de formalização'}, status=400)
        
        # Buscar tabulação "FORMALIZADO"
        tabulacao_formalizado = TabulacaoContrato.objects.filter(nome__iexact='FORMALIZADO').first()
        if not tabulacao_formalizado:
            tabulacao_formalizado = TabulacaoContrato.objects.filter(ordem=5).first()
        
        if not tabulacao_formalizado:
            return JsonResponse({'success': False, 'message': 'Tabulação FORMALIZADO não encontrada'}, status=400)
        
        contrato.cliente_formalizou = True
        contrato.data_formalizacao = timezone.now()
        contrato.status_tabulacao = tabulacao_formalizado
        contrato.save()
        
        # Notificar SSE
        _notificar_atualizacao()
        
        return JsonResponse({'success': True, 'message': 'Assinatura confirmada! Contrato movido para FORMALIZADO.'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_post_upload_video_cliente(request, contrato_id):
    """API POST para upload de vídeo do cliente (.mp4, max 25MB)"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Consultor ou operacional pode enviar vídeo
        if not request.user.is_superuser and contrato.vendedor != request.user:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        if 'video' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Vídeo é obrigatório'}, status=400)
        
        video = request.FILES['video']
        
        # Validar extensão
        nome_arquivo = video.name.lower()
        if not nome_arquivo.endswith('.mp4'):
            return JsonResponse({'success': False, 'message': 'Formato inválido. Apenas .mp4 é permitido'}, status=400)
        
        # Validar tamanho (25MB)
        tamanho_max = 25 * 1024 * 1024  # 25MB em bytes
        if video.size > tamanho_max:
            return JsonResponse({'success': False, 'message': 'Vídeo muito grande. Máximo 25MB'}, status=400)
        
        # Deletar vídeo antigo se existir
        if contrato.video_cliente:
            try:
                if os.path.exists(contrato.video_cliente.path):
                    os.remove(contrato.video_cliente.path)
            except Exception:
                pass
        
        # Buscar tabulação "VIDEO ANEXADO"
        tabulacao_video = TabulacaoContrato.objects.filter(nome__icontains='VIDEO ANEXADO').first()
        if not tabulacao_video:
            tabulacao_video = TabulacaoContrato.objects.filter(ordem=7).first()
        
        if not tabulacao_video:
            return JsonResponse({'success': False, 'message': 'Tabulação VIDEO ANEXADO não encontrada'}, status=400)
        
        # Salvar vídeo
        contrato.video_cliente = video
        contrato.video_tamanho = video.size
        contrato.status_tabulacao = tabulacao_video
        contrato.save()
        
        # Notificar SSE
        _notificar_atualizacao()
        
        return JsonResponse({
            'success': True, 
            'message': 'Vídeo enviado com sucesso!',
            'data': {
                'video_url': contrato.video_cliente.url,
                'video_tamanho': contrato.video_tamanho,
            }
        })
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_post_solicitar_video(request, contrato_id):
    """API POST para operacional solicitar vídeo do cliente"""
    try:
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Apenas operacional pode solicitar vídeo
        if not request.user.is_superuser:
            if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
                return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        # Buscar tabulação "SOLICITACAO DE VIDEO"
        tabulacao_solicitar = TabulacaoContrato.objects.filter(nome__icontains='SOLICITACAO DE VIDEO').first()
        if not tabulacao_solicitar:
            tabulacao_solicitar = TabulacaoContrato.objects.filter(ordem=6).first()
        
        if not tabulacao_solicitar:
            return JsonResponse({'success': False, 'message': 'Tabulação não encontrada'}, status=400)
        
        contrato.status_tabulacao = tabulacao_solicitar
        contrato.save()
        
        # Notificar SSE
        _notificar_atualizacao()
        
        return JsonResponse({'success': True, 'message': 'Solicitação de vídeo enviada!'})
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


# ==================== API EXCLUSÃO (SUPERUSER) ====================

@login_required
@require_http_methods(["POST", "DELETE"])
def api_delete_contrato(request, contrato_id):
    """API para excluir contrato permanentemente (APENAS SUPERUSER)"""
    try:
        # Verificar se é superuser
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'message': 'Acesso negado. Apenas administradores podem excluir contratos.'}, status=403)
        
        contrato = ContratoOperacional.objects.get(id=contrato_id)
        
        # Guardar info para log
        numero_serie = contrato.numero_serie
        cliente_nome = contrato.dados_contrato.get('dados_pessoais', {}).get('nome_completo', 'N/A') if isinstance(contrato.dados_contrato, dict) else 'N/A'
        
        # Deletar anexos relacionados
        from django.core.files.storage import default_storage
        for anexo in contrato.anexos.all():
            if anexo.arquivo:
                try:
                    default_storage.delete(anexo.arquivo.name)
                except Exception:
                    pass
            anexo.delete()
        
        # Deletar vídeo se existir
        if contrato.video_cliente:
            try:
                default_storage.delete(contrato.video_cliente.name)
            except Exception:
                pass
        
        # Deletar contrato
        contrato.delete()
        
        # Notificar SSE
        _notificar_atualizacao()
        
        return JsonResponse({
            'success': True, 
            'message': f'Contrato {numero_serie} ({cliente_nome}) excluído permanentemente!'
        })
    except ContratoOperacional.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=500)
