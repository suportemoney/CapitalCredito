from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from apps.seguranca.permissoes.decorators import controle_acess
from apps.tesouraria.financeiro_geral.models import Conta, Salario, Beneficio, CategoriaConta, SubcategoriaConta, TipoBeneficio
from apps.rh.funcionarios.models import Funcionario

def _serializar_conta(c):
    return {
        'id': c.id,
        'tipo': 'CONTA',
        'tipo_display': 'Conta (empresa)',
        'descricao': c.descricao,
        'valor': float(c.valor),
        'data_vencimento': c.data_vencimento.strftime('%Y-%m-%d'),
        'data_pagamento': c.data_pagamento.strftime('%Y-%m-%d') if c.data_pagamento else None,
        'pago': c.pago,
        'categoria_id': c.categoria_id,
        'categoria_nome': c.categoria.nome if c.categoria else None,
        'subcategoria_id': c.subcategoria_id,
        'subcategoria_nome': c.subcategoria.nome if c.subcategoria else None,
        'tipo_beneficio_id': None,
        'tipo_beneficio_nome': None,
        'funcionario_id': None,
        'funcionario_nome': None,
        'observacao': c.observacao or '',
        'has_comprovante': bool(c.comprovante),
        'comprovante_url': c.comprovante.url if c.comprovante else None,
    }

def _serializar_salario(c):
    return {
        'id': c.id,
        'tipo': 'SALARIO',
        'tipo_display': 'Salário',
        'descricao': c.descricao,
        'valor': float(c.valor),
        'data_vencimento': c.data_vencimento.strftime('%Y-%m-%d'),
        'data_pagamento': c.data_pagamento.strftime('%Y-%m-%d') if c.data_pagamento else None,
        'pago': c.pago,
        'categoria_id': None,
        'categoria_nome': None,
        'subcategoria_id': None,
        'subcategoria_nome': None,
        'tipo_beneficio_id': None,
        'tipo_beneficio_nome': None,
        'funcionario_id': c.funcionario_id,
        'funcionario_nome': c.funcionario.nome_completo if c.funcionario else None,
        'observacao': c.observacao or '',
        'has_comprovante': bool(c.comprovante),
        'comprovante_url': c.comprovante.url if c.comprovante else None,
    }

def _serializar_beneficio(c):
    return {
        'id': c.id,
        'tipo': 'BENEFICIO',
        'tipo_display': 'Benefício',
        'descricao': c.descricao,
        'valor': float(c.valor),
        'data_vencimento': c.data_vencimento.strftime('%Y-%m-%d'),
        'data_pagamento': c.data_pagamento.strftime('%Y-%m-%d') if c.data_pagamento else None,
        'pago': c.pago,
        'categoria_id': None,
        'categoria_nome': None,
        'subcategoria_id': None,
        'subcategoria_nome': None,
        'tipo_beneficio_id': c.tipo_beneficio_id,
        'tipo_beneficio_nome': c.tipo_beneficio.nome if c.tipo_beneficio else None,
        'funcionario_id': c.funcionario_id,
        'funcionario_nome': c.funcionario.nome_completo if c.funcionario else None,
        'observacao': c.observacao or '',
        'has_comprovante': bool(c.comprovante),
        'comprovante_url': c.comprovante.url if c.comprovante else None,
    }

