from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
# from apps.seguranca.permissoes.decorators import controle_acess  # Permissão será configurada depois
import csv
import io

from .models import ContratoOperacional

@login_required
# @controle_acess('SS_NOVO_CONTRATO')  # Permissão para VENDEDOR_CONSULTOR
def render_novo_contrato(request):
    """Página para criar um novo contrato."""
    return render(request, 'contratos/novo_contrato.html')

@login_required
# @controle_acess('SS_EDITAR_CONTRATO')  # Permissão para VENDEDOR_CONSULTOR
def render_editar_contrato(request, contrato_id):
    """Página para editar um contrato existente (incompleto)."""
    contrato = get_object_or_404(ContratoOperacional, id=contrato_id)
    
    # Verificar permissão: apenas o vendedor do contrato ou operacional pode editar
    if not request.user.is_superuser and contrato.vendedor != request.user:
        if not (hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario == 'OPERACIONAL'):
            raise Http404("Contrato não encontrado")
    
    return render(request, 'contratos/editar_contrato.html', {'contrato_id': contrato_id})

@login_required
# @controle_acess('SS_ACOMPANHAMENTO_CRM')  # Permissão para VENDEDOR_CONSULTOR
def render_acompanhamento_crm(request):
    """Página de acompanhamento de contratos em modo CRM (Kanban) para Vendedor/Consultor."""
    return render(request, 'contratos/acompanhamento_crm.html')

@login_required
# @controle_acess('SS_ACOMPANHAMENTO_TABELA')  # Permissão para OPERACIONAL
def render_acompanhamento_tabela(request):
    """Página de acompanhamento de contratos em modo tabela para Operacional."""
    return render(request, 'contratos/acompanhamento_tabela.html')

