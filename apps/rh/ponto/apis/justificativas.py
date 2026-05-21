"""
APIs para justificativas
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from apps.rh.ponto.models import Justificativa, JustificativaArquivo
from apps.rh.funcionarios.models import Funcionario
from apps.seguranca.permissoes.decorators import controle_acess

@login_required
@controle_acess('SS41')
@require_http_methods(["POST"])
def api_criar_justificativa(request):
    """API para criar justificativa (individual ou em lote)"""
    try:
        titulo = request.POST.get('titulo', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        data_inicio = request.POST.get('data_inicio', '').strip()
        data_fim = request.POST.get('data_fim', '').strip()
        funcionario_id = request.POST.get('funcionario_id', '').strip()
        funcionarios_ids = request.POST.getlist('funcionarios_ids[]')
        observacoes = request.POST.get('observacoes', '').strip()
        arquivos = request.FILES.getlist('arquivos[]')
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        if not tipo or tipo not in [Justificativa.TIPO_FERIAS, Justificativa.TIPO_ABONO, Justificativa.TIPO_ATESTADO, Justificativa.TIPO_FERIADO]:
            return JsonResponse({'success': False, 'message': 'Tipo inválido'})
        if not data_inicio:
            return JsonResponse({'success': False, 'message': 'Data início é obrigatória'})
        if not data_fim:
            return JsonResponse({'success': False, 'message': 'Data fim é obrigatória'})
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except:
            return JsonResponse({'success': False, 'message': 'Formato de data inválido'})
        if data_fim_obj < data_inicio_obj:
            return JsonResponse({'success': False, 'message': 'Data fim não pode ser anterior à data início'})
        funcionarios_para_processar = []
        if funcionarios_ids:
            for func_id in funcionarios_ids:
                try:
                    funcionario = Funcionario.objects.get(id=func_id, status=True)
                    funcionarios_para_processar.append(funcionario)
                except Funcionario.DoesNotExist:
                    continue
        elif funcionario_id:
            try:
                funcionario = Funcionario.objects.get(id=funcionario_id, status=True)
                funcionarios_para_processar.append(funcionario)
            except Funcionario.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'})
        else:
            return JsonResponse({'success': False, 'message': 'Selecione pelo menos um funcionário'})
        justificativas_criadas = []
        for funcionario in funcionarios_para_processar:
            justificativa = Justificativa.objects.create(
                titulo=titulo.upper(),
                tipo=tipo,
                funcionario=funcionario,
                data_inicio=data_inicio_obj,
                data_fim=data_fim_obj,
                observacoes=observacoes,
                status=True,
                criado_por=request.user
            )
            for arquivo in arquivos:
                JustificativaArquivo.objects.create(
                    justificativa=justificativa,
                    arquivo=arquivo,
                    titulo=arquivo.name.upper()
                )
            justificativas_criadas.append({
                'id': justificativa.id,
                'funcionario': funcionario.nome_completo,
            })
        mensagem = f'Justificativa criada para {len(justificativas_criadas)} funcionário(s)'
        if len(justificativas_criadas) == 1:
            mensagem = f'Justificativa criada com sucesso para {justificativas_criadas[0]["funcionario"]}'
        return JsonResponse({
            'success': True,
            'message': mensagem,
            'data': justificativas_criadas
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar justificativa: {str(e)}'})

@login_required
@controle_acess('SS41')
@require_http_methods(["GET"])
def api_listar_justificativas(request):
    """API para listar justificativas"""
    try:
        funcionario_id = request.GET.get('funcionario_id', '').strip()
        tipo = request.GET.get('tipo', '').strip()
        data_inicio = request.GET.get('data_inicio', '').strip()
        data_fim = request.GET.get('data_fim', '').strip()
        justificativas = Justificativa.objects.filter(status=True).select_related('funcionario', 'criado_por').prefetch_related('arquivos')
        if funcionario_id:
            justificativas = justificativas.filter(funcionario_id=funcionario_id)
        if tipo:
            justificativas = justificativas.filter(tipo=tipo)
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                justificativas = justificativas.filter(data_fim__gte=data_inicio_obj)
            except:
                pass
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                justificativas = justificativas.filter(data_inicio__lte=data_fim_obj)
            except:
                pass
        justificativas = justificativas.order_by('-data_criacao')[:100]
        resultado = []
        for just in justificativas:
            arquivos_list = []
            for arquivo in just.arquivos.all():
                arquivos_list.append({
                    'id': arquivo.id,
                    'titulo': arquivo.titulo,
                    'url': arquivo.arquivo.url if arquivo.arquivo else None,
                })
            resultado.append({
                'id': just.id,
                'titulo': just.titulo,
                'tipo': just.get_tipo_display(),
                'funcionario': just.funcionario.nome_completo if just.funcionario else 'Em Lote',
                'funcionario_id': just.funcionario.id if just.funcionario else None,
                'data_inicio': just.data_inicio.strftime('%d/%m/%Y'),
                'data_fim': just.data_fim.strftime('%d/%m/%Y'),
                'observacoes': just.observacoes,
                'criado_por': just.criado_por.username if just.criado_por else None,
                'data_criacao': just.data_criacao.strftime('%d/%m/%Y %H:%M:%S'),
                'arquivos': arquivos_list,
            })
        return JsonResponse({
            'success': True,
            'data': resultado
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar justificativas: {str(e)}'})
