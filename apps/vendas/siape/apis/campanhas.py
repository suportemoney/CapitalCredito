"""
APIs para gerenciar campanhas e importação CSV
Otimizado para arquivos grandes com processamento em chunks e SSE detalhado
"""
import csv
import io
import re
import json
import gc
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from apps.seguranca.permissoes.decorators import controle_acess
from apps.vendas.siape.models import (
    Campanha, Cliente, Matricula, Margens, Contrato
)

# Configurações de processamento
BATCH_SIZE = 500  # Linhas por batch
MAX_LINHAS = 250000  # Máximo de linhas permitidas
MAX_ERROS_BATCH = 100  # Máximo de erros por batch antes de abortar

# Colunas obrigatórias no CSV
COLUNAS_OBRIGATORIAS = ['nome', 'cpf', 'matricula']

@login_required
@controle_acess('SS25')
@require_http_methods(["GET"])
def api_listar_campanhas(request):
    """API GET para listar campanhas"""
    try:
        campanhas = Campanha.objects.all().order_by('-data_criacao')
        data = [{
            'id': camp.id,
            'titulo': camp.titulo,
            'status': camp.status,
            'data_criacao': camp.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'total_matriculas': camp.matriculas.count(),
            'total_contratos': camp.contratos.count(),
        } for camp in campanhas]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao listar campanhas: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["POST"])
def api_criar_campanha(request):
    """API POST para criar campanha"""
    try:
        titulo = request.POST.get('titulo', '').strip()
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        campanha = Campanha.objects.create(titulo=titulo, status=True)
        return JsonResponse({
            'success': True,
            'message': 'Campanha criada com sucesso!',
            'data': {
                'id': campanha.id,
                'titulo': campanha.titulo,
                'status': campanha.status,
                'data_criacao': campanha.data_criacao.strftime('%d/%m/%Y %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar campanha: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["GET", "POST"])
def api_editar_campanha(request, campanha_id):
    """API para editar campanha"""
    try:
        campanha = Campanha.objects.get(id=campanha_id)
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'id': campanha.id,
                    'titulo': campanha.titulo,
                    'status': campanha.status,
                }
            })
        titulo = request.POST.get('titulo', '').strip()
        status = request.POST.get('status', 'on') == 'on'
        if not titulo:
            return JsonResponse({'success': False, 'message': 'Título é obrigatório'})
        campanha.titulo = titulo
        campanha.status = status
        campanha.save()
        return JsonResponse({'success': True, 'message': 'Campanha atualizada com sucesso!'})
    except Campanha.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Campanha não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao editar campanha: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["POST"])
def api_deletar_campanha(request, campanha_id):
    """API POST para deletar campanha"""
    try:
        campanha = Campanha.objects.get(id=campanha_id)
        titulo = campanha.titulo
        campanha.delete()
        return JsonResponse({'success': True, 'message': f'Campanha "{titulo}" deletada com sucesso!'})
    except Campanha.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Campanha não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao deletar campanha: {str(e)}'}, status=500)

