from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json
import random
import string

class TipoUsuario(models.Model):
    """Tipos de usuário do sistema operacional"""
    TIPO_CHOICES = [
        ('OPERACIONAL', 'Operacional'),
        ('VENDEDOR_CONSULTOR', 'Vendedor/Consultor'),
        ('ADMIN', 'Administrador'),
    ]
    
    nome = models.CharField(max_length=50, choices=TIPO_CHOICES, unique=True, verbose_name="Nome")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        super(TipoUsuario, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.get_nome_display()
    
    class Meta:
        verbose_name = "Tipo de Usuário"
        verbose_name_plural = "Tipos de Usuário"
        ordering = ['nome']

class Banco(models.Model):
    """Bancos disponíveis no sistema"""
    nome = models.CharField(max_length=255, verbose_name="Nome do Banco")
    codigo = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        self.codigo = self.codigo.upper() if self.codigo else None
        super(Banco, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"
        ordering = ['nome']

class Convenio(models.Model):
    """Convênios disponíveis (INSS, SIAPE, FEDERAL, etc)"""
    nome = models.CharField(max_length=255, verbose_name="Nome do Convênio")
    codigo = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        self.codigo = self.codigo.upper() if self.codigo else None
        super(Convenio, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Convênio"
        verbose_name_plural = "Convênios"
        ordering = ['nome']

class Operacao(models.Model):
    """Operações/Produtos disponíveis (Refin, Novo Empréstimo, Portabilidade, etc)"""
    nome = models.CharField(max_length=255, verbose_name="Nome da Operação")
    codigo = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        self.codigo = self.codigo.upper() if self.codigo else None
        super(Operacao, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Operação"
        verbose_name_plural = "Operações"
        ordering = ['nome']

class BancoConvenio(models.Model):
    """Associação entre Banco e Convênio"""
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, related_name='convenios_associados', verbose_name="Banco")
    convenio = models.ForeignKey(Convenio, on_delete=models.CASCADE, related_name='bancos_associados', verbose_name="Convênio")
    ativo = models.BooleanField(default=False, verbose_name="Ativo")
    data_ativacao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Ativação")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        if self.ativo and not self.data_ativacao:
            self.data_ativacao = timezone.now()
        elif not self.ativo:
            self.data_ativacao = None
        super(BancoConvenio, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.banco.nome} - {self.convenio.nome}"
    
    class Meta:
        verbose_name = "Associação Banco-Convênio"
        verbose_name_plural = "Associações Banco-Convênio"
        unique_together = [['banco', 'convenio']]
        ordering = ['banco__nome', 'convenio__nome']

class ConvenioOperacao(models.Model):
    """Associação entre Convênio e Operação (Schema)
    
    IMPORTANTE: Pode existir múltiplos schemas para o mesmo Convênio+Operação.
    A ativação é feita por Banco através de BancoConvenioOperacao.
    """
    convenio = models.ForeignKey(Convenio, on_delete=models.CASCADE, related_name='operacoes_associadas', verbose_name="Convênio")
    operacao = models.ForeignKey(Operacao, on_delete=models.CASCADE, related_name='convenios_associados', verbose_name="Operação")
    titulo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Título do Schema", help_text="Título descritivo para este schema")
    # REMOVIDO: campo 'ativo' - a ativação agora é por banco via BancoConvenioOperacao
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def __str__(self):
        titulo_display = self.titulo or f"{self.convenio.nome} - {self.operacao.nome}"
        return titulo_display
    
    class Meta:
        verbose_name = "Schema (Convênio-Operação)"
        verbose_name_plural = "Schemas (Convênio-Operação)"
        # REMOVIDO unique_together para permitir múltiplos schemas por convênio+operação
        ordering = ['convenio__nome', 'operacao__nome', 'titulo']


class BancoConvenioOperacao(models.Model):
    """Ativação de Schema por Banco
    
    Liga um Banco a um Schema específico (ConvenioOperacao).
    Cada Banco só pode ter UM schema ativo por Convênio+Operação.
    
    Exemplo:
    - BANRISUL + INSS + PORTABILIDADE = Schema "INSS - Portabilidade v1" (ativo)
    - BB + INSS + PORTABILIDADE = Schema "INSS - Portabilidade v2" (ativo)
    - BANRISUL + FEDERAL + NOVO = Schema "Federal - Novo" (ativo)
    """
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, related_name='schemas_ativos', verbose_name="Banco")
    convenio_operacao = models.ForeignKey(ConvenioOperacao, on_delete=models.CASCADE, related_name='bancos_ativos', verbose_name="Schema (Convênio+Operação)")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_ativacao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Ativação")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        if self.ativo:
            # Desativar outros schemas do mesmo banco+convenio+operacao
            BancoConvenioOperacao.objects.filter(
                banco=self.banco,
                convenio_operacao__convenio=self.convenio_operacao.convenio,
                convenio_operacao__operacao=self.convenio_operacao.operacao,
                ativo=True
            ).exclude(pk=self.pk).update(ativo=False, data_ativacao=None)
            
            if not self.data_ativacao:
                self.data_ativacao = timezone.now()
        else:
            self.data_ativacao = None
        super(BancoConvenioOperacao, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.banco.nome} - {self.convenio_operacao}"
    
    class Meta:
        verbose_name = "Ativação de Schema por Banco"
        verbose_name_plural = "Ativações de Schema por Banco"
        unique_together = [['banco', 'convenio_operacao']]
        ordering = ['banco__nome', 'convenio_operacao__convenio__nome', 'convenio_operacao__operacao__nome']

class SchemaCampo(models.Model):
    """Campos customizados por Convênio+Operação"""
    TYPE_CHOICES = [
        ('TEXT', 'Texto'),
        ('NUMBER', 'Número Inteiro'),
        ('DECIMAL', 'Número Decimal'),
        ('EMAIL', 'Email'),
        ('TEL', 'Telefone'),
        ('DATE', 'Data'),
        ('TEXTAREA', 'Área de Texto'),
        ('SELECT', 'Seleção Única'),
        ('CHECKBOX', 'Checkbox'),
        ('PASSWORD', 'Senha'),
        ('MULTISELECTOR', 'Seleção Múltipla (Dropdown)'),
        ('MULTIINPUT', 'Múltiplos Inputs'),
        ('FILE', 'Upload de Arquivo Único'),
        ('MULTIFILE', 'Upload de Múltiplos Arquivos'),
    ]
    
    convenio_operacao = models.ForeignKey(ConvenioOperacao, on_delete=models.CASCADE, related_name='campos_schema', verbose_name="Convênio+Operação")
    category = models.CharField(max_length=100, verbose_name="Categoria")
    label = models.CharField(max_length=255, verbose_name="Label")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Tipo")
    choices = models.JSONField(blank=True, null=True, verbose_name="Opções", help_text="Array de strings para SELECT, MULTISELECTOR, FILE e MULTIFILE")
    placeholder = models.CharField(max_length=255, blank=True, null=True, verbose_name="Placeholder")
    required = models.BooleanField(default=False, verbose_name="Obrigatório")
    ordem = models.IntegerField(default=0, verbose_name="Ordem")
    pagina = models.IntegerField(default=1, verbose_name="Página", help_text="Número da página no formulário (mínimo 1)")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        # Não transformar em lowercase, manter como está
        super(SchemaCampo, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.convenio_operacao} - {self.label}"
    
    class Meta:
        verbose_name = "Campo de Schema"
        verbose_name_plural = "Campos de Schema"
        ordering = ['convenio_operacao', 'ordem', 'label']

class TabelaComissao(models.Model):
    """Tabelas de comissão por Banco+Convênio+Operação"""
    banco_convenio = models.ForeignKey(BancoConvenio, on_delete=models.CASCADE, related_name='tabelas_comissao', verbose_name="Banco+Convênio")
    nome_tabela = models.CharField(max_length=255, verbose_name="Nome da Tabela")
    nome_produto = models.CharField(max_length=255, verbose_name="Nome do Produto")
    operacao = models.ForeignKey(Operacao, on_delete=models.CASCADE, related_name='tabelas_comissao', verbose_name="Operação")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.nome_tabela = self.nome_tabela.upper() if self.nome_tabela else None
        self.nome_produto = self.nome_produto.upper() if self.nome_produto else None
        super(TabelaComissao, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.nome_tabela} - {self.nome_produto}"
    
    class Meta:
        verbose_name = "Tabela de Comissão"
        verbose_name_plural = "Tabelas de Comissão"
        ordering = ['banco_convenio', 'nome_tabela']

class RegraComissao(models.Model):
    """Regras e coeficientes de comissão"""
    TIPO_REGRA_CHOICES = [
        ('A_PRAZO', 'A Prazo'),
        ('A_VISTA', 'À Vista'),
        ('VALOR_FIXO', 'Valor Fixo'),
    ]
    
    tabela_comissao = models.ForeignKey(TabelaComissao, on_delete=models.CASCADE, related_name='regras', verbose_name="Tabela de Comissão")
    tipo_regra = models.CharField(max_length=20, choices=TIPO_REGRA_CHOICES, verbose_name="Tipo de Regra")
    prazo = models.IntegerField(blank=True, null=True, verbose_name="Prazo")
    vigencia_inicio = models.DateField(verbose_name="Vigência Início")
    vigencia_fim = models.DateField(blank=True, null=True, verbose_name="Vigência Fim")
    coeficiente = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, verbose_name="Coeficiente")
    outros_recebimentos = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Outros Recebimentos (%)")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    # Campos para A_VISTA
    flat_recebida = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Flat Recebida (%)")
    bonus_recebido = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Bônus Recebido (%)")
    adiantamento_recebido = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Adiantamento Recebido (%)")
    total_recebido = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Total Recebido (%)")
    flat_repassada = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Flat Repassada (%)")
    bonus_repassado = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Bônus Repassado (%)")
    adiantamento_repassado = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Adiantamento Repassado (%)")
    total_repassado = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Total Repassado (%)")
    # Campos para VALOR_FIXO
    valor_recebido = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor Recebido (R$)")
    valor_repassado = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor Repassado (R$)")
    # Regras adicionais
    regras = models.JSONField(blank=True, null=True, verbose_name="Regras", help_text="Lista de regras com nome, valor_min, valor_max, tipo_regra")
    
    def __str__(self):
        return f"{self.tabela_comissao} - {self.get_tipo_regra_display()}"
    
    class Meta:
        verbose_name = "Regra de Comissão"
        verbose_name_plural = "Regras de Comissão"
        ordering = ['tabela_comissao', 'tipo_regra']

class TabulacaoContrato(models.Model):
    """Tabulações para o sistema de esteira de contratos"""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Tabulação")
    ordem = models.IntegerField(verbose_name="Ordem", help_text="Ordem de exibição (menor número aparece primeiro)")
    cor = models.CharField(max_length=7, default='#6c757d', verbose_name="Cor", help_text="Cor em hexadecimal (ex: #6c757d)")
    status = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        super(TabulacaoContrato, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.ordem} - {self.nome}"
    
    class Meta:
        verbose_name = "Tabulação de Contrato"
        verbose_name_plural = "Tabulações de Contrato"
        ordering = ['ordem', 'nome']

def gerar_numero_serie():
    """Gera um número de série único com 12 caracteres (letras maiúsculas e números)"""
    caracteres = string.ascii_uppercase + string.digits  # A-Z + 0-9 (sem ç)
    while True:
        # Formato: XXX-XXXX-XXXX (12 caracteres úteis)
        parte1 = ''.join(random.choices(caracteres, k=3))
        parte2 = ''.join(random.choices(caracteres, k=4))
        parte3 = ''.join(random.choices(caracteres, k=4))
        numero = f"{parte1}-{parte2}-{parte3}"
        
        # Verificar se já existe
        if not ContratoOperacional.objects.filter(numero_serie=numero).exists():
            return numero

class ContratoOperacional(models.Model):
    """Contratos da esteira operacional"""
    numero_serie = models.CharField(max_length=30, unique=True, verbose_name="Número de Série", help_text="Identificador único do contrato (5-30 caracteres)")
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, related_name='contratos', verbose_name="Banco")
    convenio_operacao = models.ForeignKey(ConvenioOperacao, on_delete=models.PROTECT, related_name='contratos', verbose_name="Convênio+Operação")
    vendedor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='contratos_vendedor', verbose_name="Vendedor")
    operador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='contratos_operador', blank=True, null=True, verbose_name="Operador")
    status_tabulacao = models.ForeignKey(TabulacaoContrato, on_delete=models.PROTECT, related_name='contratos', verbose_name="Tabulação")
    dados_contrato = models.JSONField(verbose_name="Dados do Contrato", help_text="Campos comuns + customizados em formato JSON")
    link_formalizacao = models.TextField(blank=True, null=True, verbose_name="Link de Formalização")
    cliente_formalizou = models.BooleanField(default=False, verbose_name="Cliente Formalizou")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    data_formalizacao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Formalização")
    data_liberacao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Liberação")
    data_pagamento = models.DateTimeField(blank=True, null=True, verbose_name="Data de Pagamento")
    # Campos para sistema de páginas/rascunho
    is_rascunho = models.BooleanField(default=True, verbose_name="É Rascunho", help_text="True se o contrato ainda não foi totalmente preenchido")
    pagina_atual = models.IntegerField(default=1, verbose_name="Página Atual", help_text="Página atual do formulário (0 = completo)")
    # Campos para controle de tabulações
    observacoes_incompleto = models.TextField(blank=True, null=True, verbose_name="Observações Incompleto")
    video_cliente = models.FileField(upload_to='contratos/videos/%Y/%m/', blank=True, null=True, verbose_name="Vídeo do Cliente")
    video_tamanho = models.IntegerField(blank=True, null=True, verbose_name="Tamanho do Vídeo (bytes)")
    
    def save(self, *args, **kwargs):
        if not self.numero_serie:
            self.numero_serie = gerar_numero_serie()
        super(ContratoOperacional, self).save(*args, **kwargs)
    
    def __str__(self):
        cliente_nome = self.dados_contrato.get('dados_pessoais', {}).get('nome', 'N/A') if isinstance(self.dados_contrato, dict) else 'N/A'
        return f"{self.numero_serie} - {cliente_nome} - {self.banco.nome}"
    
    class Meta:
        verbose_name = "Contrato Operacional"
        verbose_name_plural = "Contratos Operacionais"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['vendedor', 'status_tabulacao']),
            models.Index(fields=['status_tabulacao', 'data_criacao']),
            models.Index(fields=['numero_serie']),
        ]

class AnexoContrato(models.Model):
    """Anexos/documentos dos contratos"""
    contrato = models.ForeignKey(ContratoOperacional, on_delete=models.CASCADE, related_name='anexos', verbose_name="Contrato")
    arquivo = models.FileField(upload_to='contratos/anexos/%Y/%m/', verbose_name="Arquivo")
    titulo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Título")
    tipo_documento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Documento")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def __str__(self):
        return f"{self.contrato} - {self.titulo or self.arquivo.name}"
    
    class Meta:
        verbose_name = "Anexo de Contrato"
        verbose_name_plural = "Anexos de Contrato"
        ordering = ['-data_criacao']