def _aplicar_filtros_contas(qs, request):
    """Aplica filtros GET na queryset de Conta."""
    descricao = request.GET.get('descricao', '').strip()
    if descricao:
        qs = qs.filter(descricao__icontains=descricao)
    cat = request.GET.get('categoria_id', '')
    if cat:
        qs = qs.filter(categoria_id=cat)
    sub = request.GET.get('subcategoria_id', '')
    if sub:
        qs = qs.filter(subcategoria_id=sub)
    try:
        vmin = request.GET.get('valor_min', '')
        if vmin:
            qs = qs.filter(valor__gte=Decimal(vmin.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    try:
        vmax = request.GET.get('valor_max', '')
        if vmax:
            qs = qs.filter(valor__lte=Decimal(vmax.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    data_de = request.GET.get('data_vencimento_de', '').strip()
    if data_de:
        try:
            qs = qs.filter(data_vencimento__gte=datetime.strptime(data_de, '%Y-%m-%d').date())
        except ValueError:
            pass
    data_ate = request.GET.get('data_vencimento_ate', '').strip()
    if data_ate:
        try:
            qs = qs.filter(data_vencimento__lte=datetime.strptime(data_ate, '%Y-%m-%d').date())
        except ValueError:
            pass
    status = request.GET.get('status', '')
    if status == 'pago':
        qs = qs.filter(pago=True)
    elif status == 'pendente':
        qs = qs.filter(pago=False)
    fid = request.GET.get('id', '')
    if fid:
        try:
            qs = qs.filter(id=int(fid))
        except (ValueError, TypeError):
            pass
    return qs

def _aplicar_filtros_salario(qs, request):
    """Aplica filtros GET na queryset de Salario."""
    descricao = request.GET.get('descricao', '').strip()
    if descricao:
        qs = qs.filter(descricao__icontains=descricao)
    func = request.GET.get('funcionario_id', '')
    if func:
        qs = qs.filter(funcionario_id=func)
    try:
        vmin = request.GET.get('valor_min', '')
        if vmin:
            qs = qs.filter(valor__gte=Decimal(vmin.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    try:
        vmax = request.GET.get('valor_max', '')
        if vmax:
            qs = qs.filter(valor__lte=Decimal(vmax.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    data_de = request.GET.get('data_vencimento_de', '').strip()
    if data_de:
        try:
            qs = qs.filter(data_vencimento__gte=datetime.strptime(data_de, '%Y-%m-%d').date())
        except ValueError:
            pass
    data_ate = request.GET.get('data_vencimento_ate', '').strip()
    if data_ate:
        try:
            qs = qs.filter(data_vencimento__lte=datetime.strptime(data_ate, '%Y-%m-%d').date())
        except ValueError:
            pass
    status = request.GET.get('status', '')
    if status == 'pago':
        qs = qs.filter(pago=True)
    elif status == 'pendente':
        qs = qs.filter(pago=False)
    fid = request.GET.get('id', '')
    if fid:
        try:
            qs = qs.filter(id=int(fid))
        except (ValueError, TypeError):
            pass
    return qs

def _aplicar_filtros_beneficio(qs, request):
    """Aplica filtros GET na queryset de Beneficio."""
    descricao = request.GET.get('descricao', '').strip()
    if descricao:
        qs = qs.filter(descricao__icontains=descricao)
    func = request.GET.get('funcionario_id', '')
    if func:
        qs = qs.filter(funcionario_id=func)
    tben = request.GET.get('tipo_beneficio_id', '')
    if tben:
        qs = qs.filter(tipo_beneficio_id=tben)
    try:
        vmin = request.GET.get('valor_min', '')
        if vmin:
            qs = qs.filter(valor__gte=Decimal(vmin.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    try:
        vmax = request.GET.get('valor_max', '')
        if vmax:
            qs = qs.filter(valor__lte=Decimal(vmax.replace(',', '.')))
    except (InvalidOperation, TypeError):
        pass
    data_de = request.GET.get('data_vencimento_de', '').strip()
    if data_de:
        try:
            qs = qs.filter(data_vencimento__gte=datetime.strptime(data_de, '%Y-%m-%d').date())
        except ValueError:
            pass
    data_ate = request.GET.get('data_vencimento_ate', '').strip()
    if data_ate:
        try:
            qs = qs.filter(data_vencimento__lte=datetime.strptime(data_ate, '%Y-%m-%d').date())
        except ValueError:
            pass
    status = request.GET.get('status', '')
    if status == 'pago':
        qs = qs.filter(pago=True)
    elif status == 'pendente':
        qs = qs.filter(pago=False)
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
def api_get_contas_pagar(request):
    """Lista contas a pagar por tipo com filtros: descricao, categoria_id, subcategoria_id, valor_min, valor_max, data_vencimento_de, data_vencimento_ate, status (pago|pendente), id, funcionario_id, tipo_beneficio_id."""
    try:
        tipo = request.GET.get('tipo', '')
        data = []
        if tipo == 'CONTA' or not tipo:
            qs = Conta.objects.filter(status_ativo=True).select_related('categoria', 'subcategoria').order_by('-data_vencimento', '-data_criacao')
            qs = _aplicar_filtros_contas(qs, request)
            data.extend([_serializar_conta(c) for c in qs])
        if tipo == 'SALARIO' or not tipo:
            qs = Salario.objects.filter(status_ativo=True).select_related('funcionario').order_by('-data_vencimento', '-data_criacao')
            qs = _aplicar_filtros_salario(qs, request)
            data.extend([_serializar_salario(c) for c in qs])
        if tipo == 'BENEFICIO' or not tipo:
            qs = Beneficio.objects.filter(status_ativo=True).select_related('funcionario', 'tipo_beneficio').order_by('-data_vencimento', '-data_criacao')
            qs = _aplicar_filtros_beneficio(qs, request)
            data.extend([_serializar_beneficio(c) for c in qs])
        if tipo:
            data.sort(key=lambda x: (x['data_vencimento'], x['id']), reverse=True)
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_contas_pagar_criar(request):
    """Cria conta a pagar. tipo: CONTA (categoria_id, subcategoria_id), SALARIO (funcionario_id), BENEFICIO (funcionario_id, tipo_beneficio_id)."""
    try:
        tipo = request.POST.get('tipo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        valor = request.POST.get('valor', '').strip()
        data_vencimento = request.POST.get('data_vencimento', '').strip()
        observacao = request.POST.get('observacao', '').strip() or None
        if not tipo or tipo not in ('CONTA', 'SALARIO', 'BENEFICIO'):
            return JsonResponse({'success': False, 'message': 'Tipo inválido'})
        if not descricao:
            return JsonResponse({'success': False, 'message': 'Descrição é obrigatória'})
        if not valor:
            return JsonResponse({'success': False, 'message': 'Valor é obrigatório'})
        if not data_vencimento:
            return JsonResponse({'success': False, 'message': 'Data de vencimento é obrigatória'})
        try:
            valor_dec = Decimal(valor.replace(',', '.'))
            data_venc = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Valor ou data inválidos'})
        if tipo == 'CONTA':
            categoria_id = request.POST.get('categoria_id')
            if not categoria_id:
                return JsonResponse({'success': False, 'message': 'Categoria é obrigatória para conta da empresa'})
            categoria = CategoriaConta.objects.get(id=categoria_id)
            subcategoria_id = request.POST.get('subcategoria_id')
            subcategoria = SubcategoriaConta.objects.filter(id=subcategoria_id, categoria=categoria).first() if subcategoria_id else None
            with transaction.atomic():
                Conta.objects.create(
                    descricao=descricao,
                    valor=valor_dec,
                    data_vencimento=data_venc,
                    pago=False,
                    categoria=categoria,
                    subcategoria=subcategoria,
                    observacao=observacao,
                    status_ativo=True,
                )
        elif tipo == 'SALARIO':
            funcionario_id = request.POST.get('funcionario_id')
            if not funcionario_id:
                return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório para salário'})
            funcionario = Funcionario.objects.get(id=funcionario_id)
            with transaction.atomic():
                Salario.objects.create(
                    descricao=descricao,
                    valor=valor_dec,
                    data_vencimento=data_venc,
                    pago=False,
                    funcionario=funcionario,
                    observacao=observacao,
                    status_ativo=True,
                )
        else:
            funcionario_id = request.POST.get('funcionario_id')
            tipo_beneficio_id = request.POST.get('tipo_beneficio_id')
            if not funcionario_id or not tipo_beneficio_id:
                return JsonResponse({'success': False, 'message': 'Funcionário e tipo de benefício são obrigatórios'})
            funcionario = Funcionario.objects.get(id=funcionario_id)
            tipo_beneficio = TipoBeneficio.objects.get(id=tipo_beneficio_id)
            with transaction.atomic():
                Beneficio.objects.create(
                    descricao=descricao,
                    valor=valor_dec,
                    data_vencimento=data_venc,
                    pago=False,
                    funcionario=funcionario,
                    tipo_beneficio=tipo_beneficio,
                    observacao=observacao,
                    status_ativo=True,
                )
        return JsonResponse({'success': True, 'message': 'Conta a pagar criada com sucesso.', 'result': None})
    except CategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Categoria não encontrada'})
    except SubcategoriaConta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subcategoria não encontrada'})
    except TipoBeneficio.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tipo de benefício não encontrado'})
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_contas_pagar_marcar_pago(request):
    """Marca como pago. Enviar tipo (CONTA, SALARIO, BENEFICIO) e conta_id (id do registro na tabela correspondente)."""
    try:
        tipo = request.POST.get('tipo', '').strip()
        conta_id = request.POST.get('conta_id')
        data_pagamento = request.POST.get('data_pagamento', '').strip()
        if not tipo or tipo not in ('CONTA', 'SALARIO', 'BENEFICIO'):
            return JsonResponse({'success': False, 'message': 'Tipo inválido'})
        if not conta_id:
            return JsonResponse({'success': False, 'message': 'ID da conta é obrigatório'})
        if data_pagamento:
            try:
                data_pag = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Data de pagamento inválida'})
        else:
            data_pag = timezone.now().date()
        if tipo == 'CONTA':
            obj = Conta.objects.get(id=conta_id, status_ativo=True)
        elif tipo == 'SALARIO':
            obj = Salario.objects.get(id=conta_id, status_ativo=True)
        else:
            obj = Beneficio.objects.get(id=conta_id, status_ativo=True)
        obj.pago = True
        obj.data_pagamento = data_pag
        comprovante = request.FILES.get('comprovante')
        if comprovante:
            obj.comprovante = comprovante
        obj.save()
        return JsonResponse({'success': True, 'message': 'Conta marcada como paga.', 'result': None})
    except (Conta.DoesNotExist, Salario.DoesNotExist, Beneficio.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Registro não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS22')
@require_http_methods(["POST"])
def api_post_contas_pagar_editar(request):
    """Edita conta a pagar. tipo, conta_id; demais campos conforme tipo (descricao, valor, data_vencimento, observacao; CONTA: categoria_id, subcategoria_id; SALARIO/BENEFICIO: funcionario_id; BENEFICIO: tipo_beneficio_id)."""
    try:
        tipo = request.POST.get('tipo', '').strip()
        conta_id = request.POST.get('conta_id')
        if not tipo or tipo not in ('CONTA', 'SALARIO', 'BENEFICIO'):
            return JsonResponse({'success': False, 'message': 'Tipo inválido'})
        if not conta_id:
            return JsonResponse({'success': False, 'message': 'ID da conta é obrigatório'})
        descricao = request.POST.get('descricao', '').strip()
        valor = request.POST.get('valor', '').strip()
        data_vencimento = request.POST.get('data_vencimento', '').strip()
        observacao = request.POST.get('observacao', '').strip() or None
        if not descricao:
            return JsonResponse({'success': False, 'message': 'Descrição é obrigatória'})
        if not valor:
            return JsonResponse({'success': False, 'message': 'Valor é obrigatório'})
        if not data_vencimento:
            return JsonResponse({'success': False, 'message': 'Data de vencimento é obrigatória'})
        try:
            valor_dec = Decimal(valor.replace(',', '.'))
            data_venc = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Valor ou data inválidos'})
        if tipo == 'CONTA':
            obj = Conta.objects.get(id=conta_id, status_ativo=True)
            if obj.pago and not request.user.is_superuser:
                return JsonResponse({'success': False, 'message': 'Apenas superusuário pode editar conta já paga.'})
            categoria_id = request.POST.get('categoria_id')
            if not categoria_id:
                return JsonResponse({'success': False, 'message': 'Categoria é obrigatória'})
            categoria = CategoriaConta.objects.get(id=categoria_id)
            subcategoria_id = request.POST.get('subcategoria_id')
            subcategoria = SubcategoriaConta.objects.filter(id=subcategoria_id, categoria=categoria).first() if subcategoria_id else None
            obj.descricao = descricao
            obj.valor = valor_dec
            obj.data_vencimento = data_venc
            obj.observacao = observacao
            obj.categoria = categoria
            obj.subcategoria = subcategoria
            if request.user.is_superuser and request.FILES.get('comprovante'):
                obj.comprovante = request.FILES.get('comprovante')
            obj.save()
        elif tipo == 'SALARIO':
            obj = Salario.objects.get(id=conta_id, status_ativo=True)
            if obj.pago and not request.user.is_superuser:
                return JsonResponse({'success': False, 'message': 'Apenas superusuário pode editar conta já paga.'})
            funcionario_id = request.POST.get('funcionario_id')
            if not funcionario_id:
                return JsonResponse({'success': False, 'message': 'Funcionário é obrigatório'})
            funcionario = Funcionario.objects.get(id=funcionario_id)
            obj.descricao = descricao
            obj.valor = valor_dec
            obj.data_vencimento = data_venc
            obj.observacao = observacao
            obj.funcionario = funcionario
            if request.user.is_superuser and request.FILES.get('comprovante'):
                obj.comprovante = request.FILES.get('comprovante')
            obj.save()
        else:
            obj = Beneficio.objects.get(id=conta_id, status_ativo=True)
            if obj.pago and not request.user.is_superuser:
                return JsonResponse({'success': False, 'message': 'Apenas superusuário pode editar conta já paga.'})
            funcionario_id = request.POST.get('funcionario_id')
            tipo_beneficio_id = request.POST.get('tipo_beneficio_id')
            if not funcionario_id or not tipo_beneficio_id:
                return JsonResponse({'success': False, 'message': 'Funcionário e tipo de benefício são obrigatórios'})
            funcionario = Funcionario.objects.get(id=funcionario_id)
            tipo_beneficio = TipoBeneficio.objects.get(id=tipo_beneficio_id)
            obj.descricao = descricao
            obj.valor = valor_dec
            obj.data_vencimento = data_venc
            obj.observacao = observacao
            obj.funcionario = funcionario
            obj.tipo_beneficio = tipo_beneficio
            if request.user.is_superuser and request.FILES.get('comprovante'):
                obj.comprovante = request.FILES.get('comprovante')
            obj.save()
        return JsonResponse({'success': True, 'message': 'Conta atualizada.', 'result': None})
    except (Conta.DoesNotExist, Salario.DoesNotExist, Beneficio.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Registro não encontrado'}, status=404)
    except (CategoriaConta.DoesNotExist, SubcategoriaConta.DoesNotExist, TipoBeneficio.DoesNotExist, Funcionario.DoesNotExist) as e:
        return JsonResponse({'success': False, 'message': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
