"""
APIs para gerenciar contratos de pagamento
"""
import re
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count
from datetime import datetime
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.financeiro_vendas.models import ContratoPagamento, Classificador
from apps.vendas.siape.models import Cliente, Produto
from apps.rh.admin.models import Setor
from apps.rh.funcionarios.models import Funcionario


def _parse_intervalo_datas(request):
    """Valida data_inicio e data_fim do GET; retorna tupla (date, date) ou JsonResponse de erro."""
    data_inicio_str = request.GET.get('data_inicio', '').strip()
    data_fim_str = request.GET.get('data_fim', '').strip()

    if not data_inicio_str:
        return JsonResponse({'success': False, 'message': 'Data início é obrigatória'}, status=400)
    if not data_fim_str:
        return JsonResponse({'success': False, 'message': 'Data fim é obrigatória'}, status=400)

    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Formato de data inválido. Use AAAA-MM-DD'}, status=400)

    if data_fim < data_inicio:
        return JsonResponse({'success': False, 'message': 'Data fim não pode ser anterior à data início'}, status=400)

    return data_inicio, data_fim


def _filtrar_por_data_pagamento(queryset, data_inicio, data_fim):
    """Filtra contratos com data_pagamento no intervalo informado."""
    return queryset.filter(
        data_pagamento__gte=data_inicio,
        data_pagamento__lte=data_fim,
    )


def _usuario_pode_gerenciar(user):
    """Superusuário ou membro da equipe (staff) pode criar/editar/inativar contratos."""
    return user.is_superuser or user.is_staff


def _aplicar_filtros_gerenciador(queryset, request):
    """Aplica filtros opcionais do gerenciador de contratos."""
    user_id = request.GET.get('user_id', '').strip()
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    setor_id = request.GET.get('setor_id', '').strip()
    if setor_id:
        queryset = queryset.filter(setor_id=setor_id)

    produto_id = request.GET.get('produto_id', '').strip()
    if produto_id:
        queryset = queryset.filter(produto_id=produto_id)

    classificador_id = request.GET.get('classificador_id', '').strip()
    if classificador_id:
        queryset = queryset.filter(classificador_id=classificador_id)

    cpf = request.GET.get('cpf', '').strip()
    if cpf:
        cpf_limpo = re.sub(r'\D', '', cpf)
        if cpf_limpo:
            queryset = queryset.filter(cliente_cpf__icontains=cpf_limpo)

    cliente = request.GET.get('cliente', '').strip()
    if cliente:
        queryset = queryset.filter(cliente_nome__icontains=cliente.upper())

    banco = request.GET.get('banco', '').strip()
    if banco:
        queryset = queryset.filter(banco__icontains=banco.upper())

    ponta = request.GET.get('ponta', '').strip()
    if ponta in ('1', 'true', 'sim'):
        queryset = queryset.filter(flg_ponta=True)
    elif ponta in ('0', 'false', 'nao'):
        queryset = queryset.filter(flg_ponta=False)

    return queryset


