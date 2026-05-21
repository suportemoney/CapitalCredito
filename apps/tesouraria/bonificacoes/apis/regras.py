from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.bonificacoes.models import BonificacaoRegra, BonificacaoGatilho, TipoRegraChoices

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_regras(request):
    try:
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = BonificacaoRegra.objects.prefetch_related('gatilhos').all()
        if apenas_ativos:
            qs = qs.filter(ativo=True)
        qs = qs.order_by('-ativo', '-data_criacao', 'nome')
        data = []
        for r in qs:
            gatilhos = [{'id': g.id, 'valor_minimo': float(g.valor_minimo), 'percentual': float(g.percentual) if g.percentual else None, 'valor_fixo': float(g.valor_fixo) if g.valor_fixo else None, 'ordem': g.ordem, 'ativo': g.ativo} for g in r.gatilhos.filter(ativo=True).order_by('valor_minimo')]
            data.append({'id': r.id, 'nome': r.nome, 'tipo_regra': r.tipo_regra, 'tipo_regra_display': r.get_tipo_regra_display(), 'campo_valor': r.campo_valor, 'campo_valor_display': r.get_campo_valor_display(), 'percentual_padrao': float(r.percentual_padrao) if r.percentual_padrao else None, 'ativo': r.ativo, 'gatilhos': gatilhos})
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_nova_regra(request):
    try:
        nome = request.POST.get('nome', '').strip()
        tipo_regra = request.POST.get('tipo_regra', '').strip()
        campo_valor = request.POST.get('campo_valor', 'valor_af').strip()
        percentual_padrao = request.POST.get('percentual_padrao', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        if tipo_regra not in [c[0] for c in TipoRegraChoices.choices]:
            return JsonResponse({'success': False, 'message': 'Tipo de regra inválido'})
        with transaction.atomic():
            regra = BonificacaoRegra(nome=nome.upper(), tipo_regra=tipo_regra, campo_valor=campo_valor or 'valor_af')
            if tipo_regra == TipoRegraChoices.PERCENTUAL and percentual_padrao:
                regra.percentual_padrao = Decimal(percentual_padrao.replace(',', '.'))
            regra.save()
        return JsonResponse({'success': True, 'message': 'Regra criada com sucesso.', 'result': {'id': regra.id}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_editar_regra(request):
    try:
        regra_id = request.POST.get('regra_id')
        nome = request.POST.get('nome', '').strip()
        tipo_regra = request.POST.get('tipo_regra', '').strip()
        campo_valor = request.POST.get('campo_valor', '').strip()
        percentual_padrao = request.POST.get('percentual_padrao', '').strip()
        ativo = request.POST.get('ativo', '').strip()
        if not regra_id:
            return JsonResponse({'success': False, 'message': 'ID da regra é obrigatório'})
        regra = BonificacaoRegra.objects.get(id=regra_id)
        if nome:
            regra.nome = nome.upper()
        if tipo_regra:
            regra.tipo_regra = tipo_regra
        if campo_valor:
            regra.campo_valor = campo_valor
        if tipo_regra == TipoRegraChoices.PERCENTUAL and percentual_padrao:
            regra.percentual_padrao = percentual_padrao
        elif tipo_regra in [TipoRegraChoices.GATILHO_PERCENTUAL, TipoRegraChoices.GATILHO_VALOR_FIXO]:
            regra.percentual_padrao = None
        if ativo.lower() in ('true', '1', 'ativo'):
            regra.ativo = True
        elif ativo.lower() in ('false', '0', 'inativo'):
            regra.ativo = False
        regra.save()
        return JsonResponse({'success': True, 'message': 'Regra atualizada.', 'result': None})
    except BonificacaoRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Regra não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_deletar_regra(request):
    try:
        regra_id = request.POST.get('regra_id')
        if not regra_id:
            return JsonResponse({'success': False, 'message': 'ID da regra é obrigatório'})
        regra = BonificacaoRegra.objects.get(id=regra_id)
        regra.delete()
        return JsonResponse({'success': True, 'message': 'Regra excluída.', 'result': None})
    except BonificacaoRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Regra não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_gatilhos(request):
    try:
        regra_id = request.GET.get('regra_id')
        if not regra_id:
            return JsonResponse({'success': False, 'message': 'regra_id é obrigatório'})
        gatilhos = BonificacaoGatilho.objects.filter(regra_id=regra_id).order_by('valor_minimo')
        data = [{'id': g.id, 'valor_minimo': float(g.valor_minimo), 'percentual': float(g.percentual) if g.percentual else None, 'valor_fixo': float(g.valor_fixo) if g.valor_fixo else None, 'ordem': g.ordem, 'ativo': g.ativo} for g in gatilhos]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_gatilho(request):
    try:
        gatilho_id = request.POST.get('gatilho_id', '').strip()
        regra_id = request.POST.get('regra_id')
        valor_minimo = request.POST.get('valor_minimo', '').strip()
        percentual = request.POST.get('percentual', '').strip()
        valor_fixo = request.POST.get('valor_fixo', '').strip()
        ordem = request.POST.get('ordem', '0').strip()
        if not regra_id:
            return JsonResponse({'success': False, 'message': 'regra_id é obrigatório'})
        regra = BonificacaoRegra.objects.get(id=regra_id)
        if not valor_minimo:
            return JsonResponse({'success': False, 'message': 'Valor mínimo é obrigatório'})
        with transaction.atomic():
            if gatilho_id:
                gatilho = BonificacaoGatilho.objects.get(id=gatilho_id, regra=regra)
            else:
                gatilho = BonificacaoGatilho(regra=regra)
            gatilho.valor_minimo = valor_minimo
            gatilho.ordem = int(ordem) if ordem else 0
            if regra.tipo_regra == TipoRegraChoices.GATILHO_PERCENTUAL:
                gatilho.percentual = percentual if percentual else None
                gatilho.valor_fixo = None
            elif regra.tipo_regra == TipoRegraChoices.GATILHO_VALOR_FIXO:
                gatilho.valor_fixo = valor_fixo if valor_fixo else None
                gatilho.percentual = None
            gatilho.save()
        return JsonResponse({'success': True, 'message': 'Gatilho salvo.', 'result': {'id': gatilho.id}})
    except BonificacaoRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Regra não encontrada'}, status=404)
    except BonificacaoGatilho.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Gatilho não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_deletar_gatilho(request):
    try:
        gatilho_id = request.POST.get('gatilho_id')
        if not gatilho_id:
            return JsonResponse({'success': False, 'message': 'ID do gatilho é obrigatório'})
        gatilho = BonificacaoGatilho.objects.get(id=gatilho_id)
        gatilho.delete()
        return JsonResponse({'success': True, 'message': 'Gatilho excluído.', 'result': None})
    except BonificacaoGatilho.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Gatilho não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