@login_required
@controle_acess('SS25')
@require_http_methods(["GET"])
def api_download_modelo(request):
    """API GET para download do modelo CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_clientes.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'tipo_base', 'nome', 'cpf', 'uf', 'situacao_funcional', 'matricula_instituidor',
        'matricula', 'orgao', 'upag', 'rubrica', 'contrato', 'tipo_contrato', 'nome_banco',
        'valor_parcela', 'parcelas_restantes', 'base_calculo', 'bruta_5', 'util_5', 'saldo_5',
        'bruta_5b', 'util_5b', 'saldo_5b', 'bruta_35', 'util_35', 'saldo_35', 'rjur'
    ])
    writer.writerow([
        'PENSIONISTA', 'JOÃO DA SILVA', '12345678901', 'SP', 'ATIVO', '123456',
        '654321', 'ÓRGÃO TESTE', 'UPAG001', 'RUB001', 'CONT001', 'CONSIGNADO', 'BANCO TESTE',
        '500.00', '10', '10000.00', '500.00', '450.00', '50.00',
        '500.00', '450.00', '50.00', '3500.00', '3150.00', '350.00', '100.00'
    ])
    return response

def limpar_cpf(cpf):
    """Remove caracteres não numéricos do CPF e normaliza com zeros à esquerda"""
    if not cpf:
        return ''
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    if len(cpf_limpo) < 11:
        cpf_limpo = cpf_limpo.zfill(11)
    if len(cpf_limpo) > 11:
        cpf_limpo = cpf_limpo[:11]
    return cpf_limpo

def converter_decimal(valor):
    """Converte string para Decimal, retorna None se inválido"""
    if not valor or str(valor).strip() == '':
        return None
    try:
        valor_limpo = str(valor).replace(',', '.').strip()
        return Decimal(valor_limpo)
    except (InvalidOperation, ValueError):
        return None

def converter_inteiro(valor):
    """Converte string para inteiro, retorna None se inválido"""
    if not valor or str(valor).strip() == '':
        return None
    try:
        return int(float(str(valor).replace(',', '.')))
    except (ValueError, TypeError):
        return None

def criar_evento_sse(dados):
    """Cria um evento SSE formatado corretamente"""
    json_str = json.dumps(dados, ensure_ascii=False)
    return f"data: {json_str}\n\n"

def extrair_dados_linha(linha):
    """Extrai e normaliza dados de uma linha do CSV"""
    linha_norm = {k.strip().lower(): v for k, v in linha.items() if k}
    return {
        'tipo_base': (linha_norm.get('tipo_base', '') or '').strip().upper(),
        'nome': (linha_norm.get('nome', '') or '').strip(),
        'cpf': limpar_cpf(linha_norm.get('cpf', '')),
        'uf': (linha_norm.get('uf', '') or '').strip().upper(),
        'situacao_funcional': (linha_norm.get('situacao_funcional', '') or '').strip(),
        'matricula_instituidor': (linha_norm.get('matricula_instituidor', '') or '').strip(),
        'matricula': (linha_norm.get('matricula', '') or '').strip(),
        'orgao': (linha_norm.get('orgao', '') or '').strip(),
        'upag': (linha_norm.get('upag', '') or '').strip(),
        'rubrica': (linha_norm.get('rubrica', '') or '').strip(),
        'contrato': (linha_norm.get('contrato', '') or '').strip(),
        'tipo_contrato': (linha_norm.get('tipo_contrato', '') or '').strip(),
        'nome_banco': (linha_norm.get('nome_banco', '') or '').strip(),
        'valor_parcela': converter_decimal(linha_norm.get('valor_parcela', '')),
        'parcelas_restantes': converter_inteiro(linha_norm.get('parcelas_restantes', '')),
        'base_calculo': converter_decimal(linha_norm.get('base_calculo', '')),
        'bruta_5': converter_decimal(linha_norm.get('bruta_5', '')),
        'util_5': converter_decimal(linha_norm.get('util_5', '')),
        'saldo_5': converter_decimal(linha_norm.get('saldo_5', '')),
        'bruta_5b': converter_decimal(linha_norm.get('bruta_5b', '')),
        'util_5b': converter_decimal(linha_norm.get('util_5b', '')),
        'saldo_5b': converter_decimal(linha_norm.get('saldo_5b', '')),
        'bruta_35': converter_decimal(linha_norm.get('bruta_35', '')),
        'util_35': converter_decimal(linha_norm.get('util_35', '')),
        'saldo_35': converter_decimal(linha_norm.get('saldo_35', '')),
        'rjur': (linha_norm.get('rjur', '') or '').strip().upper(),
    }

def processar_batch_otimizado(batch_dados, campanha, resultados):
    """
    Processa um batch de dados usando operações otimizadas de banco.
    Usa prefetch de CPFs existentes e bulk operations quando possível.
    """
    if not batch_dados:
        return
    # Coletar todos os CPFs do batch para prefetch
    cpfs_batch = [d['cpf'] for d in batch_dados if d['cpf'] and len(d['cpf']) == 11]
    clientes_existentes = {c.cpf: c for c in Cliente.objects.filter(cpf__in=cpfs_batch)}
    # Coletar todas as matrículas para prefetch
    matriculas_keys = [(d['cpf'], d['matricula'].upper()) for d in batch_dados 
                       if d['cpf'] and d['matricula']]
    matriculas_existentes = {}
    if matriculas_keys:
        for mat in Matricula.objects.filter(
            cliente__cpf__in=[k[0] for k in matriculas_keys]
        ).select_related('cliente'):
            key = (mat.cliente.cpf, mat.matricula)
            matriculas_existentes[key] = mat
    # Coletar contratos existentes
    contratos_keys = []
    for d in batch_dados:
        if d['cpf'] and d['matricula'] and d['contrato']:
            contratos_keys.append((d['cpf'], d['matricula'].upper(), d['contrato'].upper()))
    contratos_existentes = {}
    if contratos_keys:
        for cont in Contrato.objects.filter(
            matricula__cliente__cpf__in=[k[0] for k in contratos_keys]
        ).select_related('matricula__cliente'):
            key = (cont.matricula.cliente.cpf, cont.matricula.matricula, cont.contrato)
            contratos_existentes[key] = cont
    # Processar cada linha do batch
    clientes_novos = []
    clientes_atualizar = []
    matriculas_novas = []
    matriculas_atualizar = []
    margens_novas = []
    margens_atualizar = []
    contratos_novos = []
    contratos_atualizar = []
    for idx, dados in enumerate(batch_dados):
        try:
            cpf = dados['cpf']
            nome = dados['nome']
            matricula_num = dados['matricula']
            # Validar dados obrigatórios
            if not nome:
                resultados['erros'].append(f"Batch linha {idx+1}: Nome é obrigatório")
                resultados['falhas'] += 1
                continue
            if not cpf or len(cpf) != 11:
                resultados['erros'].append(f"Batch linha {idx+1}: CPF inválido")
                resultados['falhas'] += 1
                continue
            if not matricula_num:
                resultados['erros'].append(f"Batch linha {idx+1}: Matrícula é obrigatória")
                resultados['falhas'] += 1
                continue
            # Processar Cliente
            if cpf in clientes_existentes:
                cliente = clientes_existentes[cpf]
                # Só atualiza se já tem PK (já está salvo no banco)
                if cliente.pk and dados['uf']:
                    cliente.uf = dados['uf']
                    if cliente not in clientes_atualizar:
                        clientes_atualizar.append(cliente)
                resultados['clientes_atualizados'] += 1
            else:
                cliente = Cliente(
                    cpf=cpf,
                    tipo_base=dados['tipo_base'] if dados['tipo_base'] in ['PENSIONISTA', 'SERVIDOR'] else None,
                    nome=nome.upper(),
                    uf=dados['uf'],
                    situacao_funcional=dados['situacao_funcional'],
                    status=True
                )
                clientes_novos.append(cliente)
                clientes_existentes[cpf] = cliente
                resultados['clientes_novos'] += 1
            # Processar Matrícula
            mat_key = (cpf, matricula_num.upper())
            if mat_key in matriculas_existentes:
                mat_obj = matriculas_existentes[mat_key]
                # Só atualiza se já tem PK (já está salvo no banco)
                if mat_obj.pk:
                    atualizado = False
                    if dados['base_calculo'] and mat_obj.base_calculo != dados['base_calculo']:
                        mat_obj.base_calculo = dados['base_calculo']
                        atualizado = True
                    if dados['orgao'] and mat_obj.orgao != dados['orgao'].upper():
                        mat_obj.orgao = dados['orgao'].upper()
                        atualizado = True
                    if dados['upag'] and mat_obj.upag != dados['upag'].upper():
                        mat_obj.upag = dados['upag'].upper()
                        atualizado = True
                    if dados['rubrica'] and mat_obj.rubrica != dados['rubrica'].upper():
                        mat_obj.rubrica = dados['rubrica'].upper()
                        atualizado = True
                    if dados['rjur'] and mat_obj.rjur != dados['rjur']:
                        mat_obj.rjur = dados['rjur']
                        atualizado = True
                    if atualizado and mat_obj not in matriculas_atualizar:
                        matriculas_atualizar.append(mat_obj)
                resultados['matriculas_atualizadas'] += 1
            else:
                mat_obj = Matricula(
                    cliente=clientes_existentes[cpf],
                    campanha=campanha,
                    matricula=matricula_num.upper(),
                    matricula_instituidor=dados['matricula_instituidor'].upper() if dados['matricula_instituidor'] else None,
                    base_calculo=dados['base_calculo'],
                    orgao=dados['orgao'].upper() if dados['orgao'] else None,
                    upag=dados['upag'].upper() if dados['upag'] else None,
                    rubrica=dados['rubrica'].upper() if dados['rubrica'] else None,
                    rjur=dados['rjur'] if dados['rjur'] else None,
                    status=True
                )
                matriculas_novas.append(mat_obj)
                matriculas_existentes[mat_key] = mat_obj
                resultados['matriculas_novas'] += 1
            # Processar Contrato se existir
            if dados['contrato']:
                cont_key = (cpf, matricula_num.upper(), dados['contrato'].upper())
                if cont_key in contratos_existentes:
                    cont_obj = contratos_existentes[cont_key]
                    # Só atualiza se já tem PK (já está salvo no banco)
                    if cont_obj.pk:
                        atualizado = False
                        if dados['nome_banco'] and cont_obj.banco != dados['nome_banco'].upper():
                            cont_obj.banco = dados['nome_banco'].upper()
                            atualizado = True
                        if dados['valor_parcela'] and cont_obj.valor_parcela != dados['valor_parcela']:
                            cont_obj.valor_parcela = dados['valor_parcela']
                            atualizado = True
                        if dados['parcelas_restantes'] and cont_obj.parcelas_restantes != dados['parcelas_restantes']:
                            cont_obj.parcelas_restantes = dados['parcelas_restantes']
                            atualizado = True
                        if atualizado and cont_obj not in contratos_atualizar:
                            contratos_atualizar.append(cont_obj)
                    resultados['contratos_atualizados'] += 1
                else:
                    cont_obj = Contrato(
                        matricula=matriculas_existentes[mat_key],
                        campanha=campanha,
                        contrato=dados['contrato'].upper(),
                        tipo_contrato=dados['tipo_contrato'].upper() if dados['tipo_contrato'] else None,
                        banco=dados['nome_banco'].upper() if dados['nome_banco'] else None,
                        valor_parcela=dados['valor_parcela'],
                        parcelas_restantes=dados['parcelas_restantes']
                    )
                    contratos_novos.append(cont_obj)
                    contratos_existentes[cont_key] = cont_obj
                    resultados['contratos_novos'] += 1
            resultados['sucesso'] += 1
        except Exception as e:
            resultados['erros'].append(f"Batch linha {idx+1}: {str(e)}")
            resultados['falhas'] += 1
    # Executar bulk operations dentro de uma transação
    with transaction.atomic():
        # Salvar clientes novos primeiro
        if clientes_novos:
            Cliente.objects.bulk_create(clientes_novos, ignore_conflicts=True)
            # Recarregar clientes para obter IDs
            cpfs_novos = [c.cpf for c in clientes_novos]
            for c in Cliente.objects.filter(cpf__in=cpfs_novos):
                clientes_existentes[c.cpf] = c
        # Atualizar clientes existentes
        if clientes_atualizar:
            Cliente.objects.bulk_update(clientes_atualizar, ['uf'])
        # Atualizar referências de cliente nas matrículas novas
        for mat in matriculas_novas:
            if hasattr(mat, 'cliente') and mat.cliente:
                mat.cliente = clientes_existentes.get(mat.cliente.cpf, mat.cliente)
        # Salvar matrículas novas
        if matriculas_novas:
            Matricula.objects.bulk_create(matriculas_novas, ignore_conflicts=True)
            # Recarregar matrículas para obter IDs
            for mat in Matricula.objects.filter(
                cliente__cpf__in=[m.cliente.cpf for m in matriculas_novas if hasattr(m, 'cliente') and m.cliente]
            ).select_related('cliente'):
                key = (mat.cliente.cpf, mat.matricula)
                matriculas_existentes[key] = mat
        # Atualizar matrículas existentes
        if matriculas_atualizar:
            Matricula.objects.bulk_update(
                matriculas_atualizar, 
                ['base_calculo', 'orgao', 'upag', 'rubrica', 'rjur']
            )
        # Criar/atualizar margens para matrículas
        for dados in batch_dados:
            cpf = dados['cpf']
            mat_num = dados['matricula']
            if not cpf or not mat_num:
                continue
            mat_key = (cpf, mat_num.upper())
            mat_obj = matriculas_existentes.get(mat_key)
            if not mat_obj or not mat_obj.pk:
                continue
            try:
                margens, criada = Margens.objects.get_or_create(
                    matricula=mat_obj,
                    defaults={
                        'bruta_5': dados['bruta_5'] or Decimal('0'),
                        'util_5': dados['util_5'] or Decimal('0'),
                        'saldo_5': dados['saldo_5'] or Decimal('0'),
                        'bruta_5b': dados['bruta_5b'] or Decimal('0'),
                        'util_5b': dados['util_5b'] or Decimal('0'),
                        'saldo_5b': dados['saldo_5b'] or Decimal('0'),
                        'bruta_35': dados['bruta_35'] or Decimal('0'),
                        'util_35': dados['util_35'] or Decimal('0'),
                        'saldo_35': dados['saldo_35'] or Decimal('0'),
                    }
                )
                if not criada:
                    atualizado = False
                    if dados['bruta_5'] is not None:
                        margens.bruta_5 = dados['bruta_5']
                        atualizado = True
                    if dados['util_5'] is not None:
                        margens.util_5 = dados['util_5']
                        atualizado = True
                    if dados['saldo_5'] is not None:
                        margens.saldo_5 = dados['saldo_5']
                        atualizado = True
                    if dados['bruta_5b'] is not None:
                        margens.bruta_5b = dados['bruta_5b']
                        atualizado = True
                    if dados['util_5b'] is not None:
                        margens.util_5b = dados['util_5b']
                        atualizado = True
                    if dados['saldo_5b'] is not None:
                        margens.saldo_5b = dados['saldo_5b']
                        atualizado = True
                    if dados['bruta_35'] is not None:
                        margens.bruta_35 = dados['bruta_35']
                        atualizado = True
                    if dados['util_35'] is not None:
                        margens.util_35 = dados['util_35']
                        atualizado = True
                    if dados['saldo_35'] is not None:
                        margens.saldo_35 = dados['saldo_35']
                        atualizado = True
                    if atualizado:
                        margens.save()
            except Exception:
                pass
        # Atualizar referências de matrícula nos contratos novos
        for cont in contratos_novos:
            if hasattr(cont, 'matricula') and cont.matricula:
                mat_key = (cont.matricula.cliente.cpf, cont.matricula.matricula)
                cont.matricula = matriculas_existentes.get(mat_key, cont.matricula)
        # Salvar contratos novos
        if contratos_novos:
            Contrato.objects.bulk_create(contratos_novos, ignore_conflicts=True)
        # Atualizar contratos existentes
        if contratos_atualizar:
            Contrato.objects.bulk_update(
                contratos_atualizar, 
                ['banco', 'valor_parcela', 'parcelas_restantes']
            )

@login_required
@controle_acess('SS25')
@require_http_methods(["POST"])
def api_importar_csv(request):
    """
    API POST para importar CSV usando SSE (Server-Sent Events)
    Otimizada com processamento em chunks e etapas detalhadas
    """
    # Validação inicial
    if 'arquivo_csv' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'Arquivo CSV não encontrado'}, status=400)
    campanha_id = request.POST.get('campanha_id', '').strip()
    if not campanha_id:
        return JsonResponse({'success': False, 'message': 'Campanha é obrigatória'}, status=400)
    try:
        campanha = Campanha.objects.get(id=campanha_id)
    except Campanha.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Campanha não encontrada'}, status=404)
    arquivo = request.FILES['arquivo_csv']
    if not arquivo.name.lower().endswith('.csv'):
        return JsonResponse({'success': False, 'message': 'Arquivo deve ser CSV'}, status=400)
    # Verificar tamanho do arquivo (limite de 50MB)
    if arquivo.size > 50 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': 'Arquivo muito grande! Máximo de 50MB permitido.'}, status=400)
    def gerar_eventos():
        """Gerador de eventos SSE com etapas detalhadas"""
        resultados = {
            'sucesso': 0,
            'falhas': 0,
            'clientes_novos': 0,
            'clientes_atualizados': 0,
            'matriculas_novas': 0,
            'matriculas_atualizadas': 0,
            'contratos_novos': 0,
            'contratos_atualizados': 0,
            'erros': [],
        }
        inicio = timezone.now()
        # ETAPA 1: ENVIO (5%)
        yield criar_evento_sse({
            'etapa': 'envio',
            'progresso': 5,
            'mensagem': f'Arquivo "{arquivo.name}" recebido ({arquivo.size / 1024:.1f} KB)'
        })
        try:
            # ETAPA 2: LEITURA (10%)
            yield criar_evento_sse({
                'etapa': 'leitura',
                'progresso': 8,
                'mensagem': 'Lendo arquivo e detectando encoding...'
            })
            arquivo.seek(0)
            # Tentar diferentes encodings
            conteudo = None
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            for enc in encodings:
                try:
                    arquivo.seek(0)
                    conteudo = arquivo.read().decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if conteudo is None:
                yield criar_evento_sse({
                    'etapa': 'erro',
                    'progresso': 0,
                    'mensagem': 'Erro: Não foi possível decodificar o arquivo. Verifique o encoding.'
                })
                return
            # Contar linhas
            linhas_conteudo = conteudo.strip().split('\n')
            total_linhas = len(linhas_conteudo) - 1  # Descontar header
            yield criar_evento_sse({
                'etapa': 'leitura',
                'progresso': 10,
                'mensagem': f'Arquivo lido com sucesso. {total_linhas} linhas detectadas.',
                'total_linhas': total_linhas
            })
            # Validar quantidade de linhas
            if total_linhas > MAX_LINHAS:
                yield criar_evento_sse({
                    'etapa': 'erro',
                    'progresso': 0,
                    'mensagem': f'Arquivo muito grande! Máximo de {MAX_LINHAS:,} linhas permitido. Seu arquivo tem {total_linhas:,} linhas.'
                })
                return
            if total_linhas == 0:
                yield criar_evento_sse({
                    'etapa': 'erro',
                    'progresso': 0,
                    'mensagem': 'Arquivo vazio ou apenas com cabeçalho.'
                })
                return
            # ETAPA 3: VALIDAÇÃO (15%)
            yield criar_evento_sse({
                'etapa': 'validacao',
                'progresso': 12,
                'mensagem': 'Validando estrutura do arquivo...'
            })
            # Detectar delimitador
            primeira_linha = linhas_conteudo[0] if linhas_conteudo else ''
            delimitador = ';' if ';' in primeira_linha else ','
            # Verificar colunas obrigatórias
            colunas = [c.strip().lower() for c in primeira_linha.split(delimitador)]
            colunas_faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in colunas]
            if colunas_faltantes:
                yield criar_evento_sse({
                    'etapa': 'erro',
                    'progresso': 0,
                    'mensagem': f'Colunas obrigatórias faltando: {", ".join(colunas_faltantes)}'
                })
                return
            yield criar_evento_sse({
                'etapa': 'validacao',
                'progresso': 15,
                'mensagem': f'Estrutura válida. Delimitador: "{delimitador}". Iniciando processamento...'
            })
            # ETAPA 4: PROCESSAMENTO (15-85%)
            leitor = csv.DictReader(io.StringIO(conteudo), delimiter=delimitador)
            batch_dados = []
            linha_atual = 0
            total_batches = (total_linhas // BATCH_SIZE) + 1
            batch_atual = 0
            for linha in leitor:
                linha_atual += 1
                dados = extrair_dados_linha(linha)
                batch_dados.append(dados)
                # Processar batch quando atingir o tamanho
                if len(batch_dados) >= BATCH_SIZE:
                    batch_atual += 1
                    # Calcular progresso (15% a 85% = 70% do total)
                    progresso_batch = 15 + (70 * batch_atual / total_batches)
                    yield criar_evento_sse({
                        'etapa': 'processamento',
                        'progresso': round(progresso_batch, 1),
                        'mensagem': f'Processando batch {batch_atual}/{total_batches}...',
                        'linha_atual': linha_atual,
                        'total_linhas': total_linhas,
                        'batch_atual': batch_atual,
                        'total_batches': total_batches
                    })
                    # ETAPA 5: SALVAMENTO (durante processamento)
                    yield criar_evento_sse({
                        'etapa': 'salvamento',
                        'progresso': round(progresso_batch, 1),
                        'mensagem': f'Salvando batch {batch_atual} no banco de dados...'
                    })
                    processar_batch_otimizado(batch_dados, campanha, resultados)
                    # Verificar limite de erros
                    if len(resultados['erros']) > MAX_ERROS_BATCH * batch_atual:
                        yield criar_evento_sse({
                            'etapa': 'erro',
                            'progresso': round(progresso_batch, 1),
                            'mensagem': f'Muitos erros encontrados ({len(resultados["erros"])}). Abortando importação.'
                        })
                        return
                    # Limpar batch e liberar memória
                    batch_dados = []
                    gc.collect()
            # Processar último batch se houver dados restantes
            if batch_dados:
                batch_atual += 1
                yield criar_evento_sse({
                    'etapa': 'processamento',
                    'progresso': 82,
                    'mensagem': f'Processando último batch ({len(batch_dados)} registros)...',
                    'linha_atual': linha_atual,
                    'total_linhas': total_linhas
                })
                yield criar_evento_sse({
                    'etapa': 'salvamento',
                    'progresso': 85,
                    'mensagem': 'Salvando últimos registros no banco de dados...'
                })
                processar_batch_otimizado(batch_dados, campanha, resultados)
                batch_dados = []
                gc.collect()
            # ETAPA 6: FINALIZAÇÃO (100%)
            fim = timezone.now()
            tempo_decorrido = fim - inicio
            horas, resto = divmod(tempo_decorrido.total_seconds(), 3600)
            minutos, segundos = divmod(resto, 60)
            tempo_formatado = f"{int(horas):02d}:{int(minutos):02d}:{int(segundos):02d}"
            yield criar_evento_sse({
                'etapa': 'finalizacao',
                'progresso': 100,
                'mensagem': 'Importação finalizada com sucesso!',
                'resultado': {
                    'sucesso': resultados['sucesso'],
                    'falhas': resultados['falhas'],
                    'clientes_novos': resultados['clientes_novos'],
                    'clientes_atualizados': resultados['clientes_atualizados'],
                    'matriculas_novas': resultados['matriculas_novas'],
                    'matriculas_atualizadas': resultados['matriculas_atualizadas'],
                    'contratos_novos': resultados['contratos_novos'],
                    'contratos_atualizados': resultados['contratos_atualizados'],
                    'total_erros': len(resultados['erros']),
                    'erros': resultados['erros'][:50],
                    'tempo_decorrido': tempo_formatado,
                    'data_inicio': inicio.strftime('%d/%m/%Y %H:%M:%S'),
                    'data_fim': fim.strftime('%d/%m/%Y %H:%M:%S'),
                }
            })
        except Exception as e:
            yield criar_evento_sse({
                'etapa': 'erro',
                'progresso': 0,
                'mensagem': f'Erro inesperado: {str(e)}'
            })
    response = StreamingHttpResponse(gerar_eventos(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
