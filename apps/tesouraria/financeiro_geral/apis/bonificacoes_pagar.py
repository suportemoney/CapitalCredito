import os
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.financeiro_geral.models import BonificacaoAPagar
from apps.rh.funcionarios.models import Funcionario

def _serializar_bonificacao(b):
    return {
        'id': b.id,
        'funcionario_id': b.funcionario_id,
        'funcionario_nome': b.funcionario.nome_completo if b.funcionario else None,
        'valor_bonificacao': float(b.valor_bonificacao),
        'mes_referente': b.mes_referente or '',
        'chave_pix': b.chave_pix or '',
        'data_pagamento': b.data_pagamento.strftime('%Y-%m-%d') if b.data_pagamento else None,
        'status_pagamento': b.status_pagamento,
        'data_criacao': b.data_criacao.strftime('%Y-%m-%d %H:%M') if b.data_criacao else None,
        'has_comprovante': bool(b.comprovante),
        'comprovante_url': b.comprovante.url if b.comprovante else None,
        'status_ativo': b.status_ativo,
    }

def _aplicar_filtros_bonificacoes(qs, request):
    func = request.GET.get('funcionario_id', '')
    if func:
        qs = qs.filter(funcionario_id=func)
    mes = request.GET.get('mes_referente', '').strip()
    if mes:
        qs = qs.filter(mes_referente__icontains=mes)
    data_de = request.GET.get('data_pagamento_de', '').strip()
    if data_de:
        try:
            qs = qs.filter(data_pagamento__gte=datetime.strptime(data_de, '%Y-%m-%d').date())
        except ValueError:
            pass
    data_ate = request.GET.get('data_pagamento_ate', '').strip()
    if data_ate:
        try:
            qs = qs.filter(data_pagamento__lte=datetime.strptime(data_ate, '%Y-%m-%d').date())
        except ValueError:
            pass
    try:
        vmin = request.GET.get('valor_min', '')
        if vmin:
            qs = qs.filter(valor_bonificacao__gte=Decimal(vmin.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    try:
        vmax = request.GET.get('valor_max', '')
        if vmax:
            qs = qs.filter(valor_bonificacao__lte=Decimal(vmax.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    status = request.GET.get('status', 'true').lower()
    if status == 'false':
        qs = qs.filter(status_ativo=False)
    elif status != 'todos':
        qs = qs.filter(status_ativo=True)
    fid = request.GET.get('id', '')
    if fid:
        try:
            qs = qs.filter(id=int(fid))
        except (ValueError, TypeError):
            pass
    return qs

@login_required
@controle_acess('SS22')
@require_http_methods(["GET"])
def api_get_bonificacoes_pagar(request):
    """Lista bonificações a pagar com filtros: funcionario_id, mes_referente, data_pagamento_de, data_pagamento_ate, valor_min, valor_max, status (default true)."""
    try:
        qs = BonificacaoAPagar.objects.all().select_related('funcionario').order_by('status_pagamento', '-data_criacao', 'funcionario__nome_completo')
        qs = _aplicar_filtros_bonificacoes(qs, request)
        data = [_serializar_bonificacao(b) for b in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_bonificacoes_pagar_criar(request):
    """Cria bonificação a pagar. Obrigatório: funcionario_id, valor_bonificacao, mes_referente, chave_pix. Opcional: data_pagamento, comprovante."""
    try:
        funcionario_id = request.POST.get('funcionario_id')
        valor_bonificacao = request.POST.get('valor_bonificacao', '').strip()
        mes_referente = request.POST.get('mes_referente', '').strip()
        chave_pix = request.POST.get('chave_pix', '').strip()
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório'})
        if not valor_bonificacao:
            return JsonResponse({'success': False, 'message': 'Valor da bonificação é obrigatório'})
        if not mes_referente:
            return JsonResponse({'success': False, 'message': 'Mês referente é obrigatório'})
        if not chave_pix:
            return JsonResponse({'success': False, 'message': 'Chave PIX é obrigatória'})
        try:
            valor_dec = Decimal(valor_bonificacao.replace(',', '.'))
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse({'success': False, 'message': 'Valor inválido'})
        funcionario = Funcionario.objects.get(id=funcionario_id)
        data_pagamento = request.POST.get('data_pagamento', '').strip()
        data_pag = None
        if data_pagamento:
            try:
                data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
            except ValueError:
                pass
        comprovante = request.FILES.get('comprovante')
        status_pagamento = bool(data_pag and comprovante)
        with transaction.atomic():
            BonificacaoAPagar.objects.create(
                funcionario=funcionario,
                valor_bonificacao=valor_dec,
                mes_referente=mes_referente,
                chave_pix=chave_pix,
                data_pagamento=data_pag,
                comprovante=comprovante,
                status_pagamento=status_pagamento,
                status_ativo=True,
            )
        return JsonResponse({'success': True, 'message': 'Bonificação criada com sucesso.', 'result': None})
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_bonificacoes_pagar_pagar_agora(request):
    """Pagar agora: id, data_pagamento e comprovante obrigatórios."""
    try:
        bonif_id = request.POST.get('id')
        data_pagamento = request.POST.get('data_pagamento', '').strip()
        comprovante = request.FILES.get('comprovante')
        if not bonif_id:
            return JsonResponse({'success': False, 'message': 'ID da bonificação é obrigatório'})
        if not data_pagamento:
            return JsonResponse({'success': False, 'message': 'Data de pagamento é obrigatória no Pagar Agora'})
        if not comprovante:
            return JsonResponse({'success': False, 'message': 'Comprovante é obrigatório no Pagar Agora'})
        try:
            data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Data de pagamento inválida'})
        obj = BonificacaoAPagar.objects.get(id=bonif_id)
        obj.data_pagamento = data_pag
        obj.comprovante = comprovante
        obj.status_pagamento = True
        obj.save()
        return JsonResponse({'success': True, 'message': 'Bonificação paga.', 'result': None})
    except BonificacaoAPagar.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Bonificação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_bonificacoes_pagar_editar(request):
    """Edita bonificação a pagar. id, funcionario_id, valor_bonificacao, mes_referente, chave_pix obrigatórios."""
    try:
        bonif_id = request.POST.get('id')
        funcionario_id = request.POST.get('funcionario_id')
        valor_bonificacao = request.POST.get('valor_bonificacao', '').strip()
        mes_referente = request.POST.get('mes_referente', '').strip()
        chave_pix = request.POST.get('chave_pix', '').strip()
        if not bonif_id:
            return JsonResponse({'success': False, 'message': 'ID da bonificação é obrigatório'})
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório'})
        if not valor_bonificacao:
            return JsonResponse({'success': False, 'message': 'Valor da bonificação é obrigatório'})
        if not mes_referente:
            return JsonResponse({'success': False, 'message': 'Mês referente é obrigatório'})
        if not chave_pix:
            return JsonResponse({'success': False, 'message': 'Chave PIX é obrigatória'})
        try:
            valor_dec = Decimal(valor_bonificacao.replace(',', '.'))
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse({'success': False, 'message': 'Valor inválido'})
        obj = BonificacaoAPagar.objects.get(id=bonif_id)
        funcionario = Funcionario.objects.get(id=funcionario_id)
        obj.funcionario = funcionario
        obj.valor_bonificacao = valor_dec
        obj.mes_referente = mes_referente
        obj.chave_pix = chave_pix
        if request.FILES.get('comprovante'):
            obj.comprovante = request.FILES.get('comprovante')
        obj.save()
        return JsonResponse({'success': True, 'message': 'Bonificação atualizada.', 'result': None})
    except BonificacaoAPagar.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Bonificação não encontrada'}, status=404)
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_bonificacoes_pagar_inativar(request):
    """Inativa bonificação a pagar (status_ativo=False)."""
    try:
        bonif_id = request.POST.get('id')
        if not bonif_id:
            return JsonResponse({'success': False, 'message': 'ID da bonificação é obrigatório'})
        obj = BonificacaoAPagar.objects.get(id=bonif_id)
        obj.status_ativo = False
        obj.save()
        return JsonResponse({'success': True, 'message': 'Bonificação inativada.', 'result': None})
    except BonificacaoAPagar.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Bonificação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('CX47')
@require_http_methods(["POST"])
def api_post_bonificacoes_pagar_criar_ja_paga(request):
    """Cria bonificação a pagar já paga (do Calc Bonificações). POST: funcionario_id, valor_bonificacao, mes_referente (MM/YYYY). Chave PIX do funcionário no RH; sem comprovante."""
    try:
        funcionario_id = request.POST.get('funcionario_id')
        valor_bonificacao = request.POST.get('valor_bonificacao', '').strip()
        mes_referente = request.POST.get('mes_referente', '').strip()
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório'})
        if not valor_bonificacao:
            return JsonResponse({'success': False, 'message': 'Valor da bonificação é obrigatório'})
        if not mes_referente:
            return JsonResponse({'success': False, 'message': 'Mês referente é obrigatório'})
        try:
            valor_dec = Decimal(valor_bonificacao.replace(',', '.'))
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse({'success': False, 'message': 'Valor inválido'})
        funcionario = Funcionario.objects.get(id=funcionario_id)
        chave_pix = (funcionario.chave_pix or '').strip()
        if not chave_pix:
            return JsonResponse({'success': False, 'message': 'Funcionário sem chave PIX cadastrada. Cadastre no RH.'}, status=400)
        data_pag = timezone.now().date()
        with transaction.atomic():
            BonificacaoAPagar.objects.create(
                funcionario=funcionario,
                valor_bonificacao=valor_dec,
                mes_referente=mes_referente,
                chave_pix=chave_pix,
                data_pagamento=data_pag,
                comprovante=None,
                status_pagamento=True,
                status_ativo=True,
            )
        return JsonResponse({'success': True, 'message': 'Bonificação criada e marcada como paga.', 'result': None})
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["GET"])
def api_get_bonificacao_comprovante_download(request):
    """Retorna o arquivo comprovante da bonificação para download (Content-Disposition: attachment). GET id=."""
    try:
        bonif_id = request.GET.get('id')
        if not bonif_id:
            raise Http404
        obj = BonificacaoAPagar.objects.get(id=bonif_id)
        if not obj.comprovante:
            raise Http404
        filename = os.path.basename(obj.comprovante.name) or 'comprovante'
        response = FileResponse(obj.comprovante.open('rb'), as_attachment=True, filename=filename)
        return response
    except BonificacaoAPagar.DoesNotExist:
        raise Http404
    except (ValueError, TypeError):
        raise Http404
