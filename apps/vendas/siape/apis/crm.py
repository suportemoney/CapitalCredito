"""
APIs para CRM
"""
import re
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from datetime import datetime
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import ControleCRM, TabulacaoCRM, Cliente
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

@login_required
@controle_acess('SS25')
@require_http_methods(["POST"])
def api_adicionar_esteira(request):
    """API POST para adicionar cliente à esteira do CRM"""
    try:
        cpf = request.POST.get('cpf', '').strip()
        data_contato = request.POST.get('data_contato', '').strip()
        hora_contato = request.POST.get('hora_contato', '').strip()
        
        if not cpf:
            return JsonResponse({'success': False, 'message': 'CPF é obrigatório'})
        
        if not data_contato:
            return JsonResponse({'success': False, 'message': 'Data de contato é obrigatória'})
        
        if not hora_contato:
            return JsonResponse({'success': False, 'message': 'Hora de contato é obrigatória'})
        
        cpf_limpo = re.sub(r'\D', '', cpf)
        if len(cpf_limpo) != 11:
            return JsonResponse({'success': False, 'message': 'CPF inválido'})
        
        try:
            data_contato_obj = datetime.strptime(data_contato, '%Y-%m-%d').date()
        except:
            return JsonResponse({'success': False, 'message': 'Data de contato inválida'})
        
        try:
            hora_contato_obj = datetime.strptime(hora_contato, '%H:%M').time()
        except:
            return JsonResponse({'success': False, 'message': 'Hora de contato inválida'})
        
        tabulacao_em_negociacao = TabulacaoCRM.objects.filter(nome='EM NEGOCIACAO', status=True).first()
        if not tabulacao_em_negociacao:
            return JsonResponse({'success': False, 'message': 'Tabulação "Em Negociação" não encontrada. Contate o administrador.'})
        
        with transaction.atomic():
            controle, created = ControleCRM.objects.get_or_create(
                cpf=cpf_limpo,
                tabulacao=tabulacao_em_negociacao,
                user=request.user,
                status=True,
                defaults={
                    'data_contato': data_contato_obj,
                    'hora_contato': hora_contato_obj,
                }
            )
            
            if not created:
                controle.data_contato = data_contato_obj
                controle.hora_contato = hora_contato_obj
                controle.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Cliente adicionado à esteira com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao adicionar à esteira: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao adicionar à esteira: {str(e)}'}, status=500)

