from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from apps.seguranca.permissoes.decorators import controle_acess, controle_acess_any
from apps.tesouraria.bonificacoes.models import BonificacaoRegra, BonificacaoFuncionarioRegra
from apps.rh.funcionarios.models import Funcionario
from apps.rh.admin.models import Empresa, Setor

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_setores_empresas(request):
    try:
        setores = [{'id': s.id, 'nome': s.nome} for s in Setor.objects.filter(status=True).order_by('nome')]
        empresas = [{'id': e.id, 'nome': e.nome} for e in Empresa.objects.filter(status=True).order_by('nome')]
        return JsonResponse({'success': True, 'result': {'setores': setores, 'empresas': empresas}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["GET"])
def api_get_vinculos(request):
    try:
        setor_id = request.GET.get('setor_id', '').strip()
        empresa_id = request.GET.get('empresa_id', '').strip()
        qs = BonificacaoFuncionarioRegra.objects.select_related('funcionario', 'regra').prefetch_related('funcionario__dados_profissionais').all()
        if setor_id:
            qs = qs.filter(funcionario__dados_profissionais__setor_id=setor_id)
        if empresa_id:
            qs = qs.filter(funcionario__dados_profissionais__empresa_id=empresa_id)
        qs = qs.order_by('-prioridade', 'funcionario__nome_completo', 'regra__nome')
        data = []
        for v in qs:
            dados_prof = getattr(v.funcionario, 'dados_profissionais', None)
            setor_nome = dados_prof.setor.nome if dados_prof and dados_prof.setor else ''
            empresa_nome = dados_prof.empresa.nome if dados_prof and dados_prof.empresa else ''
            data.append({'id': v.id, 'funcionario_id': v.funcionario_id, 'funcionario_nome': v.funcionario.nome_completo, 'regra_id': v.regra_id, 'regra_nome': v.regra.nome, 'ativo': v.ativo, 'data_inicio': v.data_inicio.strftime('%Y-%m-%d') if v.data_inicio else '', 'data_fim': v.data_fim.strftime('%Y-%m-%d') if v.data_fim else '', 'prioridade': v.prioridade, 'setor_nome': setor_nome, 'empresa_nome': empresa_nome})
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess_any('SS45', 'SS46')
@require_http_methods(["GET"])
def api_get_funcionarios_simples(request):
    try:
        setor_id = request.GET.get('setor_id', '').strip()
        empresa_id = request.GET.get('empresa_id', '').strip()
        incluir_inativos = request.GET.get('incluir_inativos', '').lower() in ('true', '1')
        qs = Funcionario.objects.all() if incluir_inativos else Funcionario.objects.filter(status=True)
        qs = qs.select_related('dados_profissionais').order_by('nome_completo')
        if setor_id:
            qs = qs.filter(dados_profissionais__setor_id=setor_id)
        if empresa_id:
            qs = qs.filter(dados_profissionais__empresa_id=empresa_id)
        data = [{'id': f.id, 'nome': f.nome_completo} for f in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess_any('SS45', 'SS46')
@require_http_methods(["GET"])
def api_get_regras_simples(request):
    try:
        apenas_ativos = request.GET.get('ativos', 'true').lower() == 'true'
        qs = BonificacaoRegra.objects.all()
        if apenas_ativos:
            qs = qs.filter(ativo=True)
        qs = qs.order_by('nome')
        data = [{'id': r.id, 'nome': r.nome} for r in qs]
        return JsonResponse({'success': True, 'result': data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_vinculo(request):
    try:
        vinculo_id = request.POST.get('vinculo_id', '').strip()
        funcionario_id = request.POST.get('funcionario_id')
        regra_id = request.POST.get('regra_id')
        ativo = request.POST.get('ativo', 'true').strip()
        data_inicio = request.POST.get('data_inicio', '').strip()
        data_fim = request.POST.get('data_fim', '').strip()
        prioridade = request.POST.get('prioridade', '0').strip()
        if not funcionario_id or not regra_id:
            return JsonResponse({'success': False, 'message': 'Funcionário e regra são obrigatórios'})
        with transaction.atomic():
            if vinculo_id:
                vinculo = BonificacaoFuncionarioRegra.objects.get(id=vinculo_id)
            else:
                if BonificacaoFuncionarioRegra.objects.filter(funcionario_id=funcionario_id, regra_id=regra_id).exists():
                    return JsonResponse({'success': False, 'message': 'Já existe vínculo para este funcionário e regra'})
                vinculo = BonificacaoFuncionarioRegra(funcionario_id=funcionario_id, regra_id=regra_id)
            vinculo.ativo = ativo.lower() in ('true', '1', 'ativo')
            vinculo.data_inicio = data_inicio if data_inicio else None
            vinculo.data_fim = data_fim if data_fim else None
            vinculo.prioridade = int(prioridade) if prioridade else 0
            vinculo.save()
        return JsonResponse({'success': True, 'message': 'Vínculo salvo.', 'result': {'id': vinculo.id}})
    except BonificacaoFuncionarioRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vínculo não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_vinculos_lote(request):
    try:
        funcionario_ids = request.POST.getlist('funcionario_ids[]') or request.POST.get('funcionario_ids', '').split(',')
        regra_ids = request.POST.getlist('regra_ids[]') or request.POST.get('regra_ids', '').split(',')
        funcionario_ids = [x.strip() for x in funcionario_ids if x and str(x).strip().isdigit()]
        regra_ids = [x.strip() for x in regra_ids if x and str(x).strip().isdigit()]
        data_inicio = request.POST.get('data_inicio', '').strip() or None
        data_fim = request.POST.get('data_fim', '').strip() or None
        prioridade = int(request.POST.get('prioridade', '0') or 0)
        if not funcionario_ids or not regra_ids:
            return JsonResponse({'success': False, 'message': 'Selecione ao menos um funcionário e uma regra'})
        criados = 0
        ja_existentes = 0
        with transaction.atomic():
            for fid in funcionario_ids:
                for rid in regra_ids:
                    if BonificacaoFuncionarioRegra.objects.filter(funcionario_id=fid, regra_id=rid).exists():
                        ja_existentes += 1
                        continue
                    BonificacaoFuncionarioRegra.objects.create(
                        funcionario_id=fid, regra_id=rid, ativo=True,
                        data_inicio=data_inicio, data_fim=data_fim, prioridade=prioridade
                    )
                    criados += 1
        msg = f'{criados} vínculo(s) criado(s).'
        if ja_existentes:
            msg += f' {ja_existentes} já existia(m) e foi(ram) ignorado(s).'
        return JsonResponse({'success': True, 'message': msg, 'result': {'criados': criados, 'ja_existentes': ja_existentes}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@controle_acess('SS45')
@require_http_methods(["POST"])
def api_post_deletar_vinculo(request):
    try:
        vinculo_id = request.POST.get('vinculo_id')
        if not vinculo_id:
            return JsonResponse({'success': False, 'message': 'ID do vínculo é obrigatório'})
        vinculo = BonificacaoFuncionarioRegra.objects.get(id=vinculo_id)
        vinculo.delete()
        return JsonResponse({'success': True, 'message': 'Vínculo excluído.', 'result': None})
    except BonificacaoFuncionarioRegra.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vínculo não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
