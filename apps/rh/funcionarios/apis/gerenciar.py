"""
APIs para gerenciar funcionários (listar com filtros, buscar completo, editar)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.conf import settings
import re
import os

from apps.rh.funcionarios.models import (
    Funcionario, DadosProfissionais, DadosPessoais, 
    Contato, Localizacao, Genero, TipoContrato, HorarioTrabalho, Arquivos
)
from apps.rh.admin.models import Empresa, Loja, Departamento, Setor, Equipe, Cargo
from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.models import ControleAcessos, GroupsAcessos

@login_required
@controle_acess('SS18')
@require_http_methods(["GET"])
def api_listar_funcionarios(request):
    """API GET para listar funcionários com filtros"""
    try:
        status = request.GET.get('status', 'ativo')
        empresa_id = request.GET.get('empresa', '')
        departamento_id = request.GET.get('departamento', '')
        setor_id = request.GET.get('setor', '')
        loja_id = request.GET.get('loja', '')
        equipe_id = request.GET.get('equipe', '')
        cargo_id = request.GET.get('cargo', '')
        busca = request.GET.get('busca', '').strip()
        
        funcionarios = Funcionario.objects.select_related(
            'usuario',
            'dados_profissionais__empresa',
            'dados_profissionais__departamento',
            'dados_profissionais__setor',
            'dados_profissionais__equipe',
            'dados_profissionais__cargo',
            'dados_profissionais__horario'
        ).prefetch_related('dados_profissionais__lojas').all()
        
        if status == 'ativo':
            funcionarios = funcionarios.filter(status=True)
        elif status == 'inativo':
            funcionarios = funcionarios.filter(status=False)
        
        if empresa_id:
            funcionarios = funcionarios.filter(dados_profissionais__empresa_id=empresa_id)
        if departamento_id:
            funcionarios = funcionarios.filter(dados_profissionais__departamento_id=departamento_id)
        if setor_id:
            funcionarios = funcionarios.filter(dados_profissionais__setor_id=setor_id)
        if loja_id:
            funcionarios = funcionarios.filter(dados_profissionais__lojas__id=loja_id).distinct()
        if equipe_id:
            funcionarios = funcionarios.filter(dados_profissionais__equipe_id=equipe_id)
        if cargo_id:
            funcionarios = funcionarios.filter(dados_profissionais__cargo_id=cargo_id)
        
        if busca:
            funcionarios = funcionarios.filter(
                Q(nome_completo__icontains=busca) |
                Q(apelido__icontains=busca) |
                Q(cpf__icontains=busca)
            )
        
        funcionarios = funcionarios.order_by('nome_completo')
        
        funcionarios_data = []
        for func in funcionarios:
            dados_prof = func.dados_profissionais
            lojas = [loja.nome for loja in dados_prof.lojas.all()] if dados_prof else []
            
            funcionarios_data.append({
                'id': func.id,
                'apelido': func.apelido or '',
                'nome_completo': func.nome_completo,
                'cpf': func.cpf,
                'data_nascimento': func.data_nascimento.strftime('%d/%m/%Y') if func.data_nascimento else '',
                'empresa': dados_prof.empresa.nome if dados_prof and dados_prof.empresa else '',
                'departamento': dados_prof.departamento.nome if dados_prof and dados_prof.departamento else '',
                'setor': dados_prof.setor.nome if dados_prof and dados_prof.setor else '',
                'lojas': ', '.join(lojas) if lojas else '-',
                'equipe': dados_prof.equipe.nome if dados_prof and dados_prof.equipe else '-',
                'cargo': dados_prof.cargo.nome if dados_prof and dados_prof.cargo else '',
                'horario': dados_prof.horario.nome if dados_prof and dados_prof.horario else '-',
                'status': func.status,
                'usuario_id': func.usuario.id if func.usuario else None,
                'usuario_username': func.usuario.username if func.usuario else '',
                'data_criacao': func.data_criacao.strftime('%d/%m/%Y %H:%M')
            })
        
        return JsonResponse(funcionarios_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar funcionários: {str(e)}'}, status=500)

@login_required
@controle_acess('SS18')
@require_http_methods(["GET"])
def api_buscar_funcionario(request, funcionario_id):
    """API GET para buscar dados completos do funcionário"""
    try:
        funcionario = Funcionario.objects.select_related(
            'usuario',
            'dados_profissionais__empresa',
            'dados_profissionais__departamento',
            'dados_profissionais__setor',
            'dados_profissionais__equipe',
            'dados_profissionais__cargo',
            'dados_profissionais__tipo_contrato',
            'dados_profissionais__horario',
            'dados_pessoais__genero',
            'contato',
            'localizacao'
        ).prefetch_related('dados_profissionais__lojas').get(id=funcionario_id)
        
        dados_prof = getattr(funcionario, 'dados_profissionais', None)
        dados_pessoais = getattr(funcionario, 'dados_pessoais', None)
        contato = getattr(funcionario, 'contato', None)
        localizacao = getattr(funcionario, 'localizacao', None)
        
        lojas_ids = [loja.id for loja in dados_prof.lojas.all()] if dados_prof else []
        
        data = {
            'id': funcionario.id,
            'apelido': funcionario.apelido or '',
            'nome_completo': funcionario.nome_completo,
            'cpf': funcionario.cpf,
            'rg': funcionario.rg or '',
            'data_nascimento': funcionario.data_nascimento.strftime('%Y-%m-%d') if funcionario.data_nascimento else '',
            'foto': funcionario.foto.url if funcionario.foto else '',
            'chave_pix': funcionario.chave_pix or '',
            'status': funcionario.status,
            'usuario_id': funcionario.usuario.id if funcionario.usuario else None,
            'usuario_username': funcionario.usuario.username if funcionario.usuario else '',
            'dados_pessoais': {
                'genero_id': dados_pessoais.genero.id if dados_pessoais and dados_pessoais.genero else None,
                'estado_civil': dados_pessoais.estado_civil if dados_pessoais and dados_pessoais.estado_civil else '',
                'nacionalidade': dados_pessoais.nacionalidade or '' if dados_pessoais else '',
                'naturalidade': dados_pessoais.naturalidade or '' if dados_pessoais else '',
            } if dados_pessoais else {
                'genero_id': None,
                'estado_civil': '',
                'nacionalidade': '',
                'naturalidade': '',
            },
            'contato': {
                'email_pessoa': contato.email_pessoa or '' if contato else '',
                'celular_1': contato.celular_1 or '' if contato else '',
                'celular_2': contato.celular_2 or '' if contato else '',
            } if contato else {
                'email_pessoa': '',
                'celular_1': '',
                'celular_2': '',
            },
            'localizacao': {
                'cep': localizacao.cep or '' if localizacao else '',
                'endereco': localizacao.endereco or '' if localizacao else '',
                'numero': localizacao.numero or '' if localizacao else '',
                'complemento': localizacao.complemento or '' if localizacao else '',
                'bairro': localizacao.bairro or '' if localizacao else '',
                'cidade': localizacao.cidade or '' if localizacao else '',
                'estado': localizacao.estado or '' if localizacao else '',
            } if localizacao else {
                'cep': '',
                'endereco': '',
                'numero': '',
                'complemento': '',
                'bairro': '',
                'cidade': '',
                'estado': '',
            },
            'dados_profissionais': {
                'pis': dados_prof.pis or '' if dados_prof else '',
                'matricula': dados_prof.matricula or '' if dados_prof else '',
                'tipo_contrato_id': dados_prof.tipo_contrato.id if dados_prof and dados_prof.tipo_contrato else None,
                'empresa_id': dados_prof.empresa.id if dados_prof and dados_prof.empresa else None,
                'departamento_id': dados_prof.departamento.id if dados_prof and dados_prof.departamento else None,
                'setor_id': dados_prof.setor.id if dados_prof and dados_prof.setor else None,
                'equipe_id': dados_prof.equipe.id if dados_prof and dados_prof.equipe else None,
                'cargo_id': dados_prof.cargo.id if dados_prof and dados_prof.cargo else None,
                'horario_id': dados_prof.horario.id if dados_prof and dados_prof.horario else None,
                'lojas_ids': lojas_ids,
                'data_admissao': dados_prof.data_admissao.strftime('%Y-%m-%d') if dados_prof and dados_prof.data_admissao else '',
                'data_demissao': dados_prof.data_demissao.strftime('%Y-%m-%d') if dados_prof and dados_prof.data_demissao else '',
            } if dados_prof else {
                'pis': '',
                'matricula': '',
                'tipo_contrato_id': None,
                'empresa_id': None,
                'departamento_id': None,
                'setor_id': None,
                'equipe_id': None,
                'cargo_id': None,
                'horario_id': None,
                'lojas_ids': [],
                'data_admissao': '',
                'data_demissao': '',
            },
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao buscar funcionário: {str(e)}'}, status=500)

@login_required
@controle_acess('SS18')
@require_http_methods(["POST"])
def api_editar_funcionario(request, funcionario_id):
    """API POST para editar funcionário completo"""
    try:
        funcionario = Funcionario.objects.get(id=funcionario_id)
        
        with transaction.atomic():
            # Dados básicos do funcionário
            apelido = request.POST.get('apelido', '').strip()
            nome_completo = request.POST.get('nome_completo', '').strip()
            cpf = request.POST.get('cpf', '').strip()
            rg = request.POST.get('rg', '').strip()
            data_nascimento = request.POST.get('data_nascimento', '').strip()
            chave_pix = request.POST.get('chave_pix', '').strip()
            status = request.POST.get('status', 'on') == 'on'
            remover_foto = request.POST.get('remover_foto', 'false') == 'true'
            
            if not nome_completo:
                return JsonResponse({'success': False, 'message': 'Nome completo é obrigatório'})
            
            if not cpf:
                return JsonResponse({'success': False, 'message': 'CPF é obrigatório'})
            
            cpf_limpo = re.sub(r'\D', '', cpf)
            if len(cpf_limpo) != 11:
                return JsonResponse({'success': False, 'message': 'CPF inválido'})
            
            if Funcionario.objects.filter(cpf=cpf_limpo).exclude(id=funcionario_id).exists():
                return JsonResponse({'success': False, 'message': 'CPF já cadastrado para outro funcionário'})
            
            data_nasc = None
            if data_nascimento:
                from datetime import datetime
                try:
                    data_nasc = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
                except:
                    return JsonResponse({'success': False, 'message': 'Data de nascimento inválida'})
            
            funcionario.apelido = apelido.upper() if apelido else None
            funcionario.nome_completo = nome_completo.upper()
            funcionario.cpf = cpf_limpo
            funcionario.rg = rg.upper() if rg else None
            funcionario.data_nascimento = data_nasc
            funcionario.chave_pix = chave_pix if chave_pix else None
            funcionario.status = status
            
            if remover_foto and funcionario.foto:
                if os.path.isfile(funcionario.foto.path):
                    os.remove(funcionario.foto.path)
                funcionario.foto = None
            elif 'foto' in request.FILES:
                if funcionario.foto:
                    if os.path.isfile(funcionario.foto.path):
                        os.remove(funcionario.foto.path)
                funcionario.foto = request.FILES['foto']
            
            funcionario.save()
            
            # Dados Pessoais
            genero_id = request.POST.get('genero', '').strip()
            estado_civil = request.POST.get('estado_civil', '').strip()
            nacionalidade = request.POST.get('nacionalidade', '').strip()
            naturalidade = request.POST.get('naturalidade', '').strip()
            
            dados_pessoais, created = DadosPessoais.objects.get_or_create(funcionario=funcionario)
            dados_pessoais.genero = Genero.objects.get(id=genero_id) if genero_id else None
            dados_pessoais.estado_civil = estado_civil if estado_civil else None
            dados_pessoais.nacionalidade = nacionalidade.upper() if nacionalidade else None
            dados_pessoais.naturalidade = naturalidade.upper() if naturalidade else None
            dados_pessoais.save()
            
            # Contato
            email_pessoa = request.POST.get('email_pessoa', '').strip()
            celular_1 = request.POST.get('celular_1', '').strip()
            celular_2 = request.POST.get('celular_2', '').strip()
            
            contato, created = Contato.objects.get_or_create(funcionario=funcionario)
            contato.email_pessoa = email_pessoa if email_pessoa else None
            contato.celular_1 = celular_1 if celular_1 else None
            contato.celular_2 = celular_2 if celular_2 else None
            contato.save()
            
            # Localização
            cep = request.POST.get('cep', '').strip()
            endereco = request.POST.get('endereco', '').strip()
            numero = request.POST.get('numero', '').strip()
            complemento = request.POST.get('complemento', '').strip()
            bairro = request.POST.get('bairro', '').strip()
            cidade = request.POST.get('cidade', '').strip()
            estado = request.POST.get('estado', '').strip()
            
            localizacao, created = Localizacao.objects.get_or_create(funcionario=funcionario)
            localizacao.cep = cep if cep else None
            localizacao.endereco = endereco.upper() if endereco else None
            localizacao.numero = numero if numero else None
            localizacao.complemento = complemento.upper() if complemento else None
            localizacao.bairro = bairro.upper() if bairro else None
            localizacao.cidade = cidade.upper() if cidade else None
            localizacao.estado = estado.upper() if estado else None
            localizacao.save()
            
            # Dados Profissionais
            pis = request.POST.get('pis', '').strip()
            matricula = request.POST.get('matricula', '').strip()
            tipo_contrato_id = request.POST.get('tipo_contrato', '').strip()
            empresa_id = request.POST.get('empresa', '').strip()
            departamento_id = request.POST.get('departamento', '').strip()
            setor_id = request.POST.get('setor', '').strip()
            equipe_id = request.POST.get('equipe', '').strip()
            cargo_id = request.POST.get('cargo', '').strip()
            horario_id = request.POST.get('horario', '').strip()
            data_admissao = request.POST.get('data_admissao', '').strip()
            data_demissao = request.POST.get('data_demissao', '').strip()
            lojas_ids = request.POST.getlist('lojas[]')
            
            if not empresa_id:
                return JsonResponse({'success': False, 'message': 'Empresa é obrigatória'})
            if not departamento_id:
                return JsonResponse({'success': False, 'message': 'Departamento é obrigatório'})
            if not setor_id:
                return JsonResponse({'success': False, 'message': 'Setor é obrigatório'})
            if not cargo_id:
                return JsonResponse({'success': False, 'message': 'Cargo é obrigatório'})
            
            dados_prof, created = DadosProfissionais.objects.get_or_create(funcionario=funcionario)
            dados_prof.pis = pis if pis else None
            dados_prof.matricula = matricula if matricula else None
            dados_prof.tipo_contrato = TipoContrato.objects.get(id=tipo_contrato_id) if tipo_contrato_id else None
            dados_prof.empresa = Empresa.objects.get(id=empresa_id)
            dados_prof.departamento = Departamento.objects.get(id=departamento_id)
            dados_prof.setor = Setor.objects.get(id=setor_id)
            dados_prof.equipe = Equipe.objects.get(id=equipe_id) if equipe_id else None
            dados_prof.cargo = Cargo.objects.get(id=cargo_id)
            dados_prof.horario = HorarioTrabalho.objects.get(id=horario_id) if horario_id else None
            
            if data_admissao:
                from datetime import datetime
                try:
                    dados_prof.data_admissao = datetime.strptime(data_admissao, '%Y-%m-%d').date()
                except:
                    pass
            else:
                dados_prof.data_admissao = None
            
            if data_demissao:
                from datetime import datetime
                try:
                    dados_prof.data_demissao = datetime.strptime(data_demissao, '%Y-%m-%d').date()
                except:
                    pass
            else:
                dados_prof.data_demissao = None
            
            dados_prof.save()
            
            # Atualizar lojas
            dados_prof.lojas.clear()
            for loja_id in lojas_ids:
                if loja_id:
                    try:
                        loja = Loja.objects.get(id=loja_id)
                        dados_prof.lojas.add(loja)
                    except Loja.DoesNotExist:
                        pass
            grupo_id = request.POST.get('grupo_permissões', '').strip()
            if funcionario.usuario and grupo_id:
                grupo = GroupsAcessos.objects.get(id=grupo_id, status=True)
                controle, _ = ControleAcessos.objects.get_or_create(user=funcionario.usuario, defaults={'status': True})
                controle.acessos.set(grupo.acessos.filter(status=True))
        return JsonResponse({'success': True, 'message': 'Funcionário atualizado com sucesso!'})
        
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'}, status=404)
    except GroupsAcessos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Grupo de permissões não encontrado ou inativo'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar funcionário: {str(e)}'}, status=500)

@login_required
@controle_acess('SS18')
@require_http_methods(["GET"])
def api_get_documentos_funcionario(request, funcionario_id):
    """API GET para listar documentos de um funcionário"""
    try:
        funcionario = Funcionario.objects.get(id=funcionario_id)
        documentos = Arquivos.objects.filter(funcionario=funcionario, status=True).order_by('-data_criacao')
        documentos_data = []
        for doc in documentos:
            documentos_data.append({
                'id': doc.id,
                'titulo': doc.titulo,
                'arquivo_url': doc.arquivo.url if doc.arquivo else '',
                'arquivo_nome': doc.arquivo.name.split('/')[-1] if doc.arquivo else '',
                'data_criacao': doc.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'status': doc.status
            })
        return JsonResponse({'success': True, 'data': documentos_data})
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar documentos: {str(e)}'}, status=500)

@login_required
@controle_acess('SS18')
@require_http_methods(["POST"])
def api_post_adicionar_documento(request):
    """API POST para adicionar novo documento ao funcionário"""
    try:
        funcionario_id = request.POST.get('funcionario_id', '').strip()
        titulo = request.POST.get('titulo', '').strip()
        arquivo = request.FILES.get('arquivo', None)
        if not funcionario_id:
            return JsonResponse({'success': False, 'message': 'ID do funcionário é obrigatório'})
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título do documento é obrigatório'})
        if not arquivo:
            return JsonResponse({'success': False, 'message': 'Arquivo é obrigatório'})
        funcionario = Funcionario.objects.get(id=funcionario_id)
        documento = Arquivos.objects.create(
            funcionario=funcionario,
            titulo=titulo,
            arquivo=arquivo,
            status=True
        )
        return JsonResponse({
            'success': True,
            'message': 'Documento adicionado com sucesso!',
            'data': {
                'id': documento.id,
                'titulo': documento.titulo,
                'arquivo_url': documento.arquivo.url if documento.arquivo else '',
                'arquivo_nome': documento.arquivo.name.split('/')[-1] if documento.arquivo else '',
                'data_criacao': documento.data_criacao.strftime('%d/%m/%Y %H:%M')
            }
        })
    except Funcionario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Funcionário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao adicionar documento: {str(e)}'}, status=500)

@login_required
@controle_acess('SS18')
@require_http_methods(["POST"])
def api_post_deletar_documento(request, documento_id):
    """API POST para deletar documento do funcionário"""
    try:
        documento = Arquivos.objects.get(id=documento_id)
        if documento.arquivo and os.path.isfile(documento.arquivo.path):
            os.remove(documento.arquivo.path)
        documento.delete()
        return JsonResponse({'success': True, 'message': 'Documento removido com sucesso!'})
    except Arquivos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Documento não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar documento: {str(e)}'}, status=500)

@login_required
@controle_acess('SS18')
@require_http_methods(["POST"])
def api_toggle_status(request, funcionario_id):
    """API POST para alternar status do funcionário (ativo/inativo)"""
    try:
        funcionario = get_object_or_404(Funcionario, id=funcionario_id)
        funcionario.status = not funcionario.status
        funcionario.save(update_fields=['status'])

        status_text = 'ativado' if funcionario.status else 'desativado'
        return JsonResponse({
            'success': True,
            'message': f'Funcionário {status_text} com sucesso!',
            'status': funcionario.status,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao alternar status: {str(e)}'}, status=500)