@login_required
@controle_acess('SS27')
@require_http_methods(["GET"])
def api_resumo_contratos(request):
    """API GET para totais de AF, Repasse e quantidade de contratos no período (data_pagamento)."""
    try:
        intervalo = _parse_intervalo_datas(request)
        if isinstance(intervalo, JsonResponse):
            return intervalo
        data_inicio, data_fim = intervalo

        qs = _filtrar_por_data_pagamento(
            ContratoPagamento.objects.filter(status_ativo=True),
            data_inicio,
            data_fim,
        )
        agg = qs.aggregate(
            total_af=Sum('valor_af'),
            total_repasse=Sum('valor_repasse'),
            total_contratos=Count('id'),
        )

        return JsonResponse({
            'success': True,
            'data': {
                'total_af': float(agg['total_af'] or 0),
                'total_repasse': float(agg['total_repasse'] or 0),
                'total_contratos': agg['total_contratos'] or 0,
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao obter resumo: {str(e)}'}, status=500)


@login_required
@controle_acess('SS27')
@require_http_methods(["GET"])
def api_listar_contratos(request):
    """API GET para listar contratos filtrados por status e data de pagamento"""
    try:
        intervalo = _parse_intervalo_datas(request)
        if isinstance(intervalo, JsonResponse):
            return intervalo
        data_inicio, data_fim = intervalo

        status = request.GET.get('status', 'A_PAGAR')

        contratos = _filtrar_por_data_pagamento(
            ContratoPagamento.objects.filter(status_ativo=True),
            data_inicio,
            data_fim,
        ).select_related(
            'user',
            'setor',
            'produto',
            'classificador'
        )
        
        if status == 'A_PAGAR':
            contratos = contratos.filter(status='A_PAGAR')
        elif status == 'PAGO':
            contratos = contratos.filter(status='PAGO')
        elif status == 'NAO_PAGO':
            contratos = contratos.filter(status='NAO_PAGO')

        contratos = _aplicar_filtros_gerenciador(contratos, request)
        contratos = contratos.order_by('-data_contrato', '-data_criacao')
        
        data = []
        for contrato in contratos:
            funcionario = None
            if hasattr(contrato.user, 'funcionario_profile') and contrato.user.funcionario_profile:
                funcionario = contrato.user.funcionario_profile.nome_completo
            
            data.append({
                'id': contrato.id,
                'funcionario': funcionario or contrato.user.username,
                'cliente_nome': contrato.cliente_nome,
                'cliente_cpf': contrato.cliente_cpf,
                'produto_id': contrato.produto.id,
                'produto_nome': contrato.produto.nome,
                'banco': contrato.banco,
                'valor_af': float(contrato.valor_af),
                'valor_repasse': float(contrato.valor_repasse),
                'flg_ponta': contrato.flg_ponta,
                'classificador_id': contrato.classificador.id,
                'classificador_nome': contrato.classificador.titulo,
                'data_contrato': contrato.data_contrato.strftime('%Y-%m-%d'),
                'status': contrato.status,
                'data_pagamento': contrato.data_pagamento.strftime('%Y-%m-%d') if contrato.data_pagamento else '',
            })
        
        return JsonResponse({'success': True, 'data': data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar contratos: {str(e)}'}, status=500)

@login_required
@controle_acess('SS27')
@require_http_methods(["GET"])
def api_buscar_cliente_por_cpf(request):
    """API GET para buscar cliente por CPF"""
    try:
        cpf = request.GET.get('cpf', '').strip()
        cpf_limpo = re.sub(r'\D', '', cpf)
        
        if len(cpf_limpo) != 11:
            return JsonResponse({'success': False, 'message': 'CPF inválido'})
        
        cliente = Cliente.objects.filter(cpf=cpf_limpo, status=True).first()
        
        if cliente:
            return JsonResponse({
                'success': True,
                'data': {
                    'nome': cliente.nome,
                    'cpf': cliente.cpf,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Cliente não encontrado'
            })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar cliente: {str(e)}'}, status=500)

@login_required
@controle_acess('SS27')
@require_http_methods(["GET"])
def api_get_setor_funcionario(request, user_id):
    """API GET para buscar setor do funcionário associado ao usuário"""
    try:
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        setor_id = None
        if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
            dados_prof = getattr(user.funcionario_profile, 'dados_profissionais', None)
            if dados_prof and dados_prof.setor:
                setor_id = dados_prof.setor.id
        
        return JsonResponse({
            'success': True,
            'data': {
                'setor_id': setor_id,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar setor: {str(e)}'}, status=500)

@login_required
@controle_acess('SS27')
@require_http_methods(["POST"])
def api_criar_contrato(request):
    """API POST para criar novo contrato"""
    try:
        if not _usuario_pode_gerenciar(request.user):
            return JsonResponse({'success': False, 'message': 'Sem permissão para criar contratos'}, status=403)

        user_id = request.POST.get('user_id')
        setor_id = request.POST.get('setor_id')
        cliente_cpf = request.POST.get('cliente_cpf', '').strip()
        cliente_nome = request.POST.get('cliente_nome', '').strip()
        produto_id = request.POST.get('produto_id')
        banco = request.POST.get('banco', '').strip()
        valor_af = request.POST.get('valor_af', '').strip()
        valor_repasse = request.POST.get('valor_repasse', '').strip()
        flg_ponta = request.POST.get('flg_ponta') == 'on'
        classificador_id = request.POST.get('classificador_id')
        data_contrato = request.POST.get('data_contrato', '').strip()
        status = request.POST.get('status', 'A_PAGAR')
        data_pagamento = request.POST.get('data_pagamento', '').strip()
        
        if not user_id:
            return JsonResponse({'success': False, 'message': 'Vendedor é obrigatório'})
        
        if not setor_id:
            return JsonResponse({'success': False, 'message': 'Setor é obrigatório'})
        
        if not cliente_cpf:
            return JsonResponse({'success': False, 'message': 'CPF do cliente é obrigatório'})
        
        if not cliente_nome:
            return JsonResponse({'success': False, 'message': 'Nome do cliente é obrigatório'})
        
        if not produto_id:
            return JsonResponse({'success': False, 'message': 'Produto é obrigatório'})
        
        if not banco:
            return JsonResponse({'success': False, 'message': 'Banco é obrigatório'})
        
        if not valor_af:
            return JsonResponse({'success': False, 'message': 'Valor AF é obrigatório'})
        
        if not valor_repasse:
            return JsonResponse({'success': False, 'message': 'Valor Repasse é obrigatório'})
        
        if not classificador_id:
            return JsonResponse({'success': False, 'message': 'Classificador é obrigatório'})
        
        if not data_contrato:
            return JsonResponse({'success': False, 'message': 'Data do contrato é obrigatória'})
        
        cpf_limpo = re.sub(r'\D', '', cliente_cpf)
        if len(cpf_limpo) != 11:
            return JsonResponse({'success': False, 'message': 'CPF inválido'})
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            setor = Setor.objects.get(id=setor_id)
            produto = Produto.objects.get(id=produto_id)
            classificador = Classificador.objects.get(id=classificador_id)
            
            data_contrato_obj = datetime.strptime(data_contrato, '%Y-%m-%d').date()
            
            data_pagamento_obj = None
            if status == 'PAGO' and data_pagamento:
                data_pagamento_obj = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
            
            with transaction.atomic():
                contrato = ContratoPagamento.objects.create(
                    user=user,
                    setor=setor,
                    cliente_cpf=cpf_limpo,
                    cliente_nome=cliente_nome.upper(),
                    produto=produto,
                    banco=banco.upper(),
                    valor_af=valor_af,
                    valor_repasse=valor_repasse,
                    flg_ponta=flg_ponta,
                    classificador=classificador,
                    data_contrato=data_contrato_obj,
                    status=status,
                    data_pagamento=data_pagamento_obj,
                    status_ativo=True
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Contrato criado com sucesso!'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Usuário não encontrado'})
        except Setor.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Setor não encontrado'})
        except Produto.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Produto não encontrado'})
        except Classificador.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Classificador não encontrado'})
        except ValueError as e:
            return JsonResponse({'success': False, 'message': f'Data inválida: {str(e)}'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar contrato: {str(e)}'}, status=500)

@login_required
@controle_acess('SS27')
@require_http_methods(["POST"])
def api_editar_campo(request, contrato_id):
    """API POST para editar um campo específico do contrato"""
    try:
        if not _usuario_pode_gerenciar(request.user):
            return JsonResponse({'success': False, 'message': 'Sem permissão para editar contratos'}, status=403)

        campo = request.POST.get('campo')
        valor = request.POST.get('valor', '').strip()
        
        if not campo:
            return JsonResponse({'success': False, 'message': 'Campo não especificado'})
        
        contrato = ContratoPagamento.objects.get(id=contrato_id, status_ativo=True)
        
        with transaction.atomic():
            if campo == 'produto_id':
                produto = Produto.objects.get(id=valor)
                contrato.produto = produto
            elif campo == 'banco':
                contrato.banco = valor.upper()
            elif campo == 'valor_af':
                from decimal import Decimal
                contrato.valor_af = Decimal(valor)
            elif campo == 'valor_repasse':
                from decimal import Decimal
                contrato.valor_repasse = Decimal(valor)
            elif campo == 'flg_ponta':
                if isinstance(valor, str):
                    contrato.flg_ponta = valor.lower() == 'true'
                else:
                    contrato.flg_ponta = bool(valor)
            elif campo == 'classificador_id':
                classificador = Classificador.objects.get(id=valor)
                contrato.classificador = classificador
            else:
                return JsonResponse({'success': False, 'message': 'Campo inválido'})
            
            contrato.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Campo atualizado com sucesso!'
        })
        
    except ContratoPagamento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar campo: {str(e)}'}, status=500)

@login_required
@controle_acess('SS27')
@require_http_methods(["POST"])
def api_inativar_contrato(request, contrato_id):
    """API POST para inativar contrato"""
    try:
        if not _usuario_pode_gerenciar(request.user):
            return JsonResponse({'success': False, 'message': 'Sem permissão para inativar contratos'}, status=403)

        contrato = ContratoPagamento.objects.get(id=contrato_id, status_ativo=True)
        contrato.status_ativo = False
        contrato.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Contrato inativado com sucesso!'
        })
        
    except ContratoPagamento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Contrato não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao inativar contrato: {str(e)}'}, status=500)

