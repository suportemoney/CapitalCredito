from calendar import monthrange
from datetime import datetime
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, F, ExpressionWrapper, DecimalField
from apps.seguranca.permissoes.decorators import controle_acess, controle_acess_any
from apps.tesouraria.bonificacoes.models import (
    BonificacaoRegra, BonificacaoGatilho, BonificacaoFuncionarioRegra,
    BonificacaoCalculada, ReducaoBonificacaoFuncionario, ReducaoBonificacaoRegra,
    TipoRegraChoices, CampoValorChoices
)
from apps.rh.funcionarios.models import Funcionario
from apps.vendas.financeiro_vendas.models import ContratoPagamento

def _obter_valor_base_funcionario(funcionario, periodo_inicio, periodo_fim, regra=None):
    """Soma ContratoPagamento do user do funcionário no período (PAGO), conforme campo da regra."""
    user = getattr(funcionario, 'usuario', None)
    if not user:
        return Decimal('0.00')
    campo = regra.campo_valor if regra else CampoValorChoices.VALOR_REPASSE
    qs = ContratoPagamento.objects.filter(
        user=user,
        data_contrato__gte=periodo_inicio,
        data_contrato__lte=periodo_fim,
        status='PAGO',
        status_ativo=True,
    )
    if campo == CampoValorChoices.VALOR_AF:
        agg = qs.aggregate(total=Sum('valor_af'))
    else:
        # Repasse = TC acumulado × percentual do classificador de cada contrato
        agg = qs.annotate(
            valor_calculado=ExpressionWrapper(
                F('valor_tc_acumulado') * F('classificador__percentual') / Decimal('100'),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        ).aggregate(total=Sum('valor_calculado'))
    return agg['total'] or Decimal('0.00')

def _calcular_bonificacao_regra(regra, valor_base, gatilho_aplicado=None):
    """Calcula valor da bonificação conforme tipo da regra."""
    if regra.tipo_regra == TipoRegraChoices.PERCENTUAL:
        if regra.percentual_padrao:
            return valor_base * regra.percentual_padrao / Decimal('100'), None
        return Decimal('0.00'), None
    if regra.tipo_regra == TipoRegraChoices.GATILHO_PERCENTUAL and gatilho_aplicado and gatilho_aplicado.percentual:
        return valor_base * gatilho_aplicado.percentual / Decimal('100'), gatilho_aplicado
    if regra.tipo_regra == TipoRegraChoices.GATILHO_VALOR_FIXO and gatilho_aplicado and gatilho_aplicado.valor_fixo:
        return gatilho_aplicado.valor_fixo, gatilho_aplicado
    return Decimal('0.00'), None

def _obter_gatilho_aplicado(regra, valor_base):
    """Retorna o gatilho que se aplica (maior valor_minimo onde valor_base >= valor_minimo)."""
    gatilhos = list(regra.gatilhos.filter(ativo=True).order_by('-valor_minimo'))
    for g in gatilhos:
        if valor_base >= g.valor_minimo:
            return g
    return None

def _obter_soma_reducoes(funcionario, periodo_inicio, periodo_fim):
    """Soma percentuais das reduções do funcionário no período."""
    reducoes = ReducaoBonificacaoFuncionario.objects.filter(
        funcionario=funcionario,
        data_evento__gte=periodo_inicio,
        data_evento__lte=periodo_fim,
        regra_reducao__ativo=True
    ).select_related('regra_reducao')
    soma = Decimal('0.00')
    detalhes = []
    for r in reducoes:
        soma += r.regra_reducao.percentual
        detalhes.append({'titulo': r.regra_reducao.titulo, 'percentual': float(r.regra_reducao.percentual), 'data_evento': r.data_evento.strftime('%Y-%m-%d')})
    return soma, detalhes

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_preview_calculo(request):
    try:
        periodo_inicio = request.GET.get('periodo_inicio', '').strip()
        periodo_fim = request.GET.get('periodo_fim', '').strip()
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        setor_id = request.GET.get('setor_id', '').strip()
        if not periodo_inicio or not periodo_fim:
            return JsonResponse({'success': False, 'message': 'Período início e fim são obrigatórios'})
        dt_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d').date()
        dt_fim = datetime.strptime(periodo_fim, '%Y-%m-%d').date()
        if dt_fim < dt_inicio:
            return JsonResponse({'success': False, 'message': 'Data fim deve ser maior ou igual à data início'})
        qs = Funcionario.objects.filter(status=True).select_related('usuario')
        if funcionario_id:
            qs = qs.filter(id=funcionario_id)
        if setor_id:
            qs = qs.filter(dados_profissionais__setor_id=setor_id)
        preview = []
        for func in qs:
            vinculos = BonificacaoFuncionarioRegra.objects.filter(
                funcionario=func, ativo=True, regra__ativo=True
            ).filter(
                Q(data_inicio__isnull=True) | Q(data_inicio__lte=dt_fim),
                Q(data_fim__isnull=True) | Q(data_fim__gte=dt_inicio)
            ).select_related('regra').order_by('-prioridade')
            for v in vinculos:
                valor_base = _obter_valor_base_funcionario(func, dt_inicio, dt_fim, v.regra)
                gatilho = _obter_gatilho_aplicado(v.regra, valor_base)
                valor_bonif, _ = _calcular_bonificacao_regra(v.regra, valor_base, gatilho)
                soma_red, reducoes_det = _obter_soma_reducoes(func, dt_inicio, dt_fim)
                valor_final = valor_bonif * (Decimal('1') - soma_red / Decimal('100')) if soma_red else valor_bonif
                preview.append({
                    'funcionario_id': func.id, 'funcionario_nome': func.nome_completo,
                    'regra_id': v.regra_id, 'regra_nome': v.regra.nome,
                    'valor_base': float(valor_base), 'valor_bonificacao': float(valor_bonif),
                    'valor_bonificacao_final': float(valor_final), 'reducoes_aplicadas': reducoes_det
                })
        return JsonResponse({'success': True, 'result': preview})
    except ValueError as e:
        return JsonResponse({'success': False, 'message': 'Data inválida. Use formato YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess_any('SS45', 'SS46')
@require_http_methods(["GET"])
def api_get_calculo_mes(request):
    """Calcula bonificações por mês (YYYY-MM), inclui inativos. Filtros: funcionario, regra, valor_base, bonificacao, valor_final. Ordena por valor_final desc. Default valor_final_min=1."""
    try:
        mes = request.GET.get('mes', '').strip()
        if not mes or len(mes) != 7 or mes[4] != '-':
            return JsonResponse({'success': False, 'message': 'Parâmetro mes obrigatório (YYYY-MM)'})
        ano, m = int(mes[:4]), int(mes[5:7])
        _, ultimo = monthrange(ano, m)
        dt_inicio = datetime(ano, m, 1).date()
        dt_fim = datetime(ano, m, ultimo).date()
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        regra_id = request.GET.get('regra_id', '').strip()
        valor_base_min = request.GET.get('valor_base_min', '').strip()
        valor_base_max = request.GET.get('valor_base_max', '').strip()
        bonificacao_min = request.GET.get('bonificacao_min', '').strip()
        bonificacao_max = request.GET.get('bonificacao_max', '').strip()
        valor_final_min = request.GET.get('valor_final_min', '').strip()
        valor_final_max = request.GET.get('valor_final_max', '').strip()
        vinculos = BonificacaoFuncionarioRegra.objects.filter(
            ativo=True, regra__ativo=True
        ).filter(
            Q(data_inicio__isnull=True) | Q(data_inicio__lte=dt_fim),
            Q(data_fim__isnull=True) | Q(data_fim__gte=dt_inicio)
        ).select_related('funcionario', 'regra').order_by('funcionario_id', '-prioridade')
        if funcionario_id:
            vinculos = vinculos.filter(funcionario_id=funcionario_id)
        if regra_id:
            vinculos = vinculos.filter(regra_id=regra_id)
        lista = []
        for v in vinculos:
            func = v.funcionario
            valor_base = _obter_valor_base_funcionario(func, dt_inicio, dt_fim, v.regra)
            gatilho = _obter_gatilho_aplicado(v.regra, valor_base)
            valor_bonif, _ = _calcular_bonificacao_regra(v.regra, valor_base, gatilho)
            soma_red, _ = _obter_soma_reducoes(func, dt_inicio, dt_fim)
            valor_final = valor_bonif * (Decimal('1') - soma_red / Decimal('100')) if soma_red else valor_bonif
            vf = float(valor_final)
            vb = float(valor_bonif)
            vbase = float(valor_base)
            if valor_base_min and vbase < float(valor_base_min):
                continue
            if valor_base_max and vbase > float(valor_base_max):
                continue
            if bonificacao_min and vb < float(bonificacao_min):
                continue
            if bonificacao_max and vb > float(bonificacao_max):
                continue
            if valor_final_min and vf < float(valor_final_min):
                continue
            if valor_final_max and vf > float(valor_final_max):
                continue
            if v.regra.tipo_regra == TipoRegraChoices.PERCENTUAL and v.regra.percentual_padrao is not None:
                percentual_aplicado = str(v.regra.percentual_padrao) + '%'
                gatilho_valor = '-'
            elif gatilho:
                if v.regra.tipo_regra == TipoRegraChoices.GATILHO_PERCENTUAL and gatilho.percentual is not None:
                    percentual_aplicado = str(gatilho.percentual) + '%'
                    gatilho_valor = 'Mín. R$ ' + '{:,.2f}'.format(float(gatilho.valor_minimo)).replace(',', 'X').replace('.', ',').replace('X', '.')
                elif v.regra.tipo_regra == TipoRegraChoices.GATILHO_VALOR_FIXO and gatilho.valor_fixo is not None:
                    percentual_aplicado = '-'
                    gatilho_valor = 'Mín. R$ ' + '{:,.2f}'.format(float(gatilho.valor_minimo)).replace(',', 'X').replace('.', ',').replace('X', '.') + ' → R$ ' + '{:,.2f}'.format(float(gatilho.valor_fixo)).replace(',', 'X').replace('.', ',').replace('X', '.')
                else:
                    percentual_aplicado = '-'
                    gatilho_valor = 'Mín. R$ ' + '{:,.2f}'.format(float(gatilho.valor_minimo)).replace(',', 'X').replace('.', ',').replace('X', '.')
            else:
                percentual_aplicado = '-'
                gatilho_valor = '-'
            lista.append({
                'funcionario_id': func.id, 'funcionario_nome': func.nome_completo, 'funcionario_ativo': bool(func.status),
                'regra_id': v.regra_id, 'regra_nome': v.regra.nome,
                'valor_base': vbase, 'valor_bonificacao': vb, 'valor_bonificacao_final': vf,
                'percentual_aplicado': percentual_aplicado, 'gatilho_valor': gatilho_valor
            })
        lista.sort(key=lambda x: x['valor_bonificacao_final'], reverse=True)
        return JsonResponse({'success': True, 'result': lista})
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_calculos(request):
    try:
        periodo_inicio = request.GET.get('periodo_inicio', '').strip()
        periodo_fim = request.GET.get('periodo_fim', '').strip()
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        qs = BonificacaoCalculada.objects.select_related('funcionario', 'regra', 'gatilho_aplicado').order_by('-data_calculo')
        if periodo_inicio:
            qs = qs.filter(periodo_inicio__gte=periodo_inicio)
        if periodo_fim:
            qs = qs.filter(periodo_fim__lte=periodo_fim)
        if funcionario_id:
            qs = qs.filter(funcionario_id=funcionario_id)
        data = [{'id': c.id, 'funcionario_id': c.funcionario_id, 'funcionario_nome': c.funcionario.nome_completo, 'regra_id': c.regra_id, 'regra_nome': c.regra.nome, 'periodo_inicio': c.periodo_inicio.strftime('%Y-%m-%d'), 'periodo_fim': c.periodo_fim.strftime('%Y-%m-%d'), 'valor_base': float(c.valor_base), 'valor_bonificacao': float(c.valor_bonificacao), 'valor_bonificacao_final': float(c.valor_bonificacao_final) if c.valor_bonificacao_final else None, 'reducoes_aplicadas': c.reducoes_aplicadas, 'data_calculo': c.data_calculo.strftime('%Y-%m-%d %H:%M')} for c in qs[:200]]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_calcular_bonificacao(request):
    try:
        funcionario_id = request.POST.get('funcionario_id')
        regra_id = request.POST.get('regra_id')
        periodo_inicio = request.POST.get('periodo_inicio', '').strip()
        periodo_fim = request.POST.get('periodo_fim', '').strip()
        if not funcionario_id or not regra_id or not periodo_inicio or not periodo_fim:
            return JsonResponse({'success': False, 'message': 'Funcionário, regra e período são obrigatórios'})
        dt_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d').date()
        dt_fim = datetime.strptime(periodo_fim, '%Y-%m-%d').date()
        if dt_fim < dt_inicio:
            return JsonResponse({'success': False, 'message': 'Data fim deve ser maior ou igual à data início'})
        funcionario = Funcionario.objects.get(id=funcionario_id)
        regra = BonificacaoRegra.objects.get(id=regra_id, ativo=True)
        vinculo = BonificacaoFuncionarioRegra.objects.filter(
            funcionario=funcionario, regra=regra, ativo=True
        ).filter(
            Q(data_inicio__isnull=True) | Q(data_inicio__lte=dt_fim),
            Q(data_fim__isnull=True) | Q(data_fim__gte=dt_inicio)
        ).first()
        if not vinculo:
            return JsonResponse({'success': False, 'message': 'Não há vínculo ativo para este funcionário e regra no período'})
        valor_base = _obter_valor_base_funcionario(funcionario, dt_inicio, dt_fim, regra)
        gatilho = _obter_gatilho_aplicado(regra, valor_base)
        valor_bonif, gatilho_obj = _calcular_bonificacao_regra(regra, valor_base, gatilho)
        soma_red, reducoes_det = _obter_soma_reducoes(funcionario, dt_inicio, dt_fim)
        valor_final = valor_bonif * (Decimal('1') - soma_red / Decimal('100')) if soma_red else valor_bonif
        with transaction.atomic():
            BonificacaoCalculada.objects.create(
                funcionario=funcionario, regra=regra, periodo_inicio=dt_inicio, periodo_fim=dt_fim,
                valor_base=valor_base, valor_bonificacao=valor_bonif, valor_bonificacao_final=valor_final,
                reducoes_aplicadas=reducoes_det, gatilho_aplicado=gatilho_obj
            )
        return JsonResponse({'success': True, 'message': 'Bonificação calculada e salva.', 'result': {'valor_bonificacao_final': float(valor_final)}})
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'}, status=404)
    except BonificacaoRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Regra não encontrada'}, status=404)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Data inválida. Use formato YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_calcular_lote(request):
    try:
        periodo_inicio = request.POST.get('periodo_inicio', '').strip()
        periodo_fim = request.POST.get('periodo_fim', '').strip()
        setor_id = request.POST.get('setor_id', '').strip()
        if not periodo_inicio or not periodo_fim:
            return JsonResponse({'success': False, 'message': 'Período início e fim são obrigatórios'})
        dt_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d').date()
        dt_fim = datetime.strptime(periodo_fim, '%Y-%m-%d').date()
        if dt_fim < dt_inicio:
            return JsonResponse({'success': False, 'message': 'Data fim deve ser maior ou igual à data início'})
        qs = Funcionario.objects.filter(status=True)
        if setor_id:
            qs = qs.filter(dados_profissionais__setor_id=setor_id)
        calculados = 0
        with transaction.atomic():
            for func in qs:
                vinculos = BonificacaoFuncionarioRegra.objects.filter(
                    funcionario=func, ativo=True, regra__ativo=True
                ).filter(
                    Q(data_inicio__isnull=True) | Q(data_inicio__lte=dt_fim),
                    Q(data_fim__isnull=True) | Q(data_fim__gte=dt_inicio)
                ).select_related('regra').order_by('-prioridade')
                for v in vinculos:
                    valor_base = _obter_valor_base_funcionario(func, dt_inicio, dt_fim, v.regra)
                    gatilho = _obter_gatilho_aplicado(v.regra, valor_base)
                    valor_bonif, gatilho_obj = _calcular_bonificacao_regra(v.regra, valor_base, gatilho)
                    soma_red, reducoes_det = _obter_soma_reducoes(func, dt_inicio, dt_fim)
                    valor_final = valor_bonif * (Decimal('1') - soma_red / Decimal('100')) if soma_red else valor_bonif
                    BonificacaoCalculada.objects.create(
                        funcionario=func, regra=v.regra, periodo_inicio=dt_inicio, periodo_fim=dt_fim,
                        valor_base=valor_base, valor_bonificacao=valor_bonif, valor_bonificacao_final=valor_final,
                        reducoes_aplicadas=reducoes_det, gatilho_aplicado=gatilho_obj
                    )
                    calculados += 1
        return JsonResponse({'success': True, 'message': f'{calculados} bonificação(ões) calculada(s) e salva(s).', 'result': {'calculados': calculados}})
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Data inválida. Use formato YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_deletar_calculo(request):
    try:
        calculo_id = request.POST.get('calculo_id')
        if not calculo_id:
            return JsonResponse({'success': False, 'message': 'ID do cálculo é obrigatório'})
        calc = BonificacaoCalculada.objects.get(id=calculo_id)
        calc.delete()
        return JsonResponse({'success': True, 'message': 'Cálculo excluído.', 'result': None})
    except BonificacaoCalculada.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cálculo não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