@login_required
@controle_acess('SS26')
@require_http_methods(["GET"])
def api_listar_kanban(request):
    """API GET para listar dados do Kanban com filtros e permissões hierárquicas"""
    try:
        # Obter filtros
        nome_cliente = request.GET.get('nome_cliente', '').strip()
        cpf_cliente = request.GET.get('cpf_cliente', '').strip()
        data_inicio = request.GET.get('data_inicio', '').strip()
        data_fim = request.GET.get('data_fim', '').strip()
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        
        # Obter nível hierárquico do usuário logado
        nivel_importancia = None
        funcionario_logado = None
        user_ids_permitidos = []
        
        if request.user.is_superuser:
            # Superuser vê tudo
            nivel_importancia = 999
        elif hasattr(request.user, 'funcionario_profile') and request.user.funcionario_profile:
            funcionario_logado = request.user.funcionario_profile
            if hasattr(funcionario_logado, 'dados_profissionais') and funcionario_logado.dados_profissionais:
                cargo = funcionario_logado.dados_profissionais.cargo
                if cargo and cargo.nivel_hierarquico:
                    nivel_importancia = cargo.nivel_hierarquico.importancia
                    
                    # Aplicar filtros baseados no nível hierárquico
                    if nivel_importancia in [0, 1]:
                        # Apenas seus próprios cards
                        user_ids_permitidos = [request.user.id]
                    elif nivel_importancia == 2:
                        # Mesma equipe + seus próprios
                        equipe = funcionario_logado.dados_profissionais.equipe
                        if equipe:
                            funcionarios_equipe = User.objects.filter(
                                funcionario_profile__dados_profissionais__equipe=equipe,
                                funcionario_profile__status=True
                            ).values_list('id', flat=True)
                            user_ids_permitidos = list(funcionarios_equipe)
                        else:
                            user_ids_permitidos = [request.user.id]
                    elif nivel_importancia in [3, 4]:
                        # Seu setor
                        setor = funcionario_logado.dados_profissionais.setor
                        if setor:
                            funcionarios_setor = User.objects.filter(
                                funcionario_profile__dados_profissionais__setor=setor,
                                funcionario_profile__status=True
                            ).values_list('id', flat=True)
                            user_ids_permitidos = list(funcionarios_setor)
                        else:
                            user_ids_permitidos = [request.user.id]
                    elif nivel_importancia == 5:
                        # Seu departamento
                        departamento = funcionario_logado.dados_profissionais.departamento
                        if departamento:
                            funcionarios_dept = User.objects.filter(
                                funcionario_profile__dados_profissionais__departamento=departamento,
                                funcionario_profile__status=True
                            ).values_list('id', flat=True)
                            user_ids_permitidos = list(funcionarios_dept)
                        else:
                            user_ids_permitidos = [request.user.id]
                    elif nivel_importancia in [6, 7]:
                        # Todos (não precisa filtrar por user)
                        user_ids_permitidos = []
        
        # Se não tem permissão, não retorna nada
        if nivel_importancia is None and not request.user.is_superuser:
            return JsonResponse({'success': True, 'data': []})
        
        tabulacoes = TabulacaoCRM.objects.filter(status=True).order_by('ordem')
        
        tabulacoes_data = []
        for tab in tabulacoes:
            # Query base
            controles_query = ControleCRM.objects.filter(
                tabulacao=tab,
                status=True
            ).select_related('user')
            
            # Aplicar filtro de permissão hierárquica
            if nivel_importancia is not None and nivel_importancia < 6 and not request.user.is_superuser:
                if user_ids_permitidos:
                    controles_query = controles_query.filter(user_id__in=user_ids_permitidos)
                else:
                    controles_query = controles_query.none()
            
            # Aplicar filtro de funcionário/vendedor
            if funcionario_id:
                try:
                    controles_query = controles_query.filter(user_id=int(funcionario_id))
                except ValueError:
                    pass
            
            # Aplicar filtro de data
            if data_inicio:
                try:
                    data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                    controles_query = controles_query.filter(data_contato__gte=data_inicio_obj)
                except ValueError:
                    pass
            
            if data_fim:
                try:
                    data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                    controles_query = controles_query.filter(data_contato__lte=data_fim_obj)
                except ValueError:
                    pass
            
            controles = controles_query.order_by('-data_criacao')
            
            cards_data = []
            for controle in controles:
                cliente = Cliente.objects.filter(cpf=controle.cpf, status=True).first()
                
                # Aplicar filtros de nome e CPF do cliente
                if nome_cliente and cliente:
                    if nome_cliente.upper() not in cliente.nome.upper():
                        continue
                
                if cpf_cliente:
                    cpf_limpo_filtro = re.sub(r'\D', '', cpf_cliente)
                    cpf_limpo_controle = re.sub(r'\D', '', controle.cpf)
                    if cpf_limpo_filtro not in cpf_limpo_controle:
                        continue
                
                cards_data.append({
                    'id': controle.id,
                    'cpf': controle.cpf,
                    'nome': cliente.nome if cliente else 'Cliente não encontrado',
                    'data_contato': controle.data_contato.strftime('%d/%m/%Y'),
                    'hora_contato': controle.hora_contato.strftime('%H:%M'),
                    'vendedor': controle.user.username,
                })
            
            tabulacoes_data.append({
                'id': tab.id,
                'nome': tab.nome,
                'ordem': tab.ordem,
                'cor': tab.cor,
                'cards': cards_data,
            })
        
        return JsonResponse({'success': True, 'data': tabulacoes_data})
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao listar kanban: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar kanban: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_criar_tabulacao(request):
    """API POST para criar nova tabulação (apenas superuser)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
    
    try:
        nome = request.POST.get('nome', '').strip().upper()
        ordem = request.POST.get('ordem', '').strip()
        cor = request.POST.get('cor', '#6c757d').strip()
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        if not ordem:
            return JsonResponse({'success': False, 'message': 'Ordem é obrigatória'})
        
        try:
            ordem_int = int(ordem)
        except:
            return JsonResponse({'success': False, 'message': 'Ordem inválida'})
        
        if TabulacaoCRM.objects.filter(nome=nome).exists():
            return JsonResponse({'success': False, 'message': 'Tabulação com este nome já existe'})
        
        tabulacao = TabulacaoCRM.objects.create(
            nome=nome,
            ordem=ordem_int,
            cor=cor,
            status=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Tabulação criada com sucesso!',
            'data': {
                'id': tabulacao.id,
                'nome': tabulacao.nome,
                'ordem': tabulacao.ordem,
                'cor': tabulacao.cor,
            }
        })
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao criar tabulação: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao criar tabulação: {str(e)}'}, status=500)

@login_required
@controle_acess('SS26')
@require_http_methods(["POST"])
def api_mover_card(request):
    """API POST para mover card entre colunas com verificação de permissões e coleta de dados"""
    try:
        from apps.vendas.siape.models import DadosReversao, DadosChecagem, ArquivoReversao, ArquivoChecagem, Representante
        from datetime import datetime
        
        controle_id = request.POST.get('controle_id')
        nova_tabulacao_id = request.POST.get('nova_tabulacao_id')
        
        if not controle_id or not nova_tabulacao_id:
            return JsonResponse({'success': False, 'message': 'Dados incompletos'})
        
        controle = ControleCRM.objects.get(id=controle_id, status=True)
        nova_tabulacao = TabulacaoCRM.objects.get(id=nova_tabulacao_id, status=True)
        
        # Verificar se precisa de dados adicionais (REVERSÃO ou CHECAGEM)
        precisa_dados = False
        tipo_dados = None
        
        if nova_tabulacao.nome.upper() == 'REVERSÃO':
            precisa_dados = True
            tipo_dados = 'REVERSAO'
        elif nova_tabulacao.nome.upper() == 'CHECAGEM':
            precisa_dados = True
            tipo_dados = 'CHECAGEM'
        
        # Se precisa de dados, verificar se foram enviados
        if precisa_dados:
            if tipo_dados == 'REVERSAO':
                data_para_reversao = request.POST.get('data_para_reversao')
                horario_disponivel = request.POST.get('horario_disponivel')
                responsavel_id = request.POST.get('responsavel_por_reversao')
                observacao = request.POST.get('observacao', '').strip()
                
                if not data_para_reversao or not horario_disponivel or not responsavel_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Dados incompletos. Preencha data, horário e responsável.',
                        'precisa_dados': True,
                        'tipo': 'REVERSAO'
                    })
                
                # Validar se a data não é passada
                try:
                    data_reversao_obj = datetime.strptime(data_para_reversao, '%Y-%m-%d').date()
                    hoje = datetime.now().date()
                    if data_reversao_obj < hoje:
                        return JsonResponse({
                            'success': False,
                            'message': 'Não é possível agendar para datas passadas.',
                            'precisa_dados': True,
                            'tipo': 'REVERSAO'
                        })
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Data inválida.',
                        'precisa_dados': True,
                        'tipo': 'REVERSAO'
                    })
                
                # Verificar permissão para mover (apenas responsável, superior hierárquico ou superuser)
                responsavel = User.objects.get(id=responsavel_id)
                pode_mover = verificar_permissao_mover_card(request.user, responsavel)
                
                if not pode_mover:
                    return JsonResponse({
                        'success': False,
                        'message': 'Você não tem permissão para mover este card. Apenas o responsável selecionado, superiores hierárquicos ou superuser podem mover.'
                    }, status=403)
                
                with transaction.atomic():
                    controle.tabulacao = nova_tabulacao
                    controle.save()
                    
                    # Criar ou atualizar dados de reversão
                    dados_reversao, created = DadosReversao.objects.get_or_create(
                        controle=controle,
                        defaults={
                            'data_para_reversao': datetime.strptime(data_para_reversao, '%Y-%m-%d').date(),
                            'horario_disponivel': datetime.strptime(horario_disponivel, '%H:%M').time(),
                            'responsavel_por_reversao': responsavel,
                            'observacao': observacao.upper() if observacao else None,
                        }
                    )
                    
                    if not created:
                        dados_reversao.data_para_reversao = datetime.strptime(data_para_reversao, '%Y-%m-%d').date()
                        dados_reversao.horario_disponivel = datetime.strptime(horario_disponivel, '%H:%M').time()
                        dados_reversao.responsavel_por_reversao = responsavel
                        dados_reversao.observacao = observacao.upper() if observacao else None
                        dados_reversao.save()
                    
                    # Criar horário disponível (sempre criar novo, permitindo múltiplos agendamentos)
                    from apps.vendas.siape.models import HorarioDisponivel
                    data_reversao_obj = datetime.strptime(data_para_reversao, '%Y-%m-%d').date()
                    horario_reversao_obj = datetime.strptime(horario_disponivel, '%H:%M').time()
                    
                    # Verificar se já existe para esta tabulação específica
                    horario_existente = HorarioDisponivel.objects.filter(
                        controle_crm=controle,
                        data=data_reversao_obj,
                        hora=horario_reversao_obj,
                        responsavel=responsavel,
                        tabulacao=nova_tabulacao
                    ).first()
                    
                    if horario_existente:
                        # Se já existe para esta tabulação, apenas atualizar status
                        horario_existente.status = True
                        horario_existente.save()
                    else:
                        # Criar novo agendamento
                        HorarioDisponivel.objects.create(
                            controle_crm=controle,
                            data=data_reversao_obj,
                            hora=horario_reversao_obj,
                            responsavel=responsavel,
                            tabulacao=nova_tabulacao,
                            status=True
                        )
                    
                    # Processar arquivos
                    arquivos = request.FILES.getlist('arquivos_reversao')
                    for arquivo in arquivos:
                        ArquivoReversao.objects.create(
                            reversao=dados_reversao,
                            arquivo=arquivo,
                            titulo=arquivo.name.upper()
                        )
                
                return JsonResponse({'success': True, 'message': 'Card movido para Reversão com sucesso!'})
                
            elif tipo_dados == 'CHECAGEM':
                data_para_checagem = request.POST.get('data_para_checagem')
                horario_disponivel = request.POST.get('horario_disponivel')
                responsavel_id = request.POST.get('responsavel_por_checagem')
                observacao = request.POST.get('observacao', '').strip()
                nome_banco = request.POST.get('nome_banco', '').strip()
                valor_af = request.POST.get('valor_af', '').strip()
                valor_repasse = request.POST.get('valor_repasse', '').strip()
                saldo_devedor = request.POST.get('saldo_devedor', '').strip()
                valor_parcela_atual = request.POST.get('valor_parcela_atual', '').strip()
                valor_parcela_nova_proposta = request.POST.get('valor_parcela_nova_proposta', '').strip()
                valor_troco = request.POST.get('valor_troco', '').strip()
                prazo_atual = request.POST.get('prazo_atual', '').strip()
                prazo_acordado = request.POST.get('prazo_acordado', '').strip()
                
                if not data_para_checagem or not horario_disponivel or not responsavel_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Dados incompletos. Preencha data, horário e responsável.',
                        'precisa_dados': True,
                        'tipo': 'CHECAGEM'
                    })
                
                # Validar se a data não é passada
                try:
                    data_checagem_obj = datetime.strptime(data_para_checagem, '%Y-%m-%d').date()
                    hoje = datetime.now().date()
                    if data_checagem_obj < hoje:
                        return JsonResponse({
                            'success': False,
                            'message': 'Não é possível agendar para datas passadas.',
                            'precisa_dados': True,
                            'tipo': 'CHECAGEM'
                        })
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Data inválida.',
                        'precisa_dados': True,
                        'tipo': 'CHECAGEM'
                    })
                
                # Verificar permissão para mover
                responsavel = User.objects.get(id=responsavel_id)
                pode_mover = verificar_permissao_mover_card(request.user, responsavel)
                
                if not pode_mover:
                    return JsonResponse({
                        'success': False,
                        'message': 'Você não tem permissão para mover este card. Apenas o responsável selecionado, superiores hierárquicos ou superuser podem mover.'
                    }, status=403)
                
                with transaction.atomic():
                    controle.tabulacao = nova_tabulacao
                    controle.save()
                    
                    data_checagem_obj = datetime.strptime(data_para_checagem, '%Y-%m-%d').date()
                    horario_checagem_obj = datetime.strptime(horario_disponivel, '%H:%M').time()
                    
                    # Criar ou atualizar dados de checagem
                    dados_checagem, created = DadosChecagem.objects.get_or_create(
                        controle=controle,
                        defaults={
                            'data_para_checagem': data_checagem_obj,
                            'horario_disponivel': horario_checagem_obj,
                            'responsavel_por_checagem': responsavel,
                            'observacao': observacao.upper() if observacao else None,
                            'nome_banco': nome_banco.upper() if nome_banco else None,
                            'valor_af': float(valor_af) if valor_af else None,
                            'valor_repasse': float(valor_repasse) if valor_repasse else None,
                            'saldo_devedor': float(saldo_devedor) if saldo_devedor else None,
                            'valor_parcela_atual': float(valor_parcela_atual) if valor_parcela_atual else None,
                            'valor_parcela_nova_proposta': float(valor_parcela_nova_proposta) if valor_parcela_nova_proposta else None,
                            'valor_troco': float(valor_troco) if valor_troco else None,
                            'prazo_atual': int(prazo_atual) if prazo_atual else None,
                            'prazo_acordado': int(prazo_acordado) if prazo_acordado else None,
                        }
                    )
                    
                    if not created:
                        dados_checagem.data_para_checagem = data_checagem_obj
                        dados_checagem.horario_disponivel = horario_checagem_obj
                        dados_checagem.responsavel_por_checagem = responsavel
                        dados_checagem.observacao = observacao.upper() if observacao else None
                        dados_checagem.nome_banco = nome_banco.upper() if nome_banco else None
                        dados_checagem.valor_af = float(valor_af) if valor_af else None
                        dados_checagem.valor_repasse = float(valor_repasse) if valor_repasse else None
                        dados_checagem.saldo_devedor = float(saldo_devedor) if saldo_devedor else None
                        dados_checagem.valor_parcela_atual = float(valor_parcela_atual) if valor_parcela_atual else None
                        dados_checagem.valor_parcela_nova_proposta = float(valor_parcela_nova_proposta) if valor_parcela_nova_proposta else None
                        dados_checagem.valor_troco = float(valor_troco) if valor_troco else None
                        dados_checagem.prazo_atual = int(prazo_atual) if prazo_atual else None
                        dados_checagem.prazo_acordado = int(prazo_acordado) if prazo_acordado else None
                        dados_checagem.save()
                    
                    # Criar horário disponível (sempre criar novo, permitindo múltiplos agendamentos)
                    from apps.vendas.siape.models import HorarioDisponivel
                    
                    # Verificar se já existe para esta tabulação específica
                    horario_existente = HorarioDisponivel.objects.filter(
                        controle_crm=controle,
                        data=data_checagem_obj,
                        hora=horario_checagem_obj,
                        responsavel=responsavel,
                        tabulacao=nova_tabulacao
                    ).first()
                    
                    if horario_existente:
                        # Se já existe para esta tabulação, apenas atualizar status
                        horario_existente.status = True
                        horario_existente.save()
                    else:
                        # Criar novo agendamento
                        HorarioDisponivel.objects.create(
                            controle_crm=controle,
                            data=data_checagem_obj,
                            hora=horario_checagem_obj,
                            responsavel=responsavel,
                            tabulacao=nova_tabulacao,
                            status=True
                        )
                    
                    # Processar arquivos
                    arquivos = request.FILES.getlist('arquivos_checagem')
                    for arquivo in arquivos:
                        ArquivoChecagem.objects.create(
                            checagem=dados_checagem,
                            arquivo=arquivo,
                            titulo=arquivo.name.upper()
                        )
                
                return JsonResponse({'success': True, 'message': 'Card movido para Checagem com sucesso!'})
        else:
            # Movimentação normal - verificar se card está em REVERSÃO ou CHECAGEM
            tabulacao_atual = controle.tabulacao
            precisa_verificar_permissao = False
            responsavel_card = None
            
            if tabulacao_atual.nome.upper() == 'REVERSÃO':
                if hasattr(controle, 'dados_reversao'):
                    precisa_verificar_permissao = True
                    responsavel_card = controle.dados_reversao.responsavel_por_reversao
            elif tabulacao_atual.nome.upper() == 'CHECAGEM':
                if hasattr(controle, 'dados_checagem'):
                    precisa_verificar_permissao = True
                    responsavel_card = controle.dados_checagem.responsavel_por_checagem
            
            if precisa_verificar_permissao and responsavel_card:
                pode_mover = verificar_permissao_mover_card(request.user, responsavel_card)
                if not pode_mover:
                    return JsonResponse({
                        'success': False,
                        'message': 'Você não tem permissão para mover este card. Apenas o responsável, superiores hierárquicos ou superuser podem mover.'
                    }, status=403)
            
            controle.tabulacao = nova_tabulacao
            controle.save()
            return JsonResponse({'success': True, 'message': 'Card movido com sucesso!'})
        
    except ControleCRM.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Controle não encontrado'}, status=404)
    except TabulacaoCRM.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tabulação não encontrada'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Responsável não encontrado'}, status=404)
    except Exception as e:
        logger.error(f"[CRM] Erro ao mover card: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao mover card: {str(e)}'}, status=500)

def verificar_permissao_mover_card(user_logado, responsavel_card):
    """Verifica se o usuário logado pode mover o card (responsável, superior hierárquico ou superuser)"""
    if user_logado.is_superuser:
        return True
    
    if user_logado.id == responsavel_card.id:
        return True
    
    # Verificar se é superior hierárquico
    if hasattr(user_logado, 'funcionario_profile') and user_logado.funcionario_profile:
        funcionario_logado = user_logado.funcionario_profile
        if hasattr(funcionario_logado, 'dados_profissionais') and funcionario_logado.dados_profissionais:
            cargo_logado = funcionario_logado.dados_profissionais.cargo
            if cargo_logado and cargo_logado.nivel_hierarquico:
                nivel_logado = cargo_logado.nivel_hierarquico.importancia
                
                if hasattr(responsavel_card, 'funcionario_profile') and responsavel_card.funcionario_profile:
                    funcionario_responsavel = responsavel_card.funcionario_profile
                    if hasattr(funcionario_responsavel, 'dados_profissionais') and funcionario_responsavel.dados_profissionais:
                        cargo_responsavel = funcionario_responsavel.dados_profissionais.cargo
                        if cargo_responsavel and cargo_responsavel.nivel_hierarquico:
                            nivel_responsavel = cargo_responsavel.nivel_hierarquico.importancia
                            if nivel_logado > nivel_responsavel:
                                return True
    
    return False

@login_required
@controle_acess('SS26')
@require_http_methods(["GET"])
def api_listar_representantes(request, tipo):
    """API GET para listar representantes por tipo (REVERSAO ou CHECAGEM)"""
    try:
        from apps.vendas.siape.models import Representante
        
        # Normalizar tipo: REVERSAO ou REVERSÃO -> REVERSAO
        tipo_normalizado = tipo.upper()
        if tipo_normalizado == 'REVERSÃO':
            tipo_normalizado = 'REVERSAO'
        
        if tipo_normalizado not in ['REVERSAO', 'CHECAGEM']:
            logger.error(f"[CRM] Tipo de representante inválido: {tipo}")
            return JsonResponse({'success': False, 'message': 'Tipo de representante inválido. Use REVERSAO ou CHECAGEM.'}, status=400)
        
        representantes = Representante.objects.filter(tipo=tipo_normalizado, status=True).prefetch_related('usuarios')
        
        if not representantes.exists():
            # Se não houver representantes cadastrados, retornar lista vazia (não é erro)
            return JsonResponse({'success': True, 'data': []})
        
        data = []
        for rep in representantes:
            usuarios_data = []
            for user in rep.usuarios.filter(is_active=True):
                try:
                    nome = user.username
                    if hasattr(user, 'funcionario_profile') and user.funcionario_profile:
                        nome = user.funcionario_profile.nome_completo
                    usuarios_data.append({
                        'id': user.id,
                        'username': user.username,
                        'nome': nome,
                        'horario_inicio': rep.horario_inicio.strftime('%H:%M') if rep.horario_inicio else None,
                        'horario_final': rep.horario_final.strftime('%H:%M') if rep.horario_final else None,
                        'tempo_call': rep.tempo_call,
                    })
                except Exception as e:
                    logger.error(f"[CRM] Erro ao processar usuário {user.id} do representante {rep.id}: {str(e)}")
                    continue
            
            data.extend(usuarios_data)
        
        return JsonResponse({'success': True, 'data': data})
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao listar representantes (tipo: {tipo}): {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar representantes: {str(e)}'}, status=500)

@login_required
@controle_acess('SS26')
@require_http_methods(["GET"])
def api_listar_dias_disponiveis(request):
    """API GET para listar dias disponíveis de um responsável (dias com pelo menos um horário livre)"""
    try:
        from apps.vendas.siape.models import HorarioDisponivel, Representante
        from datetime import datetime, timedelta, date
        from django.db.models import Q
        
        responsavel_id = request.GET.get('responsavel_id')
        horario_inicio_str = request.GET.get('horario_inicio')
        horario_final_str = request.GET.get('horario_final')
        tempo_call = int(request.GET.get('tempo_call', 30))
        dias_futuros = int(request.GET.get('dias_futuros', 30))  # Quantos dias à frente buscar
        
        if not responsavel_id or not horario_inicio_str or not horario_final_str:
            return JsonResponse({'success': False, 'message': 'Parâmetros incompletos'}, status=400)
        
        horario_inicio = datetime.strptime(horario_inicio_str, '%H:%M').time()
        horario_final = datetime.strptime(horario_final_str, '%H:%M').time()
        
        hoje = date.today()
        dias_disponiveis = []
        
        # Buscar todos os horários ocupados do responsável nos próximos dias
        data_fim = hoje + timedelta(days=dias_futuros)
        horarios_ocupados = HorarioDisponivel.objects.filter(
            responsavel_id=responsavel_id,
            data__gte=hoje,
            data__lte=data_fim,
            status=True
        ).values_list('data', 'hora', flat=False)
        
        # Agrupar horários ocupados por data
        ocupados_por_data = {}
        for data_ocupada, hora_ocupada in horarios_ocupados:
            if data_ocupada not in ocupados_por_data:
                ocupados_por_data[data_ocupada] = []
            ocupados_por_data[data_ocupada].append(hora_ocupada)
        
        # Converter horários ocupados para minutos
        ocupados_minutos_por_data = {}
        for data_ocupada, horas in ocupados_por_data.items():
            minutos_ocupados = set()
            for hora_ocupada in horas:
                minutos_inicio = hora_ocupada.hour * 60 + hora_ocupada.minute
                # Assumir tempo_call padrão para calcular período ocupado
                for i in range(tempo_call):
                    minutos_ocupados.add(minutos_inicio + i)
            ocupados_minutos_por_data[data_ocupada] = minutos_ocupados
        
        # Verificar cada dia
        inicio_minutos = horario_inicio.hour * 60 + horario_inicio.minute
        final_minutos = horario_final.hour * 60 + horario_final.minute
        
        for i in range(dias_futuros + 1):
            data_atual = hoje + timedelta(days=i)
            minutos_ocupados = ocupados_minutos_por_data.get(data_atual, set())
            
            # Verificar se há pelo menos um slot disponível neste dia
            tem_slot_livre = False
            slot_atual = inicio_minutos
            while slot_atual + tempo_call <= final_minutos:
                slot_livre = True
                for j in range(tempo_call):
                    if (slot_atual + j) in minutos_ocupados:
                        slot_livre = False
                        break
                if slot_livre:
                    tem_slot_livre = True
                    break
                slot_atual += tempo_call
            
            if tem_slot_livre:
                dias_disponiveis.append({
                    'data': data_atual.strftime('%Y-%m-%d'),
                    'display': data_atual.strftime('%d/%m/%Y'),
                    'dia_semana': data_atual.strftime('%A')
                })
        
        return JsonResponse({'success': True, 'data': dias_disponiveis})
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao listar dias disponíveis: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar dias: {str(e)}'}, status=500)

@login_required
@controle_acess('SS26')
@require_http_methods(["GET"])
def api_listar_horarios_disponiveis(request):
    """API GET para listar horários disponíveis de um responsável em uma data específica"""
    try:
        from apps.vendas.siape.models import HorarioDisponivel
        from datetime import datetime, timedelta
        
        responsavel_id = request.GET.get('responsavel_id')
        data_str = request.GET.get('data')
        tabulacao_id = request.GET.get('tabulacao_id')
        horario_inicio_str = request.GET.get('horario_inicio')
        horario_final_str = request.GET.get('horario_final')
        tempo_call = int(request.GET.get('tempo_call', 30))
        
        if not responsavel_id or not data_str or not tabulacao_id or not horario_inicio_str or not horario_final_str:
            return JsonResponse({'success': False, 'message': 'Parâmetros incompletos'}, status=400)
        
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
        horario_inicio = datetime.strptime(horario_inicio_str, '%H:%M').time()
        horario_final = datetime.strptime(horario_final_str, '%H:%M').time()
        
        # Buscar horários já agendados para este responsável nesta data
        # IMPORTANTE: Buscar TODOS os horários ocupados com status=True
        controle_id = request.GET.get('controle_id', '')
        
        # Primeiro, buscar TODOS os horários ocupados para debug
        todos_horarios = HorarioDisponivel.objects.filter(
            responsavel_id=responsavel_id,
            data=data
        ).values_list('hora', 'controle_crm_id', 'status', 'tabulacao_id', flat=False)
        
        logger.info(f"[CRM] TODOS os horários no banco para responsável {responsavel_id} na data {data}: {[(str(h[0]), h[1], h[2], h[3]) for h in todos_horarios]}")
        
        # Buscar apenas os ativos
        horarios_ocupados_query = HorarioDisponivel.objects.filter(
            responsavel_id=responsavel_id,
            data=data,
            status=True
        )
        
        # Se estiver editando (controle_id fornecido E tabulação_id fornecida), 
        # excluir apenas o horário do controle atual para a mesma tabulação
        if controle_id and tabulacao_id:
            try:
                controle_atual = ControleCRM.objects.get(id=controle_id)
                # Excluir apenas se for a mesma tabulação (editando o mesmo agendamento)
                if controle_atual.tabulacao_id == int(tabulacao_id):
                    horarios_ocupados_query = horarios_ocupados_query.exclude(
                        controle_crm_id=controle_id,
                        tabulacao_id=tabulacao_id
                    )
                    logger.info(f"[CRM] Excluindo controle_id {controle_id} e tabulação {tabulacao_id} da busca (editando mesmo agendamento)")
                else:
                    # Se for tabulação diferente, não excluir (pode ter múltiplos agendamentos)
                    logger.info(f"[CRM] Mantendo controle_id {controle_id} na busca (tabulação diferente: {controle_atual.tabulacao_id} != {tabulacao_id})")
            except ControleCRM.DoesNotExist:
                logger.warning(f"[CRM] Controle {controle_id} não encontrado, buscando todos os horários")
            except ValueError:
                logger.warning(f"[CRM] Erro ao converter tabulacao_id {tabulacao_id}, buscando todos os horários")
        
        # Buscar horários ocupados com seus respectivos tempo_call
        horarios_ocupados_list = list(horarios_ocupados_query.values_list('hora', 'controle_crm_id', flat=False))
        horarios_ocupados = [h[0] for h in horarios_ocupados_list]
        
        logger.info(f"[CRM] Buscando horários disponíveis para responsável {responsavel_id} na data {data}")
        logger.info(f"[CRM] Total de horários ocupados encontrados (status=True): {len(horarios_ocupados_list)}")
        logger.info(f"[CRM] Horários ocupados (hora, controle_id): {[(str(h[0]), h[1]) for h in horarios_ocupados_list]}")
        logger.info(f"[CRM] Controle ID sendo excluído: {controle_id}")
        
        if len(horarios_ocupados) == 0:
            logger.warning(f"[CRM] ATENÇÃO: Nenhum horário ocupado encontrado! Verifique se o responsavel_id ({responsavel_id}) e data ({data}) estão corretos.")
        
        # Converter horários ocupados para minutos desde meia-noite para facilitar comparação
        # Considerar o período completo de cada call agendado
        horarios_ocupados_minutos = set()
        for hora_ocupada in horarios_ocupados:
            minutos_inicio = hora_ocupada.hour * 60 + hora_ocupada.minute
            # Adicionar todos os minutos dentro do período de call (do início até início + tempo_call)
            # Usar o tempo_call passado como parâmetro (assumindo que todos os agendamentos usam o mesmo tempo_call)
            for i in range(tempo_call):
                horarios_ocupados_minutos.add(minutos_inicio + i)
        
        logger.info(f"[CRM] Minutos ocupados: {sorted(horarios_ocupados_minutos)}")
        logger.info(f"[CRM] Tempo de call: {tempo_call} minutos")
        
        # Gerar slots disponíveis
        horarios_disponiveis = []
        inicio_minutos = horario_inicio.hour * 60 + horario_inicio.minute
        final_minutos = horario_final.hour * 60 + horario_final.minute
        
        slot_atual = inicio_minutos
        while slot_atual + tempo_call <= final_minutos:
            # Verificar se este slot está livre
            # Um slot está livre se NENHUM dos minutos do período está ocupado
            slot_livre = True
            minutos_conflitantes = []
            for i in range(tempo_call):
                minuto_verificar = slot_atual + i
                if minuto_verificar in horarios_ocupados_minutos:
                    slot_livre = False
                    minutos_conflitantes.append(minuto_verificar)
            
            horas = slot_atual // 60
            minutos = slot_atual % 60
            horario_str = f"{horas:02d}:{minutos:02d}"
            
            if slot_livre:
                horarios_disponiveis.append({
                    'hora': horario_str,
                    'display': horario_str
                })
            else:
                # Log detalhado para debug
                horas_conflito = [m // 60 for m in minutos_conflitantes]
                minutos_conflito = [m % 60 for m in minutos_conflitantes]
                logger.info(f"[CRM] Slot {horario_str} (minutos {slot_atual}-{slot_atual + tempo_call - 1}) OCUPADO")
                logger.info(f"[CRM]   - Minutos conflitantes: {minutos_conflitantes}")
                logger.info(f"[CRM]   - Horários conflitantes: {[f'{h:02d}:{m:02d}' for h, m in zip(horas_conflito, minutos_conflito)]}")
            
            slot_atual += tempo_call
        
        logger.info(f"[CRM] Total de horários disponíveis gerados: {len(horarios_disponiveis)}")
        logger.info(f"[CRM] Horários disponíveis: {[h['hora'] for h in horarios_disponiveis]}")
        
        return JsonResponse({'success': True, 'data': horarios_disponiveis})
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao listar horários disponíveis: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar horários: {str(e)}'}, status=500)

@login_required
@controle_acess('SS26')
@require_http_methods(["GET"])
def api_listar_funcionarios(request):
    """API GET para listar funcionários/vendedores para filtro"""
    try:
        from apps.rh.funcionarios.models import Funcionario
        
        # Obter nível hierárquico do usuário logado
        nivel_importancia = None
        funcionario_logado = None
        funcionarios_permitidos = []
        
        if request.user.is_superuser:
            # Superuser vê todos
            funcionarios = Funcionario.objects.filter(
                status=True,
                usuario__isnull=False
            ).select_related('usuario', 'dados_profissionais__cargo__nivel_hierarquico').order_by('nome_completo')
        elif hasattr(request.user, 'funcionario_profile') and request.user.funcionario_profile:
            funcionario_logado = request.user.funcionario_profile
            if hasattr(funcionario_logado, 'dados_profissionais') and funcionario_logado.dados_profissionais:
                cargo = funcionario_logado.dados_profissionais.cargo
                if cargo and cargo.nivel_hierarquico:
                    nivel_importancia = cargo.nivel_hierarquico.importancia
                    
                    # Aplicar filtros baseados no nível hierárquico
                    if nivel_importancia in [0, 1]:
                        # Apenas ele mesmo
                        funcionarios_permitidos = [funcionario_logado]
                    elif nivel_importancia == 2:
                        # Mesma equipe + ele mesmo
                        equipe = funcionario_logado.dados_profissionais.equipe
                        if equipe:
                            funcionarios_permitidos = Funcionario.objects.filter(
                                dados_profissionais__equipe=equipe,
                                status=True,
                                usuario__isnull=False
                            )
                        else:
                            funcionarios_permitidos = [funcionario_logado]
                    elif nivel_importancia in [3, 4]:
                        # Seu setor
                        setor = funcionario_logado.dados_profissionais.setor
                        if setor:
                            funcionarios_permitidos = Funcionario.objects.filter(
                                dados_profissionais__setor=setor,
                                status=True,
                                usuario__isnull=False
                            )
                        else:
                            funcionarios_permitidos = [funcionario_logado]
                    elif nivel_importancia == 5:
                        # Seu departamento
                        departamento = funcionario_logado.dados_profissionais.departamento
                        if departamento:
                            funcionarios_permitidos = Funcionario.objects.filter(
                                dados_profissionais__departamento=departamento,
                                status=True,
                                usuario__isnull=False
                            )
                        else:
                            funcionarios_permitidos = [funcionario_logado]
                    elif nivel_importancia in [6, 7]:
                        # Todos
                        funcionarios_permitidos = Funcionario.objects.filter(
                            status=True,
                            usuario__isnull=False
                        )
        
        if request.user.is_superuser:
            funcionarios = Funcionario.objects.filter(
                status=True,
                usuario__isnull=False
            ).select_related('usuario', 'dados_profissionais__cargo__nivel_hierarquico').order_by('nome_completo')
        else:
            if funcionarios_permitidos:
                if isinstance(funcionarios_permitidos, list):
                    funcionarios = Funcionario.objects.filter(
                        id__in=[f.id for f in funcionarios_permitidos],
                        status=True,
                        usuario__isnull=False
                    ).select_related('usuario', 'dados_profissionais__cargo__nivel_hierarquico').order_by('nome_completo')
                else:
                    funcionarios = funcionarios_permitidos.select_related('usuario', 'dados_profissionais__cargo__nivel_hierarquico').order_by('nome_completo')
            else:
                funcionarios = Funcionario.objects.none()
        
        data = []
        for func in funcionarios:
            if func.usuario:
                data.append({
                    'id': func.usuario.id,
                    'nome': func.nome_completo,
                    'username': func.usuario.username,
                })
        
        return JsonResponse({'success': True, 'data': data})
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao listar funcionários: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao listar funcionários: {str(e)}'}, status=500)

@login_required
@controle_acess('SS26')
@require_http_methods(["GET"])
def api_ficha_cliente(request, cpf):
    """API GET para buscar ficha completa do cliente por CPF"""
    try:
        from django.db.models import Prefetch
        from apps.vendas.siape.models import Matricula, Margens, Contrato, DadosReversao, DadosChecagem, ArquivoReversao, ArquivoChecagem
        
        cpf_limpo = re.sub(r'\D', '', cpf)
        cliente = Cliente.objects.prefetch_related(
            Prefetch(
                'matriculas',
                queryset=Matricula.objects.filter(status=True).select_related('campanha').prefetch_related(
                    'margens',
                    Prefetch('contratos', queryset=Contrato.objects.select_related('campanha'))
                )
            )
        ).filter(cpf=cpf_limpo, status=True).first()
        
        if not cliente:
            return JsonResponse({'success': False, 'message': 'Cliente não encontrado'}, status=404)
        
        dados_pessoais = {
            'id': cliente.id,
            'nome': cliente.nome,
            'cpf': cliente.cpf,
            'uf': cliente.uf or '',
            'situacao_funcional': cliente.situacao_funcional or '',
            'tipo_base': cliente.tipo_base or '',
        }
        
        matriculas_data = []
        for matricula in cliente.matriculas.all():
            margens = matricula.margens if hasattr(matricula, 'margens') else None
            contratos = matricula.contratos.all()
            
            matriculas_data.append({
                'id': matricula.id,
                'matricula': matricula.matricula,
                'matricula_instituidor': matricula.matricula_instituidor or '',
                'orgao': matricula.orgao or '',
                'upag': matricula.upag or '',
                'base_calculo': float(matricula.base_calculo) if matricula.base_calculo else 0,
                'rjur': matricula.rjur or '',
                'campanha': matricula.campanha.titulo,
                'qtd_contratos': contratos.count(),
                'margens': {
                    'bruta_5': float(margens.bruta_5) if margens and margens.bruta_5 else 0,
                    'util_5': float(margens.util_5) if margens and margens.util_5 else 0,
                    'saldo_5': float(margens.saldo_5) if margens and margens.saldo_5 else 0,
                    'bruta_5b': float(margens.bruta_5b) if margens and margens.bruta_5b else 0,
                    'util_5b': float(margens.util_5b) if margens and margens.util_5b else 0,
                    'saldo_5b': float(margens.saldo_5b) if margens and margens.saldo_5b else 0,
                    'bruta_35': float(margens.bruta_35) if margens and margens.bruta_35 else 0,
                    'util_35': float(margens.util_35) if margens and margens.util_35 else 0,
                    'saldo_35': float(margens.saldo_35) if margens and margens.saldo_35 else 0,
                } if margens else {
                    'bruta_5': 0, 'util_5': 0, 'saldo_5': 0,
                    'bruta_5b': 0, 'util_5b': 0, 'saldo_5b': 0,
                    'bruta_35': 0, 'util_35': 0, 'saldo_35': 0,
                },
                'contratos': [{
                    'id': contrato.id,
                    'contrato': contrato.contrato,
                    'tipo_contrato': contrato.tipo_contrato or '',
                    'banco': contrato.banco or '',
                    'valor_parcela': float(contrato.valor_parcela) if contrato.valor_parcela else 0,
                    'parcelas_restantes': contrato.parcelas_restantes or 0,
                    'campanha': contrato.campanha.titulo,
                } for contrato in contratos],
            })
        
        # Buscar dados de Reversão ou Checagem se o controle estiver nessas tabulações
        dados_reversao = None
        dados_checagem = None
        
        controle_crm = ControleCRM.objects.filter(
            cpf=cpf_limpo,
            status=True
        ).select_related('tabulacao').first()
        
        if controle_crm:
            tabulacao_nome = controle_crm.tabulacao.nome.upper() if controle_crm.tabulacao else ''
            # Normalizar: REVERSÃO -> REVERSAO
            if tabulacao_nome == 'REVERSÃO':
                tabulacao_nome = 'REVERSAO'
            
            if tabulacao_nome == 'REVERSAO':
                try:
                    # Usar getattr para evitar erro se não existir
                    if hasattr(controle_crm, 'dados_reversao'):
                        reversao = controle_crm.dados_reversao
                        responsavel_nome = reversao.responsavel_por_reversao.username
                        if hasattr(reversao.responsavel_por_reversao, 'funcionario_profile') and reversao.responsavel_por_reversao.funcionario_profile:
                            responsavel_nome = reversao.responsavel_por_reversao.funcionario_profile.nome_completo
                        
                        arquivos = []
                        for arquivo in reversao.arquivos.all():
                            arquivos.append({
                                'id': arquivo.id,
                                'url': arquivo.arquivo.url,
                                'titulo': arquivo.titulo or arquivo.arquivo.name,
                            })
                        
                        dados_reversao = {
                            'data_para_reversao': reversao.data_para_reversao.strftime('%d/%m/%Y') if reversao.data_para_reversao else '',
                            'horario_disponivel': reversao.horario_disponivel.strftime('%H:%M') if reversao.horario_disponivel else '',
                            'responsavel_nome': responsavel_nome,
                            'responsavel_id': reversao.responsavel_por_reversao.id,
                            'observacao': reversao.observacao or '',
                            'arquivos': arquivos,
                            'data_criacao': reversao.data_criacao.strftime('%d/%m/%Y %H:%M') if reversao.data_criacao else '',
                        }
                except Exception as e:
                    logger.error(f"[CRM] Erro ao buscar dados de reversão: {str(e)}", exc_info=True)
            
            elif tabulacao_nome == 'CHECAGEM':
                try:
                    # Usar getattr para evitar erro se não existir
                    if hasattr(controle_crm, 'dados_checagem'):
                        checagem = controle_crm.dados_checagem
                        responsavel_nome = checagem.responsavel_por_checagem.username
                        if hasattr(checagem.responsavel_por_checagem, 'funcionario_profile') and checagem.responsavel_por_checagem.funcionario_profile:
                            responsavel_nome = checagem.responsavel_por_checagem.funcionario_profile.nome_completo
                        
                        arquivos = []
                        for arquivo in checagem.arquivos.all():
                            arquivos.append({
                                'id': arquivo.id,
                                'url': arquivo.arquivo.url,
                                'titulo': arquivo.titulo or arquivo.arquivo.name,
                            })
                        
                        dados_checagem = {
                            'data_para_checagem': checagem.data_para_checagem.strftime('%d/%m/%Y') if checagem.data_para_checagem else '',
                            'horario_disponivel': checagem.horario_disponivel.strftime('%H:%M') if checagem.horario_disponivel else '',
                            'responsavel_nome': responsavel_nome,
                            'responsavel_id': checagem.responsavel_por_checagem.id,
                            'observacao': checagem.observacao or '',
                            'nome_banco': checagem.nome_banco or '',
                            'valor_af': float(checagem.valor_af) if checagem.valor_af else None,
                            'valor_repasse': float(checagem.valor_repasse) if checagem.valor_repasse else None,
                            'saldo_devedor': float(checagem.saldo_devedor) if checagem.saldo_devedor else None,
                            'valor_parcela_atual': float(checagem.valor_parcela_atual) if checagem.valor_parcela_atual else None,
                            'valor_parcela_nova_proposta': float(checagem.valor_parcela_nova_proposta) if checagem.valor_parcela_nova_proposta else None,
                            'valor_troco': float(checagem.valor_troco) if checagem.valor_troco else None,
                            'prazo_atual': checagem.prazo_atual,
                            'prazo_acordado': checagem.prazo_acordado,
                            'arquivos': arquivos,
                            'data_criacao': checagem.data_criacao.strftime('%d/%m/%Y %H:%M') if checagem.data_criacao else '',
                        }
                except Exception as e:
                    logger.error(f"[CRM] Erro ao buscar dados de checagem: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': True,
            'data': {
                'dados_pessoais': dados_pessoais,
                'matriculas': matriculas_data,
                'dados_reversao': dados_reversao,
                'dados_checagem': dados_checagem,
            }
        })
        
    except Exception as e:
        logger.error(f"[CRM] Erro ao buscar cliente: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Erro ao buscar cliente: {str(e)}'}, status=500)
