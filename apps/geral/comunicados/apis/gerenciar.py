"""
APIs para gerenciar comunicados (CRUD)
Templates: listar.html, criar.html, editar.html
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from apps.geral.comunicados.models import Comunicado, CategoriaComunicado, ArquivoComunicado

@login_required
@require_http_methods(["POST"])
def api_criar(request):
    """API para criar novo comunicado"""
    try:
        titulo = request.POST.get('titulo')
        tipo = request.POST.get('tipo', 'GERAL')
        categoria_id = request.POST.get('categoria')
        conteudo = request.POST.get('conteudo')
        prioridade = request.POST.get('prioridade', 'NORMAL')
        fixo = request.POST.get('fixo') == 'on'
        status = request.POST.get('status', 'on') == 'on'  # Default True
        data_evento = request.POST.get('data_evento') or None
        
        if not titulo or not conteudo:
            return JsonResponse({'success': False, 'message': 'Título e conteúdo são obrigatórios'})
        
        # Criar comunicado
        comunicado = Comunicado.objects.create(
            titulo=titulo,
            tipo=tipo,
            categoria_id=categoria_id if categoria_id else None,
            conteudo=conteudo,
            prioridade=prioridade,
            fixo=fixo,
            status=status,
            data_evento=data_evento,
            criado_por=request.user
        )
        
        # Processar banner se enviado
        if 'banner' in request.FILES:
            comunicado.banner = request.FILES['banner']
            comunicado.save()
        
        # Processar arquivos anexos
        if 'arquivos[]' in request.FILES:
            arquivos = request.FILES.getlist('arquivos[]')
            titulos_arquivos = request.POST.getlist('titulos_arquivos[]')
            
            for i, arquivo in enumerate(arquivos):
                titulo_arquivo = titulos_arquivos[i] if i < len(titulos_arquivos) else None
                ArquivoComunicado.objects.create(
                    comunicado=comunicado,
                    arquivo=arquivo,
                    titulo=titulo_arquivo
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Comunicado criado com sucesso!',
            'comunicado_id': comunicado.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["POST"])
def api_editar(request, comunicado_id):
    """API para editar comunicado existente"""
    try:
        comunicado = get_object_or_404(Comunicado, id=comunicado_id)
        
        titulo = request.POST.get('titulo')
        tipo = request.POST.get('tipo')
        categoria_id = request.POST.get('categoria')
        conteudo = request.POST.get('conteudo')
        prioridade = request.POST.get('prioridade')
        fixo = request.POST.get('fixo') == 'on'
        status = request.POST.get('status', 'on') == 'on'
        data_evento = request.POST.get('data_evento') or None
        
        if not titulo or not conteudo:
            return JsonResponse({'success': False, 'message': 'Título e conteúdo são obrigatórios'})
        
        # Atualizar campos
        comunicado.titulo = titulo
        comunicado.tipo = tipo
        comunicado.categoria_id = categoria_id if categoria_id else None
        comunicado.conteudo = conteudo
        comunicado.prioridade = prioridade
        comunicado.fixo = fixo
        comunicado.status = status
        comunicado.data_evento = data_evento
        comunicado.save()
        
        # Processar banner se enviado
        if 'banner' in request.FILES:
            comunicado.banner = request.FILES['banner']
            comunicado.save()
        
        # Processar novos arquivos anexos
        if 'arquivos[]' in request.FILES:
            arquivos = request.FILES.getlist('arquivos[]')
            titulos_arquivos = request.POST.getlist('titulos_arquivos[]')
            
            for i, arquivo in enumerate(arquivos):
                titulo_arquivo = titulos_arquivos[i] if i < len(titulos_arquivos) else None
                ArquivoComunicado.objects.create(
                    comunicado=comunicado,
                    arquivo=arquivo,
                    titulo=titulo_arquivo
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Comunicado atualizado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["POST"])
def api_deletar(request, comunicado_id):
    """API para deletar comunicado"""
    try:
        comunicado = get_object_or_404(Comunicado, id=comunicado_id)
        comunicado.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Comunicado deletado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["POST"])
def api_toggle_status(request, comunicado_id):
    """API para alternar status do comunicado (ativo/inativo)"""
    try:
        comunicado = get_object_or_404(Comunicado, id=comunicado_id)
        comunicado.status = not comunicado.status
        comunicado.save()
        
        status_text = 'ativado' if comunicado.status else 'desativado'
        return JsonResponse({
            'success': True,
            'message': f'Comunicado {status_text} com sucesso!',
            'status': comunicado.status
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_http_methods(["POST"])
def api_deletar_arquivo(request, arquivo_id):
    """API para deletar arquivo anexo"""
    try:
        arquivo = get_object_or_404(ArquivoComunicado, id=arquivo_id)
        arquivo.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Arquivo deletado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

