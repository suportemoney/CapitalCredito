"""
APIs para relatório de presença
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, time
from apps.rh.ponto.models import RegistroPonto, Justificativa, ConfiguracaoHorarioFuncionario
from apps.rh.funcionarios.models import Funcionario
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS42')
@require_http_methods(["GET"])
def api_relatorio_presenca(request):
    """API para gerar relatório de presença"""
    try:
        data_inicio_str = request.GET.get('data_inicio', '').strip()
        data_fim_str = request.GET.get('data_fim', '').strip()
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        if not data_inicio_str:
            return JsonResponse({'success': False, 'message': 'Data início é obrigatória'})
        if not data_fim_str:
            return JsonResponse({'success': False, 'message': 'Data fim é obrigatória'})
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except:
            return JsonResponse({'success': False, 'message': 'Formato de data inválido'})
        if data_fim < data_inicio:
            return JsonResponse({'success': False, 'message': 'Data fim não pode ser anterior à data início'})
        funcionarios = Funcionario.objects.filter(status=True)
        if funcionario_id:
            funcionarios = funcionarios.filter(id=funcionario_id)
        funcionarios = funcionarios.order_by('nome_completo')
        resultado = []
        data_atual = data_inicio
        while data_atual <= data_fim:
            for funcionario in funcionarios:
                data_admissao = None
                try:
                    dados_profissionais = funcionario.dados_profissionais
                    data_admissao = dados_profissionais.data_admissao
                except:
                    pass
                antes_admissao = data_admissao and data_atual < data_admissao
                registros_dia = RegistroPonto.objects.filter(
                    funcionario=funcionario,
                    data=data_atual,
                    status=True
                ).order_by('data_hora')
                justificativas_dia = Justificativa.objects.filter(
                    funcionario=funcionario,
                    data_inicio__lte=data_atual,
                    data_fim__gte=data_atual,
                    status=True
                )
                tem_justificativa = justificativas_dia.exists()
                tipo_justificativa = None
                motivo_justificativa = None
                if tem_justificativa:
                    j = justificativas_dia.first()
                    tipo_justificativa = j.get_tipo_display()
                    motivo_justificativa = (j.titulo or '') + (f' - {j.observacoes}' if j.observacoes else '')
                bateu_ponto = registros_dia.exists()
                entrada1_reg = None
                saida1_reg = None
                entrada2_reg = None
                saida2_reg = None
                for reg in registros_dia:
                    data_hora_local = timezone.localtime(reg.data_hora)
                    if reg.tipo == RegistroPonto.TIPO_ENTRADA and reg.numero == 1:
                        entrada1_reg = data_hora_local.time()
                    elif reg.tipo == RegistroPonto.TIPO_SAIDA and reg.numero == 1:
                        saida1_reg = data_hora_local.time()
                    elif reg.tipo == RegistroPonto.TIPO_ENTRADA and reg.numero == 2:
                        entrada2_reg = data_hora_local.time()
                    elif reg.tipo == RegistroPonto.TIPO_SAIDA and reg.numero == 2:
                        saida2_reg = data_hora_local.time()
                entrada1_str = entrada1_reg.strftime('%H:%M') if entrada1_reg else '-'
                saida1_str = saida1_reg.strftime('%H:%M') if saida1_reg else '-'
                entrada2_str = entrada2_reg.strftime('%H:%M') if entrada2_reg else '-'
                saida2_str = saida2_reg.strftime('%H:%M') if saida2_reg else '-'
                horario_total_segundos = 0
                if entrada1_reg and saida1_reg:
                    diff1 = datetime.combine(data_atual, saida1_reg) - datetime.combine(data_atual, entrada1_reg)
                    horario_total_segundos += diff1.total_seconds()
                if entrada2_reg and saida2_reg:
                    diff2 = datetime.combine(data_atual, saida2_reg) - datetime.combine(data_atual, entrada2_reg)
                    horario_total_segundos += diff2.total_seconds()
                horas_trabalhadas = int(horario_total_segundos // 3600)
                minutos_trabalhados = int((horario_total_segundos % 3600) // 60)
                horario_total_str = f"{horas_trabalhadas:02d}:{minutos_trabalhados:02d}" if horario_total_segundos > 0 else '-'
                dia_semana_num = data_atual.weekday()
                dias_semana_map = {0: 'SEGUNDA', 1: 'TERCA', 2: 'QUARTA', 3: 'QUINTA', 4: 'SEXTA', 5: 'SABADO', 6: 'DOMINGO'}
                dia_semana_nome = dias_semana_map.get(dia_semana_num, '')
                horario_esperado_segundos = 0
                if not antes_admissao:
                    try:
                        config = ConfiguracaoHorarioFuncionario.objects.get(funcionario=funcionario, status=True)
                        if config.horarios_por_dia and dia_semana_nome in config.horarios_por_dia:
                            horario_dia = config.horarios_por_dia[dia_semana_nome]
                            entrada1_esp = None
                            saida1_esp = None
                            entrada2_esp = None
                            saida2_esp = None
                            if horario_dia.get('entrada1'):
                                entrada1_esp = datetime.strptime(horario_dia['entrada1'], '%H:%M').time()
                            if horario_dia.get('saida1'):
                                saida1_esp = datetime.strptime(horario_dia['saida1'], '%H:%M').time()
                            if horario_dia.get('entrada2'):
                                entrada2_esp = datetime.strptime(horario_dia['entrada2'], '%H:%M').time()
                            if horario_dia.get('saida2'):
                                saida2_esp = datetime.strptime(horario_dia['saida2'], '%H:%M').time()
                            if entrada1_esp and saida1_esp:
                                diff1_esp = datetime.combine(data_atual, saida1_esp) - datetime.combine(data_atual, entrada1_esp)
                                horario_esperado_segundos += diff1_esp.total_seconds()
                            if entrada2_esp and saida2_esp:
                                diff2_esp = datetime.combine(data_atual, saida2_esp) - datetime.combine(data_atual, entrada2_esp)
                                horario_esperado_segundos += diff2_esp.total_seconds()
                    except ConfiguracaoHorarioFuncionario.DoesNotExist:
                        pass
                horas_esperadas = int(horario_esperado_segundos // 3600)
                minutos_esperados = int((horario_esperado_segundos % 3600) // 60)
                horario_esperado_str = f"{horas_esperadas:02d}:{minutos_esperados:02d}" if horario_esperado_segundos > 0 else '-'
                if antes_admissao:
                    horario_faltando_str = '-'
                else:
                    horario_faltando_segundos = horario_esperado_segundos - horario_total_segundos
                    horas_faltando = int(abs(horario_faltando_segundos) // 3600)
                    minutos_faltando = int((abs(horario_faltando_segundos) % 3600) // 60)
                    if horario_faltando_segundos > 0:
                        horario_faltando_str = f"-{horas_faltando:02d}:{minutos_faltando:02d}"
                    elif horario_faltando_segundos < 0:
                        horario_faltando_str = f"+{horas_faltando:02d}:{minutos_faltando:02d}"
                    else:
                        horario_faltando_str = '-'
                resultado.append({
                    'data': data_atual.strftime('%d/%m/%Y'),
                    'funcionario_id': funcionario.id,
                    'funcionario_nome': funcionario.nome_completo,
                    'funcionario_cpf': funcionario.cpf or '',
                    'chave_pix': funcionario.chave_pix or '',
                    'bateu_ponto': bateu_ponto,
                    'tem_justificativa': tem_justificativa,
                    'tipo_justificativa': tipo_justificativa,
                    'motivo_justificativa': motivo_justificativa or '',
                    'entrada1': entrada1_str,
                    'saida1': saida1_str,
                    'entrada2': entrada2_str,
                    'saida2': saida2_str,
                    'horario_total': horario_total_str,
                    'horario_esperado': horario_esperado_str,
                    'horario_faltando': horario_faltando_str,
                })
            data_atual += timedelta(days=1)
        return JsonResponse({
            'success': True,
            'data': resultado,
            'data_inicio': data_inicio.strftime('%d/%m/%Y'),
            'data_fim': data_fim.strftime('%d/%m/%Y'),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao gerar relatório: {str(e)}'})
