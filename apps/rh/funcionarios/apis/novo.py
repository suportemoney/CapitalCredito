"""
APIs para cadastro de novo funcionário
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from datetime import datetime
import re

from apps.rh.funcionarios.models import Funcionario, DadosProfissionais
from apps.rh.admin.models import Empresa, Loja, Departamento, Setor, Equipe, Cargo
from apps.rh.funcionarios.models import HorarioTrabalho
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.models import ControleAcessos, GroupsAcessos

def padronizar_username(apelido):
    """
    Padroniza o username: tudo minúsculo e espaços viram underscore
    Ex: 'EDUARDA SOARES' -> 'eduarda_soares'
    """
    if not apelido:
        return ''
    # Remover espaços extras e converter para minúsculo
    username = apelido.strip().lower()
    # Substituir espaços por underscore
    username = re.sub(r'\s+', '_', username)
    # Remover caracteres especiais (manter apenas letras, números e underscore)
    username = re.sub(r'[^a-z0-9_]', '', username)
    return username

@login_required
@controle_acess('SS17')
@require_http_methods(["POST"])
def api_criar_funcionario(request):
    """API para criar novo funcionário e usuário Django"""
    try:
        # Dados básicos
        apelido = request.POST.get('apelido', '').strip()
        nome_completo = request.POST.get('nome_completo', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        data_nascimento = request.POST.get('data_nascimento', '').strip()
        
        # Dados profissionais
        empresa_id = request.POST.get('empresa')
        departamento_id = request.POST.get('departamento')
        setor_id = request.POST.get('setor')
        loja_id = request.POST.get('loja', '').strip()
        equipe_id = request.POST.get('equipe', '').strip()
        cargo_id = request.POST.get('cargo')
        horario_id = request.POST.get('horario', '').strip()
        
        # Validações básicas
        if not apelido:
            return JsonResponse({'success': False, 'message': 'Apelido é obrigatório'})
        
        if not nome_completo:
            return JsonResponse({'success': False, 'message': 'Nome completo é obrigatório'})
        
        if not cpf:
            return JsonResponse({'success': False, 'message': 'CPF é obrigatório'})
        
        # Limpar CPF
        cpf_limpo = re.sub(r'\D', '', cpf)
        if len(cpf_limpo) != 11:
            return JsonResponse({'success': False, 'message': 'CPF inválido'})
        
        # Verificar se CPF já existe
        if Funcionario.objects.filter(cpf=cpf_limpo).exists():
            return JsonResponse({'success': False, 'message': 'CPF já cadastrado'})
        
        # Padronizar username
        username_padronizado = padronizar_username(apelido)
        if not username_padronizado:
            return JsonResponse({'success': False, 'message': 'Apelido inválido para gerar username'})
        
        # Verificar se username padronizado já existe
        if User.objects.filter(username=username_padronizado).exists():
            return JsonResponse({'success': False, 'message': f'Username "{username_padronizado}" já está em uso'})
        
        # Validações profissionais
        if not empresa_id:
            return JsonResponse({'success': False, 'message': 'Empresa é obrigatória'})
        
        if not departamento_id:
            return JsonResponse({'success': False, 'message': 'Departamento é obrigatório'})
        
        if not setor_id:
            return JsonResponse({'success': False, 'message': 'Setor é obrigatório'})
        
        if not cargo_id:
            return JsonResponse({'success': False, 'message': 'Cargo é obrigatório'})
        
        # Converter data de nascimento
        data_nasc = None
        if data_nascimento:
            try:
                data_nasc = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
            except:
                return JsonResponse({'success': False, 'message': 'Data de nascimento inválida'})
        
        # Buscar objetos relacionados
        empresa = Empresa.objects.get(id=empresa_id)
        departamento = Departamento.objects.get(id=departamento_id)
        setor = Setor.objects.get(id=setor_id)
        cargo = Cargo.objects.get(id=cargo_id)
        
        loja = None
        if loja_id:
            loja = Loja.objects.get(id=loja_id)
        
        equipe = None
        if equipe_id:
            equipe = Equipe.objects.get(id=equipe_id)
        
        horario = None
        if horario_id:
            horario = HorarioTrabalho.objects.get(id=horario_id)
        
        # Criar senha padrão: Capital@ano_atual
        ano_atual = datetime.now().year
        senha_padrao = f"Capital@{ano_atual}"
        
        with transaction.atomic():
            # Criar funcionário primeiro (sem usuário ainda)
            funcionario = Funcionario.objects.create(
                nome_completo=nome_completo.upper(),
                cpf=cpf_limpo,
                data_nascimento=data_nasc,
                usuario=None,  # Será preenchido após criar o usuário
                apelido=apelido.upper(),
                status=True
            )
            
            # Criar dados profissionais
            dados_profissionais = DadosProfissionais.objects.create(
                funcionario=funcionario,
                empresa=empresa,
                departamento=departamento,
                setor=setor,
                cargo=cargo,
                horario=horario
            )
            
            # Adicionar loja se fornecida
            if loja:
                dados_profissionais.lojas.add(loja)
            
            # Criar usuário Django após o funcionário (com username padronizado)
            usuario = User.objects.create_user(
                username=username_padronizado,
                email='',  # Email vazio por padrão
                password=senha_padrao,
                first_name=nome_completo.split()[0] if nome_completo else '',
                last_name=' '.join(nome_completo.split()[1:]) if len(nome_completo.split()) > 1 else ''
            )
            
            # Vincular usuário ao funcionário
            funcionario.usuario = usuario
            funcionario.save()
            grupo_id = request.POST.get('grupo_permissões', '').strip()
            if grupo_id:
                grupo = GroupsAcessos.objects.get(id=grupo_id, status=True)
                controle, _ = ControleAcessos.objects.get_or_create(user=usuario, defaults={'status': True})
                controle.acessos.set(grupo.acessos.filter(status=True))
        return JsonResponse({
            'success': True,
            'message': f'Funcionário "{apelido}" cadastrado com sucesso! Usuário criado com senha padrão: {senha_padrao}'
        })
        
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Empresa não encontrada'})
    except Departamento.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Departamento não encontrado'})
    except Setor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Setor não encontrado'})
    except Cargo.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cargo não encontrado'})
    except Loja.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Loja não encontrada'})
    except Equipe.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Equipe não encontrada'})
    except HorarioTrabalho.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Horário de trabalho não encontrado'})
    except GroupsAcessos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Grupo de permissões não encontrado ou inativo'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao cadastrar funcionário: {str(e)}'})

