"""
APIs para configuração de horário de trabalho
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from apps.rh.ponto.models import ConfiguracaoHorarioFuncionario
from apps.rh.funcionarios.models import Funcionario, HorarioTrabalho
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS43')
@require_http_methods(["POST"])
def api_configurar_horario(request):
    """API para configurar horário de trabalho do funcionário (individual ou em lote)"""
    try:
        funcionarios_ids = request.POST.getlist('funcionarios_ids[]')
        horarios_por_dia_str = request.POST.get('horarios_por_dia', '{}').strip()
        if not funcionarios_ids or len(funcionarios_ids) == 0:
            return JsonResponse({'success': False, 'message': 'Selecione pelo menos um funcionário'})
        try:
            horarios_por_dia = json.loads(horarios_por_dia_str) if horarios_por_dia_str else {}
        except:
            horarios_por_dia = {}
        for dia, horarios in horarios_por_dia.items():
            entrada1 = horarios.get('entrada1')
            saida1 = horarios.get('saida1')
            entrada2 = horarios.get('entrada2')
            saida2 = horarios.get('saida2')
            if not entrada1 or not saida1:
                return JsonResponse({'success': False, 'message': f'Preencha pelo menos Entrada 1 e Saída 1 para {dia}'})
            if (entrada2 and not saida2) or (not entrada2 and saida2):
                return JsonResponse({'success': False, 'message': f'Para {dia}, se preencher Entrada 2, deve preencher Saída 2 também (ou deixe ambos vazios)'})
        funcionarios_processados = []
        funcionarios_nao_encontrados = []
        for funcionario_id in funcionarios_ids:
            try:
                funcionario = Funcionario.objects.get(id=funcionario_id, status=True)
                trabalha_fim_semana_str = request.POST.get(f'trabalha_fim_semana[{funcionario_id}]', 'false').strip().lower()
                trabalha_fim_semana = trabalha_fim_semana_str == 'true'
                configuracao, created = ConfiguracaoHorarioFuncionario.objects.update_or_create(
                    funcionario=funcionario,
                    defaults={
                        'horario_trabalho': None,
                        'trabalha_fim_semana': trabalha_fim_semana,
                        'horarios_por_dia': horarios_por_dia,
                        'status': True,
                    }
                )
                funcionarios_processados.append({
                    'id': configuracao.id,
                    'funcionario': funcionario.nome_completo,
                    'acao': 'criada' if created else 'atualizada'
                })
            except Funcionario.DoesNotExist:
                funcionarios_nao_encontrados.append(funcionario_id)
        if funcionarios_nao_encontrados:
            return JsonResponse({'success': False, 'message': f'Funcionário(s) não encontrado(s): {", ".join(funcionarios_nao_encontrados)}'})
        if len(funcionarios_processados) == 1:
            mensagem = f'Configuração de horário {funcionarios_processados[0]["acao"]} com sucesso para {funcionarios_processados[0]["funcionario"]}!'
        else:
            mensagem = f'Configuração de horário aplicada com sucesso para {len(funcionarios_processados)} funcionário(s)!'
        return JsonResponse({
            'success': True,
            'message': mensagem,
            'data': {
                'funcionarios_processados': funcionarios_processados,
                'horarios_por_dia': horarios_por_dia,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao configurar horário: {str(e)}'})

@login_required
@controle_acess('SS43')
@require_http_methods(["GET"])
def api_buscar_configuracao(request):
    """API para buscar configuração de horário existente"""
    try:
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório'})
        try:
            configuracao = ConfiguracaoHorarioFuncionario.objects.get(funcionario_id=funcionario_id, status=True)
            return JsonResponse({
                'success': True,
                'data': {
                    'id': configuracao.id,
                    'funcionario_id': configuracao.funcionario.id,
                    'horario_trabalho_id': configuracao.horario_trabalho.id if configuracao.horario_trabalho else None,
                    'trabalha_fim_semana': configuracao.trabalha_fim_semana,
                    'horarios_por_dia': configuracao.horarios_por_dia or {},
                }
            })
        except ConfiguracaoHorarioFuncionario.DoesNotExist:
            return JsonResponse({
                'success': True,
                'data': None
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar configuração: {str(e)}'})
