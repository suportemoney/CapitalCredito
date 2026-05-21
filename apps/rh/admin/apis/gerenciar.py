"""
APIs para gerenciamento de modelos administrativos (CRUD)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core import serializers
from ..models import Empresa, Loja, NivelHierarquico, Cargo, Departamento, Setor, Equipe
from apps.seguranca.permissoes.decorators import controle_acess
import re
import json

# ========== EMPRESAS ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_empresa(request):
    """API para criar nova empresa"""
    try:
        nome = request.POST.get('nome')
        cnpj = request.POST.get('cnpj', '').strip()
        flg_parceira = request.POST.get('flg_parceira') == 'on'
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        # Limpar CNPJ (remover caracteres não numéricos)
        cnpj_limpo = re.sub(r'\D', '', cnpj) if cnpj else ''
        
        if cnpj_limpo and Empresa.objects.filter(cnpj=cnpj_limpo).exists():
            return JsonResponse({'success': False, 'message': 'CNPJ já cadastrado'})
        
        with transaction.atomic():
            empresa = Empresa.objects.create(
                nome=nome,
                cnpj=cnpj_limpo if cnpj_limpo else None,
                flg_parceira=flg_parceira,
                status=status
            )
        
        return JsonResponse({'success': True, 'message': 'Empresa criada com sucesso!', 'id': empresa.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_empresa(request, empresa_id):
    """API para editar empresa (GET retorna dados, POST salva)"""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': empresa.nome,
            'cnpj': empresa.cnpj or '',
            'flg_parceira': empresa.flg_parceira,
            'status': empresa.status
        })
    
    try:
        nome = request.POST.get('nome')
        cnpj = request.POST.get('cnpj', '').strip()
        flg_parceira = request.POST.get('flg_parceira') == 'on'
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        cnpj_limpo = re.sub(r'\D', '', cnpj) if cnpj else ''
        
        if cnpj_limpo and Empresa.objects.filter(cnpj=cnpj_limpo).exclude(id=empresa_id).exists():
            return JsonResponse({'success': False, 'message': 'CNPJ já cadastrado'})
        
        with transaction.atomic():
            empresa.nome = nome
            empresa.cnpj = cnpj_limpo if cnpj_limpo else None
            empresa.flg_parceira = flg_parceira
            empresa.status = status
            empresa.save()
        
        return JsonResponse({'success': True, 'message': 'Empresa atualizada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_empresa(request, empresa_id):
    """API para deletar empresa"""
    try:
        empresa = get_object_or_404(Empresa, id=empresa_id)
        empresa.delete()
        return JsonResponse({'success': True, 'message': 'Empresa deletada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========== LOJAS ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_loja(request):
    """API para criar nova loja"""
    try:
        nome = request.POST.get('nome')
        endereco = request.POST.get('endereco', '')
        flg_sede = request.POST.get('flg_sede') == 'on'
        flg_filial = request.POST.get('flg_filial') == 'on'
        flg_franquia = request.POST.get('flg_franquia') == 'on'
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        with transaction.atomic():
            loja = Loja.objects.create(
                nome=nome,
                endereco=endereco,
                flg_sede=flg_sede,
                flg_filial=flg_filial,
                flg_franquia=flg_franquia,
                status=status
            )
            
            if 'logo' in request.FILES:
                loja.logo = request.FILES['logo']
                loja.save(update_fields=['logo'])
        
        return JsonResponse({'success': True, 'message': 'Loja criada com sucesso!', 'id': loja.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_loja(request, loja_id):
    """API para editar loja (GET retorna dados, POST salva)"""
    loja = get_object_or_404(Loja, id=loja_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': loja.nome,
            'endereco': loja.endereco or '',
            'flg_sede': loja.flg_sede,
            'flg_filial': loja.flg_filial,
            'flg_franquia': loja.flg_franquia,
            'status': loja.status,
            'logo': loja.logo.url if loja.logo else None
        })
    
    try:
        nome = request.POST.get('nome')
        endereco = request.POST.get('endereco', '')
        flg_sede = request.POST.get('flg_sede') == 'on'
        flg_filial = request.POST.get('flg_filial') == 'on'
        flg_franquia = request.POST.get('flg_franquia') == 'on'
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        with transaction.atomic():
            loja.nome = nome
            loja.endereco = endereco
            loja.flg_sede = flg_sede
            loja.flg_filial = flg_filial
            loja.flg_franquia = flg_franquia
            loja.status = status
            
            if 'logo' in request.FILES:
                loja.logo = request.FILES['logo']
            elif request.POST.get('remover_logo') == 'on':
                loja.logo.delete(save=False)
                loja.logo = None
            
            loja.save()
        
        return JsonResponse({'success': True, 'message': 'Loja atualizada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_loja(request, loja_id):
    """API para deletar loja"""
    try:
        loja = get_object_or_404(Loja, id=loja_id)
        loja.delete()
        return JsonResponse({'success': True, 'message': 'Loja deletada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========== DEPARTAMENTOS ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_departamento(request):
    """API para criar novo departamento"""
    try:
        nome = request.POST.get('nome')
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        departamento = Departamento.objects.create(nome=nome, status=status)
        return JsonResponse({'success': True, 'message': 'Departamento criado com sucesso!', 'id': departamento.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_departamento(request, departamento_id):
    """API para editar departamento (GET retorna dados, POST salva)"""
    departamento = get_object_or_404(Departamento, id=departamento_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': departamento.nome,
            'status': departamento.status
        })
    
    try:
        nome = request.POST.get('nome')
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        departamento.nome = nome
        departamento.status = status
        departamento.save()
        
        return JsonResponse({'success': True, 'message': 'Departamento atualizado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_departamento(request, departamento_id):
    """API para deletar departamento"""
    try:
        departamento = get_object_or_404(Departamento, id=departamento_id)
        departamento.delete()
        return JsonResponse({'success': True, 'message': 'Departamento deletado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========== SETORES ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_setor(request):
    """API para criar novo setor"""
    try:
        nome = request.POST.get('nome')
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        setor = Setor.objects.create(nome=nome, status=status)
        return JsonResponse({'success': True, 'message': 'Setor criado com sucesso!', 'id': setor.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_setor(request, setor_id):
    """API para editar setor (GET retorna dados, POST salva)"""
    setor = get_object_or_404(Setor, id=setor_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': setor.nome,
            'status': setor.status
        })
    
    try:
        nome = request.POST.get('nome')
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        setor.nome = nome
        setor.status = status
        setor.save()
        
        return JsonResponse({'success': True, 'message': 'Setor atualizado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_setor(request, setor_id):
    """API para deletar setor"""
    try:
        setor = get_object_or_404(Setor, id=setor_id)
        setor.delete()
        return JsonResponse({'success': True, 'message': 'Setor deletado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========== CARGOS ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_cargo(request):
    """API para criar novo cargo"""
    try:
        nome = request.POST.get('nome')
        nivel_id = request.POST.get('nivel_hierarquico_id')
        status = request.POST.get('status') == 'on'
        
        if not nome or not nivel_id:
            return JsonResponse({'success': False, 'message': 'Nome e Nível Hierárquico são obrigatórios'})
        
        nivel = get_object_or_404(NivelHierarquico, id=nivel_id)
        
        if Cargo.objects.filter(nome=nome.upper(), nivel_hierarquico=nivel).exists():
            return JsonResponse({'success': False, 'message': 'Cargo já existe para este nível hierárquico'})
        
        cargo = Cargo.objects.create(nome=nome, nivel_hierarquico=nivel, status=status)
        return JsonResponse({'success': True, 'message': 'Cargo criado com sucesso!', 'id': cargo.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_cargo(request, cargo_id):
    """API para editar cargo (GET retorna dados, POST salva)"""
    cargo = get_object_or_404(Cargo, id=cargo_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': cargo.nome,
            'nivel_hierarquico_id': cargo.nivel_hierarquico.id,
            'status': cargo.status
        })
    
    try:
        nome = request.POST.get('nome')
        nivel_id = request.POST.get('nivel_hierarquico_id')
        status = request.POST.get('status') == 'on'
        
        if not nome or not nivel_id:
            return JsonResponse({'success': False, 'message': 'Nome e Nível Hierárquico são obrigatórios'})
        
        nivel = get_object_or_404(NivelHierarquico, id=nivel_id)
        
        if Cargo.objects.filter(nome=nome.upper(), nivel_hierarquico=nivel).exclude(id=cargo_id).exists():
            return JsonResponse({'success': False, 'message': 'Cargo já existe para este nível hierárquico'})
        
        cargo.nome = nome
        cargo.nivel_hierarquico = nivel
        cargo.status = status
        cargo.save()
        
        return JsonResponse({'success': True, 'message': 'Cargo atualizado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_cargo(request, cargo_id):
    """API para deletar cargo"""
    try:
        cargo = get_object_or_404(Cargo, id=cargo_id)
        cargo.delete()
        return JsonResponse({'success': True, 'message': 'Cargo deletado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========== EQUIPES ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_equipe(request):
    """API para criar nova equipe"""
    try:
        nome = request.POST.get('nome')
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        equipe = Equipe.objects.create(nome=nome, status=status)
        return JsonResponse({'success': True, 'message': 'Equipe criada com sucesso!', 'id': equipe.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_equipe(request, equipe_id):
    """API para editar equipe (GET retorna dados, POST salva)"""
    equipe = get_object_or_404(Equipe, id=equipe_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': equipe.nome,
            'status': equipe.status
        })
    
    try:
        nome = request.POST.get('nome')
        status = request.POST.get('status') == 'on'
        
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'})
        
        equipe.nome = nome
        equipe.status = status
        equipe.save()
        
        return JsonResponse({'success': True, 'message': 'Equipe atualizada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_equipe(request, equipe_id):
    """API para deletar equipe"""
    try:
        equipe = get_object_or_404(Equipe, id=equipe_id)
        equipe.delete()
        return JsonResponse({'success': True, 'message': 'Equipe deletada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========== NÍVEIS HIERÁRQUICOS ==========

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_criar_nivel(request):
    """API para criar novo nível hierárquico"""
    try:
        nome = request.POST.get('nome')
        importancia = request.POST.get('importancia')
        status = request.POST.get('status') == 'on'
        
        if not nome or not importancia:
            return JsonResponse({'success': False, 'message': 'Nome e Importância são obrigatórios'})
        
        try:
            importancia = int(importancia)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Importância deve ser um número'})
        
        nivel = NivelHierarquico.objects.create(nome=nome, importancia=importancia, status=status)
        return JsonResponse({'success': True, 'message': 'Nível hierárquico criado com sucesso!', 'id': nivel.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_editar_nivel(request, nivel_id):
    """API para editar nível hierárquico (GET retorna dados, POST salva)"""
    nivel = get_object_or_404(NivelHierarquico, id=nivel_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'nome': nivel.nome,
            'importancia': nivel.importancia,
            'status': nivel.status
        })
    
    try:
        nome = request.POST.get('nome')
        importancia = request.POST.get('importancia')
        status = request.POST.get('status') == 'on'
        
        if not nome or not importancia:
            return JsonResponse({'success': False, 'message': 'Nome e Importância são obrigatórios'})
        
        try:
            importancia = int(importancia)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Importância deve ser um número'})
        
        nivel.nome = nome
        nivel.importancia = importancia
        nivel.status = status
        nivel.save()
        
        return JsonResponse({'success': True, 'message': 'Nível hierárquico atualizado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
@require_http_methods(["POST"])
def api_deletar_nivel(request, nivel_id):
    """API para deletar nível hierárquico"""
    try:
        nivel = get_object_or_404(NivelHierarquico, id=nivel_id)
        nivel.delete()
        return JsonResponse({'success': True, 'message': 'Nível hierárquico deletado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@controle_acess('SS16')
def api_listar_niveis(request):
    """API para listar níveis hierárquicos (para select)"""
    niveis = NivelHierarquico.objects.filter(status=True).order_by('-importancia')
    niveis_data = [{'id': nivel.id, 'nome': nivel.nome, 'importancia': nivel.importancia} for nivel in niveis]
    return JsonResponse(niveis_data, safe=False)

# ========== APIs GET para atualizar tabelas ==========

@login_required
@controle_acess('SS16')
def api_get_empresas(request):
    """API GET para retornar lista de empresas em JSON"""
    empresas = Empresa.objects.all().order_by('nome')
    empresas_data = [{
        'id': emp.id,
        'nome': emp.nome,
        'cnpj': emp.cnpj or '',
        'flg_parceira': emp.flg_parceira,
        'status': emp.status,
        'data_criacao': emp.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for emp in empresas]
    return JsonResponse(empresas_data, safe=False)

@login_required
@controle_acess('SS16')
def api_get_lojas(request):
    """API GET para retornar lista de lojas em JSON"""
    lojas = Loja.objects.all().order_by('nome')
    lojas_data = [{
        'id': loja.id,
        'nome': loja.nome,
        'logo_url': loja.logo.url if loja.logo else None,
        'flg_sede': loja.flg_sede,
        'flg_filial': loja.flg_filial,
        'flg_franquia': loja.flg_franquia,
        'endereco': loja.endereco or '',
        'status': loja.status,
        'data_criacao': loja.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for loja in lojas]
    return JsonResponse(lojas_data, safe=False)

@login_required
@controle_acess('SS16')
def api_get_departamentos(request):
    """API GET para retornar lista de departamentos em JSON"""
    departamentos = Departamento.objects.all().order_by('nome')
    departamentos_data = [{
        'id': dep.id,
        'nome': dep.nome,
        'status': dep.status,
        'data_criacao': dep.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for dep in departamentos]
    return JsonResponse(departamentos_data, safe=False)

@login_required
@controle_acess('SS16')
def api_get_setores(request):
    """API GET para retornar lista de setores em JSON"""
    setores = Setor.objects.all().order_by('nome')
    setores_data = [{
        'id': setor.id,
        'nome': setor.nome,
        'status': setor.status,
        'data_criacao': setor.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for setor in setores]
    return JsonResponse(setores_data, safe=False)

@login_required
@controle_acess('SS16')
def api_get_cargos(request):
    """API GET para retornar lista de cargos em JSON"""
    cargos = Cargo.objects.select_related('nivel_hierarquico').all().order_by('nivel_hierarquico__importancia', 'nome')
    cargos_data = [{
        'id': cargo.id,
        'nome': cargo.nome,
        'nivel_hierarquico_id': cargo.nivel_hierarquico.id,
        'nivel_hierarquico_nome': cargo.nivel_hierarquico.nome,
        'nivel_hierarquico_importancia': cargo.nivel_hierarquico.importancia,
        'status': cargo.status,
        'data_criacao': cargo.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for cargo in cargos]
    return JsonResponse(cargos_data, safe=False)

@login_required
@controle_acess('SS16')
def api_get_equipes(request):
    """API GET para retornar lista de equipes em JSON"""
    equipes = Equipe.objects.all().order_by('nome')
    equipes_data = [{
        'id': equipe.id,
        'nome': equipe.nome,
        'status': equipe.status,
        'data_criacao': equipe.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for equipe in equipes]
    return JsonResponse(equipes_data, safe=False)

@login_required
@controle_acess('SS16')
def api_get_niveis(request):
    """API GET para retornar lista de níveis hierárquicos em JSON"""
    niveis = NivelHierarquico.objects.all().order_by('-importancia')
    niveis_data = [{
        'id': nivel.id,
        'nome': nivel.nome,
        'importancia': nivel.importancia,
        'status': nivel.status,
        'data_criacao': nivel.data_criacao.strftime('%d/%m/%Y %H:%M')
    } for nivel in niveis]
    return JsonResponse(niveis_data, safe=False)

