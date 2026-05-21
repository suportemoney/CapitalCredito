"""
APIs para schemas e campos customizados
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
# from apps.seguranca.permissoes.decorators import controle_acess  # Permissão será configurada depois
from apps.operacional.contratos.models import ConvenioOperacao, SchemaCampo, Convenio, Operacao
from apps.operacional.contratos.utils import get_campos_comuns
import csv
import json
import io

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["GET"])
def api_get_schemas_importados(request):
    """API GET para listar todos os schemas importados (ConvenioOperacao com campos)"""
    try:
        # Buscar todos os ConvenioOperacao que têm campos de schema
        convenios_operacoes = ConvenioOperacao.objects.filter(
            campos_schema__isnull=False
        ).distinct().select_related('convenio', 'operacao').prefetch_related('campos_schema').order_by('-data_criacao')
        
        data = []
        for co in convenios_operacoes:
            campos_count = co.campos_schema.count()
            if campos_count > 0:  # Só incluir se tiver campos
                # Pegar data de criação do primeiro campo (aproximação da data de importação)
                primeiro_campo = co.campos_schema.order_by('data_criacao').first()
                data_importacao = primeiro_campo.data_criacao if primeiro_campo else co.data_criacao
                
                data.append({
                    'id': co.id,
                    'titulo': co.titulo or f'{co.convenio.nome} - {co.operacao.nome}',
                    'convenio_nome': co.convenio.nome,
                    'operacao_nome': co.operacao.nome,
                    'campos_count': campos_count,
                    'data_importacao': data_importacao.strftime('%d/%m/%Y %H:%M'),
                })
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar schemas: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["GET"])
def api_get_schemas_por_convenio_operacao(request):
    """API GET para listar schemas de um Convênio+Operação"""
    try:
        convenio_operacao_id = request.GET.get('convenio_operacao_id')
        if not convenio_operacao_id:
            return JsonResponse({'success': False, 'message': 'convenio_operacao_id é obrigatório'})
        
        campos = SchemaCampo.objects.filter(
            convenio_operacao_id=convenio_operacao_id
        ).order_by('ordem', 'label')
        
        # Tentar ordenar por pagina se o campo existir
        try:
            campos = campos.order_by('pagina', 'ordem', 'label')
        except Exception:
            pass  # Campo pagina pode não existir ainda
        
        data = []
        for campo in campos:
            item = {
                'id': campo.id,
                'category': campo.category,
                'label': campo.label,
                'type': campo.type,
                'choices': campo.choices or [],
                'placeholder': campo.placeholder or '',
                'required': campo.required,
                'ordem': campo.ordem,
            }
            # Adicionar pagina com fallback para 1 se não existir
            try:
                item['pagina'] = campo.pagina if campo.pagina else 1
            except AttributeError:
                item['pagina'] = 1
            data.append(item)
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar schemas: {str(e)}'}, status=500)

@login_required
@require_http_methods(["GET"])
def api_get_schema_campos(request):
    """API GET para retornar campos do schema para formulário.
    
    Se o schema (ConvenioOperacao) tem campos customizados, usa APENAS esses campos.
    Se não tem campos customizados, usa os campos comuns como fallback.
    """
    try:
        convenio_operacao_id = request.GET.get('convenio_operacao_id')
        if not convenio_operacao_id:
            return JsonResponse({'success': False, 'message': 'convenio_operacao_id é obrigatório'})
        
        # Campos customizados do schema
        campos_customizados = SchemaCampo.objects.filter(
            convenio_operacao_id=convenio_operacao_id
        ).order_by('pagina', 'ordem', 'label')
        
        # Se tem campos customizados, usa APENAS eles (schema autossuficiente)
        if campos_customizados.exists():
            data = [{
                'id': campo.id,
                'category': campo.category,
                'label': campo.label,
                'type': campo.type,
                'choices': campo.choices or [],
                'placeholder': campo.placeholder or '',
                'required': campo.required,
                'ordem': campo.ordem,
                'pagina': campo.pagina,
                'customizado': True,
            } for campo in campos_customizados]
            
            # Calcular total de páginas dos campos customizados
            paginas = [c.pagina for c in campos_customizados]
            total_paginas = max(paginas) if paginas else 1
        else:
            # Fallback: usar campos comuns se não tem customizados
            campos_comuns = get_campos_comuns()
            data = [{
                'id': None,
                'category': campo['category'],
                'label': campo['label'],
                'type': campo['type'],
                'choices': campo.get('choices', []),
                'placeholder': campo.get('placeholder', ''),
                'required': campo.get('required', False),
                'ordem': 0,
                'pagina': campo.get('pagina', 1),
                'customizado': False,
            } for campo in campos_comuns]
            total_paginas = 1
        
        return JsonResponse({
            'success': True, 
            'data': data,
            'total_paginas': total_paginas,
            'paginas': list(range(1, total_paginas + 1))
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar schema: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_criar_campo_schema(request):
    """API POST para criar campo customizado via interface"""
    try:
        convenio_operacao_id = request.POST.get('convenio_operacao_id')
        category = request.POST.get('category', '').strip()
        label = request.POST.get('label', '').strip()
        field_type = request.POST.get('type', '').strip()
        placeholder = request.POST.get('placeholder', '').strip()
        required = request.POST.get('required', 'false') == 'true'
        ordem = int(request.POST.get('ordem', 0))
        pagina_str = request.POST.get('pagina', '1').strip()
        pagina = int(pagina_str) if pagina_str.isdigit() else 1
        if pagina < 1:
            pagina = 1
        choices_str = request.POST.get('choices', '').strip()
        
        if not convenio_operacao_id or not category or not label or not field_type:
            return JsonResponse({'success': False, 'message': 'Campos obrigatórios: convenio_operacao_id, category, label, type'})
        
        convenio_operacao = ConvenioOperacao.objects.get(id=convenio_operacao_id)
        
        choices = None
        if choices_str and field_type in ['SELECT', 'MULTISELECTOR']:
            choices = [c.strip() for c in choices_str.split(',') if c.strip()]
        elif choices_str and field_type == 'MULTIINPUT':
            choices = [c.strip() for c in choices_str.split(';') if c.strip()]
        
        campo = SchemaCampo.objects.create(
            convenio_operacao=convenio_operacao,
            category=category,
            label=label,
            type=field_type,
            choices=choices,
            placeholder=placeholder if placeholder else None,
            required=required,
            ordem=ordem,
            pagina=pagina,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Campo criado com sucesso!',
            'data': {
                'id': campo.id,
                'category': campo.category,
                'label': campo.label,
                'type': campo.type,
                'choices': campo.choices or [],
                'placeholder': campo.placeholder or '',
                'required': campo.required,
                'ordem': campo.ordem,
                'pagina': campo.pagina,
            }
        })
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio+Operação não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar campo: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão será configurada depois
@require_http_methods(["POST"])
def api_post_upload_schema_csv(request):
    """API POST para fazer upload de CSV e criar/atualizar schema"""
    try:
        # Aceitar tanto convenio_operacao_id (para compatibilidade) quanto convenio_id + operacao_id
        convenio_operacao_id = request.POST.get('convenio_operacao_id', '').strip()
        convenio_id = request.POST.get('convenio_id', '').strip()
        operacao_id = request.POST.get('operacao_id', '').strip()
        
        # Converter strings vazias para None
        convenio_operacao_id = convenio_operacao_id if convenio_operacao_id else None
        convenio_id = convenio_id if convenio_id else None
        operacao_id = operacao_id if operacao_id else None
        
        if convenio_operacao_id:
            # Modo antigo: já tem a associação
            try:
                convenio_operacao = ConvenioOperacao.objects.get(id=convenio_operacao_id)
            except (ValueError, ConvenioOperacao.DoesNotExist):
                return JsonResponse({'success': False, 'message': f'Convênio+Operação com ID {convenio_operacao_id} não encontrado'}, status=404)
        elif convenio_id and operacao_id:
            # Modo novo: criar associação se não existir
            try:
                convenio = Convenio.objects.get(id=convenio_id)
                operacao = Operacao.objects.get(id=operacao_id)
            except (ValueError, Convenio.DoesNotExist):
                return JsonResponse({'success': False, 'message': f'Convênio com ID {convenio_id} não encontrado'}, status=404)
            except (ValueError, Operacao.DoesNotExist):
                return JsonResponse({'success': False, 'message': f'Operação com ID {operacao_id} não encontrada'}, status=404)
            
            # Pegar título se fornecido
            titulo = request.POST.get('titulo', '').strip()
            titulo = titulo if titulo else None
            
            # Criar schema (ConvenioOperacao) - agora sempre cria novo se tiver título diferente
            if titulo:
                # Se tem título, buscar por convênio+operação+título ou criar novo
                convenio_operacao, created = ConvenioOperacao.objects.get_or_create(
                    convenio=convenio,
                    operacao=operacao,
                    titulo=titulo
                )
            else:
                # Se não tem título, buscar existente sem título ou criar novo
                convenio_operacao = ConvenioOperacao.objects.filter(
                    convenio=convenio,
                    operacao=operacao,
                    titulo__isnull=True
                ).first()
                if not convenio_operacao:
                    convenio_operacao = ConvenioOperacao.objects.create(
                        convenio=convenio,
                        operacao=operacao
                    )
                    created = True
                else:
                    created = False
            
            if created:
                # Log para debug (pode remover em produção)
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'Associação Convenio-Operacao criada: {convenio.nome} - {operacao.nome} (ID: {convenio_operacao.id})')
        else:
            return JsonResponse({
                'success': False, 
                'message': 'convenio_operacao_id OU (convenio_id + operacao_id) são obrigatórios',
                'recebido': {
                    'convenio_operacao_id': convenio_operacao_id,
                    'convenio_id': convenio_id,
                    'operacao_id': operacao_id
                }
            }, status=400)
        
        if 'arquivo' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'Arquivo CSV é obrigatório'})
        arquivo = request.FILES['arquivo']
        
        # Ler CSV (remover BOM se existir)
        file_content = arquivo.read().decode('utf-8-sig')  # utf-8-sig remove BOM automaticamente
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=';')
        
        # Debug: verificar se o CSV foi lido corretamente
        print(f"DEBUG: Nomes das colunas do CSV: {csv_reader.fieldnames}")
        
        criados = 0
        atualizados = 0
        erros = []
        linhas_processadas = 0
        
        for row in csv_reader:
            linhas_processadas += 1
            try:
                # Debug: verificar primeira linha
                if linhas_processadas == 1:
                    print(f"DEBUG: Primeira linha do CSV: {row}")
                
                category = row.get('Category', '').strip()
                label = row.get('Label', '').strip()
                field_type = row.get('Type', '').strip().upper()
                choices_str = row.get('Choices', '').strip()
                placeholder = row.get('Placeholder', '').strip().strip('"')
                required = row.get('Required', '0').strip() == '1'
                ordem_str = row.get('Ordem', '').strip()
                pagina_str = row.get('Pagina', '').strip()  # Nova coluna de página
                
                # Debug: verificar valores extraídos
                if linhas_processadas <= 3:
                    print(f"DEBUG Linha {linhas_processadas}: category='{category}', label='{label}', type='{field_type}', required='{required}', ordem='{ordem_str}', pagina='{pagina_str}'")
                
                if not category or not label or not field_type:
                    if linhas_processadas <= 3:
                        print(f"DEBUG: Linha {linhas_processadas} ignorada - dados incompletos")
                    continue
                
                choices = None
                if choices_str:
                    if field_type in ['SELECT', 'MULTISELECTOR']:
                        # Para SELECT e MULTISELECTOR, separar por vírgula
                        choices = [c.strip() for c in choices_str.split(',') if c.strip()]
                    elif field_type == 'MULTIINPUT':
                        # Para MULTIINPUT, separar por ponto e vírgula
                        choices = [c.strip() for c in choices_str.split(';') if c.strip()]
                
                # Calcular ordem e página
                ordem = int(ordem_str) if ordem_str and ordem_str.isdigit() else 0
                pagina = int(pagina_str) if pagina_str and pagina_str.isdigit() else 1
                if pagina < 1:
                    pagina = 1  # Página mínima é 1
                
                campo, created = SchemaCampo.objects.update_or_create(
                    convenio_operacao=convenio_operacao,
                    category=category,
                    label=label,
                    defaults={
                        'type': field_type,
                        'choices': choices,
                        'placeholder': placeholder if placeholder else None,
                        'required': required,
                        'ordem': ordem,
                        'pagina': pagina,
                    }
                )
                
                if created:
                    criados += 1
                    if linhas_processadas <= 3:
                        print(f"DEBUG: Campo criado - {label} (ID: {campo.id})")
                else:
                    atualizados += 1
                    if linhas_processadas <= 3:
                        print(f"DEBUG: Campo atualizado - {label} (ID: {campo.id})")
                    
            except Exception as e:
                error_msg = f'Erro ao processar linha {linhas_processadas} (label: {label if "label" in locals() else "N/A"}): {str(e)}'
                erros.append(error_msg)
                print(f"DEBUG ERRO: {error_msg}")
                import traceback
                print(traceback.format_exc())
        
        print(f"DEBUG: Total de linhas processadas: {linhas_processadas}, Criados: {criados}, Atualizados: {atualizados}, Erros: {len(erros)}")
        
        return JsonResponse({
            'success': True,
            'message': f'CSV processado: {criados} criados, {atualizados} atualizados',
            'data': {
                'criados': criados,
                'atualizados': atualizados,
                'erros': erros,
                'linhas_processadas': linhas_processadas,
                'convenio_operacao_id': convenio_operacao.id,  # Retornar o ID da associação criada/encontrada
            }
        })
    except ConvenioOperacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio+Operação não encontrado'}, status=404)
    except Convenio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Convênio não encontrado'}, status=404)
    except Operacao.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Operação não encontrada'}, status=404)
    except Exception as e:
        import traceback
        from django.conf import settings
        error_data = {
            'success': False, 
            'message': f'Erro ao processar CSV: {str(e)}'
        }
        if settings.DEBUG:
            error_data['traceback'] = traceback.format_exc()
        return JsonResponse(error_data, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["GET", "POST"])
def api_editar_campo_schema(request, campo_id):
    """API para editar campo de schema"""
    try:
        campo = SchemaCampo.objects.get(id=campo_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': campo.id,
                    'convenio_operacao_id': campo.convenio_operacao.id,
                    'category': campo.category,
                    'label': campo.label,
                    'type': campo.type,
                    'choices': campo.choices or [],
                    'placeholder': campo.placeholder or '',
                    'required': campo.required,
                    'ordem': campo.ordem,
                    'pagina': campo.pagina,
                }
            })
        
        category = request.POST.get('category', '').strip()
        label = request.POST.get('label', '').strip()
        field_type = request.POST.get('type', '').strip()
        placeholder = request.POST.get('placeholder', '').strip()
        required = request.POST.get('required', 'false') == 'true'
        ordem = int(request.POST.get('ordem', campo.ordem))
        pagina_str = request.POST.get('pagina', str(campo.pagina)).strip()
        pagina = int(pagina_str) if pagina_str.isdigit() else campo.pagina
        if pagina < 1:
            pagina = 1
        choices_str = request.POST.get('choices', '').strip()
        
        if not category or not label or not field_type:
            return JsonResponse({'success': False, 'message': 'Campos obrigatórios: category, label, type'})
        
        choices = None
        if choices_str and field_type in ['SELECT', 'MULTISELECTOR']:
            choices = [c.strip() for c in choices_str.split(',') if c.strip()]
        elif choices_str and field_type == 'MULTIINPUT':
            choices = [c.strip() for c in choices_str.split(';') if c.strip()]
        
        campo.category = category
        campo.label = label
        campo.type = field_type
        campo.choices = choices
        campo.placeholder = placeholder if placeholder else None
        campo.required = required
        campo.ordem = ordem
        campo.pagina = pagina
        campo.save()
        
        return JsonResponse({'success': True, 'message': 'Campo atualizado com sucesso!'})
    except SchemaCampo.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Campo não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar campo: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_deletar_campo_schema(request, campo_id):
    """API POST para deletar campo de schema"""
    try:
        campo = SchemaCampo.objects.get(id=campo_id)
        campo.delete()
        return JsonResponse({'success': True, 'message': 'Campo deletado com sucesso!'})
    except SchemaCampo.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Campo não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar campo: {str(e)}'}, status=500)

@login_required
# @controle_acess('SS_ADMINISTRATIVO')
@require_http_methods(["POST"])
def api_post_reordenar_campos(request):
    """API POST para reordenar campos do schema"""
    try:
        campo_ids = request.POST.getlist('campo_ids[]')
        if not campo_ids:
            return JsonResponse({'success': False, 'message': 'campo_ids é obrigatório'})
        
        for ordem, campo_id in enumerate(campo_ids, start=1):
            try:
                campo = SchemaCampo.objects.get(id=campo_id)
                campo.ordem = ordem
                campo.save()
            except SchemaCampo.DoesNotExist:
                continue
        
        return JsonResponse({'success': True, 'message': 'Campos reordenados com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao reordenar campos: {str(e)}'}, status=500)