@login_required
# @controle_acess('SS_GERENCIAR_BANCOS')  # Permissão para OPERACIONAL e ADMIN
def render_gerenciar_bancos(request):
    """Página para gerenciar bancos, convênios e operações."""
    return render(request, 'contratos/gerenciar_bancos.html')

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão para ADMIN
def render_administrativo(request):
    """Página administrativa para CRUD de bancos, convênios, operações e schemas."""
    return render(request, 'contratos/administrativo.html')

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão para ADMIN
def download_modelo_schema_csv(request):
    """Download do modelo CSV com exemplos de todos os tipos de campos"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_schema_campos.csv"'
    
    # Forçar BOM UTF-8 para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # Cabeçalho - INCLUI COLUNA PAGINA
    writer.writerow(['Category', 'Label', 'Type', 'Choices', 'Placeholder', 'Required', 'Ordem', 'Pagina'])
    
    # Exemplos de cada tipo de campo
    # IMPORTANTE: 
    # - MULTIINPUT usa ponto e vírgula (;) no campo Choices para separar os sub-campos
    # - SELECT e MULTISELECTOR usam vírgula (,) no campo Choices para separar as opções
    # - FILE e MULTIFILE não precisam de Choices (campo vazio)
    # - PAGINA: número da página onde o campo aparece (mínimo 1)
    exemplos = [
        # PÁGINA 1 - Dados Pessoais e Contato
        # TEXT - Texto simples
        ['dados_pessoais', 'nome_completo', 'TEXT', '', 'Digite o nome completo', '1', '1', '1'],
        ['dados_pessoais', 'cpf', 'TEXT', '', '000.000.000-00', '1', '2', '1'],
        ['dados_pessoais', 'idade', 'NUMBER', '', 'Ex: 35', '0', '3', '1'],
        ['dados_pessoais', 'data_nascimento', 'DATE', '', 'dd/mm/aaaa', '1', '4', '1'],
        ['dados_pessoais', 'estado_civil', 'SELECT', 'solteiro,casado,divorciado,viuvo,uniao_estavel', 'Selecione o estado civil', '1', '5', '1'],
        ['dados_pessoais', 'sexo', 'SELECT', 'masculino,feminino,outro', 'Selecione...', '1', '6', '1'],
        # Contato
        ['contato', 'telefone', 'TEL', '', '(00) 00000-0000', '1', '7', '1'],
        ['contato', 'telefone_residencial', 'TEL', '', '(00) 0000-0000', '0', '8', '1'],
        ['contato', 'email', 'EMAIL', '', 'exemplo@email.com', '1', '9', '1'],
        ['contato', 'email_secundario', 'EMAIL', '', 'exemplo2@email.com', '0', '10', '1'],
        
        # PÁGINA 2 - Endereço e Dados Bancários
        ['endereco', 'logradouro', 'TEXT', '', 'Rua, Avenida, etc', '0', '1', '2'],
        ['endereco', 'numero', 'TEXT', '', 'Número', '0', '2', '2'],
        ['endereco', 'complemento', 'TEXT', '', 'Apto, Bloco, etc', '0', '3', '2'],
        ['endereco', 'bairro', 'TEXT', '', 'Bairro', '0', '4', '2'],
        ['endereco', 'cidade', 'TEXT', '', 'Cidade', '0', '5', '2'],
        ['endereco', 'estado', 'TEXT', '', 'UF', '0', '6', '2'],
        ['endereco', 'cep', 'TEXT', '', '00000-000', '0', '7', '2'],
        ['bancario', 'tipo_conta', 'SELECT', 'conta_corrente,conta_poupanca,conta_salario', 'Selecione o tipo de conta', '0', '8', '2'],
        ['bancario', 'banco', 'TEXT', '', 'Nome do banco', '0', '9', '2'],
        ['bancario', 'agencia', 'TEXT', '', 'Agência', '0', '10', '2'],
        ['bancario', 'conta', 'TEXT', '', 'Conta', '0', '11', '2'],
        
        # PÁGINA 3 - Documentos
        ['documentos', 'rg_anexo', 'FILE', '', 'Selecione o arquivo do RG', '1', '1', '3'],
        ['documentos', 'comprovante_renda_anexo', 'FILE', '', 'Selecione o comprovante de renda', '0', '2', '3'],
        ['documentos', 'comprovante_residencia', 'FILE', '', 'Selecione o comprovante de residência', '0', '3', '3'],
        ['documentos', 'documentos_complementares', 'MULTIFILE', '', 'Selecione os arquivos complementares', '0', '4', '3'],
        ['dados_pessoais', 'data_emissao_rg', 'DATE', '', 'dd/mm/aaaa', '0', '5', '3'],
        
        # PÁGINA 4 - Dados da Operação
        ['operacao', 'prazo_meses', 'NUMBER', '', 'Ex: 84', '1', '1', '4'],
        ['operacao', 'quantidade_parcelas', 'NUMBER', '', 'Ex: 120', '0', '2', '4'],
        ['operacao', 'valor_operacao', 'DECIMAL', '', '0.00', '1', '3', '4'],
        ['financeiro_pessoal', 'valor_salario', 'DECIMAL', '', '0.00', '0', '4', '4'],
        ['operacao', 'taxa_juros', 'DECIMAL', '', '0.00', '0', '5', '4'],
        ['operacao', 'incluir_seguro', 'CHECKBOX', '', '', '0', '6', '4'],
        ['operacao', 'aceita_termos', 'CHECKBOX', '', '', '1', '7', '4'],
        ['operacao', 'documentos_anexados', 'MULTISELECTOR', 'rg,cpf,comprovante_renda,comprovante_residencia,contrato_atual', 'Selecione o documento', '0', '8', '4'],
        ['operacao', 'tipos_garantia', 'MULTISELECTOR', 'avalista,imovel,veiculo,consignacao', 'Selecione o tipo de garantia', '0', '9', '4'],
        
        # PÁGINA 5 - Portabilidade (exemplo específico)
        ['portabilidade', 'contratos_portabilidade', 'MULTIINPUT', 'banco_origem;numero_contrato;valor_parcela;parcelas_restantes', 'Adicione os contratos a portar', '0', '1', '5'],
        ['dados_pessoais', 'dependentes', 'MULTIINPUT', 'nome_dependente;cpf_dependente;data_nascimento;parentesco', 'Adicione os dependentes', '0', '2', '5'],
        
        # PÁGINA 6 - Observações e Finalização
        ['outras_informacoes', 'observacoes', 'TEXTAREA', '', 'Digite observações adicionais', '0', '1', '6'],
        ['outras_informacoes', 'observacoes_internas', 'TEXTAREA', '', 'Observações apenas para equipe', '0', '2', '6'],
        ['seguranca', 'senha_acesso', 'PASSWORD', '', 'Digite uma senha forte', '0', '3', '6'],
    ]
    
    for exemplo in exemplos:
        writer.writerow(exemplo)
    
    return response

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão para ADMIN
def download_modelo_bancos_csv(request):
    """Download do modelo CSV para importação de bancos em lote"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_bancos.csv"'
    
    # Forçar BOM UTF-8 para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # Cabeçalho
    writer.writerow(['nome', 'codigo'])
    
    # Exemplos
    exemplos = [
        ['BANCO DO BRASIL', '001'],
        ['CAIXA ECONÔMICA FEDERAL', '104'],
        ['BANRISUL', '041'],
        ['SANTANDER', '033'],
        ['ITAU', '341'],
    ]
    
    for exemplo in exemplos:
        writer.writerow(exemplo)
    
    return response

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão para ADMIN
def download_modelo_convenios_csv(request):
    """Download do modelo CSV para importação de convênios em lote"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_convenios.csv"'
    
    # Forçar BOM UTF-8 para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # Cabeçalho
    writer.writerow(['nome', 'codigo'])
    
    # Exemplos
    exemplos = [
        ['INSS', 'INSS'],
        ['SIAPE', 'SIAPE'],
        ['FEDERAL', 'FEDERAL'],
        ['ESTADUAL', 'ESTADUAL'],
        ['MUNICIPAL', 'MUNICIPAL'],
    ]
    
    for exemplo in exemplos:
        writer.writerow(exemplo)
    
    return response

@login_required
# @controle_acess('SS_ADMINISTRATIVO')  # Permissão para ADMIN
def download_modelo_operacoes_csv(request):
    """Download do modelo CSV para importação de operações em lote"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_operacoes.csv"'
    
    # Forçar BOM UTF-8 para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response, delimiter=';')
    
    # Cabeçalho
    writer.writerow(['nome', 'codigo'])
    
    # Exemplos
    exemplos = [
        ['REFINANCIAMENTO', 'REFIN'],
        ['NOVO EMPRESTIMO', 'NOVO'],
        ['PORTABILIDADE', 'PORT'],
        ['MARGEM LIVRE', 'MARGEM'],
        ['CARTÃO BENEFICIO', 'CART'],
    ]
    
    for exemplo in exemplos:
        writer.writerow(exemplo)
    
    return response
