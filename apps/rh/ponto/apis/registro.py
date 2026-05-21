"""
APIs para registro de ponto
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, date
from apps.rh.ponto.models import RegistroPonto, Justificativa, JustificativaArquivo
from apps.rh.funcionarios.models import Funcionario
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS40')
@require_http_methods(["POST"])
def api_registrar_ponto(request):
    """API para registrar ponto (entrada ou saída)"""
    try:
        if not hasattr(request.user, 'funcionario_profile') or not request.user.funcionario_profile:
            return JsonResponse({'success': False, 'message': 'Usuário não está vinculado a um funcionário'})
        funcionario = request.user.funcionario_profile
        agora = timezone.localtime(timezone.now())
        hoje = agora.date()
        registros_hoje = RegistroPonto.objects.filter(
            funcionario=funcionario,
            data=hoje,
            status=True
        ).order_by('data_hora')
        entradas = registros_hoje.filter(tipo=RegistroPonto.TIPO_ENTRADA)
        saidas = registros_hoje.filter(tipo=RegistroPonto.TIPO_SAIDA)
        proximo_tipo = None
        proximo_numero = None
        if entradas.count() == 0:
            proximo_tipo = RegistroPonto.TIPO_ENTRADA
            proximo_numero = 1
        elif saidas.count() == 0:
            proximo_tipo = RegistroPonto.TIPO_SAIDA
            proximo_numero = 1
        elif entradas.count() == 1 and saidas.count() == 1:
            proximo_tipo = RegistroPonto.TIPO_ENTRADA
            proximo_numero = 2
        elif entradas.count() == 2 and saidas.count() == 1:
            proximo_tipo = RegistroPonto.TIPO_SAIDA
            proximo_numero = 2
        else:
            return JsonResponse({'success': False, 'message': 'Limite de registros atingido para hoje (máximo 2 entradas e 2 saídas)'})
        if RegistroPonto.objects.filter(
            funcionario=funcionario,
            data=hoje,
            tipo=proximo_tipo,
            numero=proximo_numero,
            status=True
        ).exists():
            return JsonResponse({'success': False, 'message': f'{proximo_tipo} {proximo_numero} já foi registrado hoje'})
        registro = RegistroPonto.objects.create(
            funcionario=funcionario,
            tipo=proximo_tipo,
            numero=proximo_numero,
            data_hora=agora,
            data=hoje,
            status=True
        )
        return JsonResponse({
            'success': True,
            'message': f'{proximo_tipo} {proximo_numero} registrado com sucesso!',
            'data': {
                'id': registro.id,
                'tipo': registro.get_tipo_display(),
                'numero': registro.numero,
                'data_hora': timezone.localtime(registro.data_hora).strftime('%d/%m/%Y %H:%M:%S'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao registrar ponto: {str(e)}'})

@login_required
@controle_acess('SS40')
@require_http_methods(["GET"])
def api_listar_pontos_dia(request):
    """API para listar pontos do dia"""
    try:
        if not hasattr(request.user, 'funcionario_profile') or not request.user.funcionario_profile:
            return JsonResponse({'success': False, 'message': 'Usuário não está vinculado a um funcionário'})
        funcionario = request.user.funcionario_profile
        data_str = request.GET.get('data', None)
        if data_str:
            try:
                data = datetime.strptime(data_str, '%Y-%m-%d').date()
            except:
                data = timezone.localtime(timezone.now()).date()
        else:
            data = timezone.localtime(timezone.now()).date()
        registros = RegistroPonto.objects.filter(
            funcionario=funcionario,
            data=data,
            status=True
        ).order_by('data_hora')
        pontos = []
        for registro in registros:
            data_hora_local = timezone.localtime(registro.data_hora)
            pontos.append({
                'id': registro.id,
                'tipo': registro.get_tipo_display(),
                'numero': registro.numero,
                'horario': data_hora_local.strftime('%H:%M:%S'),
                'data_hora': data_hora_local.strftime('%d/%m/%Y %H:%M:%S'),
            })
        return JsonResponse({
            'success': True,
            'data': pontos,
            'data_str': data.strftime('%d/%m/%Y'),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar pontos: {str(e)}'})

@login_required
@controle_acess('SS42')
@require_http_methods(["POST"])
def api_ajustar_horario(request):
    """API para ajustar horários de ponto (apenas superuser)"""
    try:
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'message': 'Apenas superusuários podem ajustar horários'})
        funcionario_id = request.POST.get('funcionario_id', '').strip()
        data_str = request.POST.get('data', '').strip()
        entrada1_str = request.POST.get('entrada1', '').strip()
        saida1_str = request.POST.get('saida1', '').strip()
        entrada2_str = request.POST.get('entrada2', '').strip()
        saida2_str = request.POST.get('saida2', '').strip()
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório'})
        if not data_str:
            return JsonResponse({'success': False, 'message': 'Data é obrigatória'})
        try:
            funcionario = Funcionario.objects.get(id=funcionario_id, status=True)
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Funcionario.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'})
        except:
            return JsonResponse({'success': False, 'message': 'Formato de data inválido'})
        registros_criados = []
        registros_atualizados = []
        horarios = [
            ('entrada1', entrada1_str, RegistroPonto.TIPO_ENTRADA, 1),
            ('saida1', saida1_str, RegistroPonto.TIPO_SAIDA, 1),
            ('entrada2', entrada2_str, RegistroPonto.TIPO_ENTRADA, 2),
            ('saida2', saida2_str, RegistroPonto.TIPO_SAIDA, 2),
        ]
        for nome_campo, horario_str, tipo, numero in horarios:
            if horario_str:
                try:
                    horario_time = datetime.strptime(horario_str, '%H:%M').time()
                    data_hora_naive = datetime.combine(data, horario_time)
                    data_hora = timezone.make_aware(data_hora_naive, timezone.get_current_timezone())
                    registro, created = RegistroPonto.objects.update_or_create(
                        funcionario=funcionario,
                        data=data,
                        tipo=tipo,
                        numero=numero,
                        defaults={
                            'data_hora': data_hora,
                            'status': True,
                        }
                    )
                    if created:
                        registros_criados.append(f'{registro.get_tipo_display()} {registro.numero}')
                    else:
                        registros_atualizados.append(f'{registro.get_tipo_display()} {registro.numero}')
                except:
                    return JsonResponse({'success': False, 'message': f'Formato de horário inválido para {nome_campo}: {horario_str}'})
            else:
                RegistroPonto.objects.filter(
                    funcionario=funcionario,
                    data=data,
                    tipo=tipo,
                    numero=numero,
                    status=True
                ).update(status=False)
        justificativa_texto = request.POST.get('justificativa', '').strip()
        arquivos = request.FILES.getlist('arquivos')
        if justificativa_texto:
            justificativa = Justificativa.objects.create(
                titulo=f'AJUSTE DE HORÁRIO - {data.strftime("%d/%m/%Y")}',
                tipo=Justificativa.TIPO_ABONO,
                funcionario=funcionario,
                data_inicio=data,
                data_fim=data,
                observacoes=justificativa_texto,
                status=True,
                criado_por=request.user
            )
            for arquivo in arquivos:
                JustificativaArquivo.objects.create(
                    justificativa=justificativa,
                    arquivo=arquivo,
                    titulo=arquivo.name.upper()
                )
        mensagem = 'Horários ajustados com sucesso!'
        if registros_criados:
            mensagem += f' Criados: {", ".join(registros_criados)}.'
        if registros_atualizados:
            mensagem += f' Atualizados: {", ".join(registros_atualizados)}.'
        return JsonResponse({
            'success': True,
            'message': mensagem,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao ajustar horário: {str(e)}'})
