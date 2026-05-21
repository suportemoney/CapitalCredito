"""
APIs para consulta de clientes
"""
import re
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import Cliente, Matricula, Margens, Contrato, Campanha

@login_required
# @controle_acess('SS25')  # TEMPORARIAMENTE DESABILITADO PARA DEBUG
@require_http_methods(["GET"])
def api_buscar_clientes(request):
    """API GET para buscar cliente por CPF e retornar detalhes completos diretamente"""
    try:
        busca = request.GET.get('busca', '').strip()
        campanha_id = request.GET.get('campanha_id', '').strip()
        
        if not busca:
            return JsonResponse({'success': False, 'message': 'Digite um CPF para buscar'}, status=400)
        
        cpf_limpo = re.sub(r'\D', '', busca)
        if len(cpf_limpo) != 11:
            return JsonResponse({'success': False, 'message': 'CPF deve conter 11 dígitos'}, status=400)
        
        # Buscar cliente apenas por CPF (sem filtro de status ou matrículas)
        cliente = Cliente.objects.filter(cpf=cpf_limpo).first()
        
        if not cliente:
            return JsonResponse({'success': False, 'message': 'Cliente não encontrado'}, status=404)
        
        # Verificar se cliente está ativo
        if not cliente.status:
            return JsonResponse({'success': False, 'message': 'Cliente encontrado mas está inativo'}, status=404)
        
        # Filtrar matrículas: se especificou campanha, filtra por ela; senão mostra TODAS as matrículas ativas
        matriculas_query = Matricula.objects.filter(cliente=cliente, status=True)
        
        if campanha_id:
            # Se especificou campanha, filtrar por ela
            matriculas_query = matriculas_query.filter(campanha_id=campanha_id)
        # Se não especificou campanha (campanha_id vazio), mostra TODAS as matrículas ativas do cliente
        
        # Buscar cliente com matrículas filtradas (mesmo que não tenha matrículas, ainda retorna o cliente)
        cliente = Cliente.objects.prefetch_related(
            Prefetch(
                'matriculas',
                queryset=matriculas_query.select_related('campanha').prefetch_related(
                    'margens',
                    Prefetch('contratos', queryset=Contrato.objects.select_related('campanha'))
                )
            )
        ).get(id=cliente.id)
        
        dados_pessoais = {
            'id': cliente.id,
            'nome': cliente.nome,
            'cpf': cliente.cpf,
            'uf': cliente.uf or '',
            'situacao_funcional': cliente.situacao_funcional or '',
            'tipo_base': cliente.tipo_base or '',
            'celular': getattr(cliente, 'celular', None) or '',
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
        
        return JsonResponse({
            'success': True,
            'data': {
                'dados_pessoais': dados_pessoais,
                'matriculas': matriculas_data,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar cliente: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["GET"])
def api_detalhes_cliente(request, cliente_id):
    """API GET para buscar detalhes completos do cliente"""
    try:
        cliente = Cliente.objects.prefetch_related(
            Prefetch(
                'matriculas',
                queryset=Matricula.objects.filter(status=True).select_related('campanha').prefetch_related(
                    'margens',
                    Prefetch('contratos', queryset=Contrato.objects.select_related('campanha'))
                )
            )
        ).get(id=cliente_id, status=True)
        
        dados_pessoais = {
            'nome': cliente.nome,
            'cpf': cliente.cpf,
            'uf': cliente.uf or '',
            'situacao_funcional': cliente.situacao_funcional or '',
            'tipo_base': cliente.tipo_base or '',
            'celular': getattr(cliente, 'celular', None) or '',
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
        
        return JsonResponse({
            'success': True,
            'data': {
                'dados_pessoais': dados_pessoais,
                'matriculas': matriculas_data,
            }
        })
        
    except Cliente.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cliente não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar detalhes: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["GET"])
def api_listar_campanhas_ativas(request):
    """API GET para listar apenas campanhas ativas"""
    try:
        campanhas = Campanha.objects.filter(status=True).order_by('-data_criacao')
        data = [{
            'id': camp.id,
            'titulo': camp.titulo,
        } for camp in campanhas]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar campanhas: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["POST"])
def api_adicionar_contato(request, cliente_id):
    """API POST para adicionar/atualizar celular do cliente"""
    try:
        cliente = Cliente.objects.get(id=cliente_id, status=True)
        
        celular = request.POST.get('celular', '').strip()
        
        # Limpar celular (remover caracteres não numéricos)
        celular_limpo = re.sub(r'\D', '', celular)
        
        if not celular_limpo:
            return JsonResponse({'success': False, 'message': 'Celular é obrigatório'}, status=400)
        
        if len(celular_limpo) < 10 or len(celular_limpo) > 11:
            return JsonResponse({'success': False, 'message': 'Celular deve conter 10 ou 11 dígitos'}, status=400)
        
        cliente.celular = celular_limpo
        cliente.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Contato adicionado com sucesso!',
            'celular': cliente.celular
        })
        
    except Cliente.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cliente não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao adicionar contato: {str(e)}'}, status=500)

