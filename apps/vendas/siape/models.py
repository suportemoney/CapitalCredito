from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import re
import os

# Importar models do rh.admin (usando string para evitar import circular)
# Setor será referenciado como string 'rh.admin.Setor'

class Produto(models.Model):
    """Produtos que a empresa vende/faz"""
    nome = models.CharField(max_length=255, verbose_name="Nome do Produto")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        super(Produto, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['nome']

class Campanha(models.Model):
    """Campanhas de importação de clientes"""
    titulo = models.CharField(max_length=255, verbose_name="Título da Campanha")
    status = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper() if self.titulo else None
        super(Campanha, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.titulo
    
    class Meta:
        verbose_name = "Campanha"
        verbose_name_plural = "Campanhas"
        ordering = ['-data_criacao']

class Cliente(models.Model):
    """Clientes importados"""
    TIPO_BASE_CHOICES = [
        ('PENSIONISTA', 'Pensionista'),
        ('SERVIDOR', 'Servidor'),
    ]
    
    tipo_base = models.CharField(max_length=20, choices=TIPO_BASE_CHOICES, blank=True, null=True, verbose_name="Tipo de Base")
    nome = models.CharField(max_length=255, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    uf = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")
    situacao_funcional = models.CharField(max_length=100, blank=True, null=True, verbose_name="Situação Funcional")
    celular = models.CharField(max_length=20, blank=True, null=True, verbose_name="Celular")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        self.uf = self.uf.upper() if self.uf else None
        super(Cliente, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.nome} ({self.cpf})"
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nome']
        indexes = [
            models.Index(fields=['cpf']),
        ]

class Matricula(models.Model):
    """Matrículas dos clientes"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='matriculas', verbose_name="Cliente")
    campanha = models.ForeignKey(Campanha, on_delete=models.PROTECT, related_name='matriculas', verbose_name="Campanha")
    matricula = models.CharField(max_length=50, verbose_name="Matrícula")
    matricula_instituidor = models.CharField(max_length=50, blank=True, null=True, verbose_name="Matrícula Instituidor")
    base_calculo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Base de Cálculo")
    orgao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Órgão")
    upag = models.CharField(max_length=100, blank=True, null=True, verbose_name="UPAG")
    rubrica = models.CharField(max_length=100, blank=True, null=True, verbose_name="Rubrica")
    rjur = models.CharField(max_length=50, blank=True, null=True, verbose_name="RJUR")
    status = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def save(self, *args, **kwargs):
        self.matricula = self.matricula.upper() if self.matricula else None
        self.matricula_instituidor = self.matricula_instituidor.upper() if self.matricula_instituidor else None
        self.orgao = self.orgao.upper() if self.orgao else None
        self.upag = self.upag.upper() if self.upag else None
        self.rubrica = self.rubrica.upper() if self.rubrica else None
        super(Matricula, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.matricula} - {self.cliente.nome}"
    
    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        ordering = ['-data_criacao']
        unique_together = [['cliente', 'campanha', 'matricula']]
        indexes = [
            models.Index(fields=['matricula']),
            models.Index(fields=['cliente', 'campanha', 'matricula']),
            models.Index(fields=['campanha', 'status']),
        ]

class Margens(models.Model):
    """Margens de crédito das matrículas"""
    matricula = models.OneToOneField(Matricula, on_delete=models.CASCADE, related_name='margens', verbose_name="Matrícula")
    bruta_5 = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Bruta 5%")
    util_5 = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Util 5%")
    saldo_5 = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Saldo 5%")
    bruta_5b = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Bruta 5B%")
    util_5b = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Util 5B%")
    saldo_5b = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Saldo 5B%")
    bruta_35 = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Bruta 35%")
    util_35 = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Util 35%")
    saldo_35 = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Saldo 35%")
    
    def __str__(self):
        return f"Margens - {self.matricula.matricula}"
    
    class Meta:
        verbose_name = "Margem"
        verbose_name_plural = "Margens"
        ordering = ['matricula__cliente__nome']

class Contrato(models.Model):
    """Contratos/débitos das matrículas (uma linha por parcela/débito no CSV)."""
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name='contratos', verbose_name="Matrícula")
    campanha = models.ForeignKey(Campanha, on_delete=models.PROTECT, related_name='contratos', verbose_name="Campanha")
    tipo_contrato = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de Contrato")
    contrato = models.CharField(max_length=100, verbose_name="Contrato")
    banco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Banco")
    valor_parcela = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor da Parcela")
    parcelas_restantes = models.IntegerField(blank=True, null=True, verbose_name="Parcelas Restantes")
    numero_parcela = models.PositiveIntegerField(default=1, verbose_name="Número da parcela/débito")
    def save(self, *args, **kwargs):
        self.tipo_contrato = self.tipo_contrato.upper() if self.tipo_contrato else None
        self.contrato = self.contrato.upper() if self.contrato else None
        self.banco = self.banco.upper() if self.banco else None
        super(Contrato, self).save(*args, **kwargs)
    def __str__(self):
        return f"{self.contrato} - {self.matricula.matricula}"
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ['-matricula__data_criacao']
        unique_together = [['matricula', 'contrato', 'numero_parcela']]
        indexes = [
            models.Index(fields=['contrato']),
            models.Index(fields=['matricula', 'contrato', 'numero_parcela']),
        ]

class TabulacaoCRM(models.Model):
    """Tabulações do CRM Kanban"""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Tabulação")
    ordem = models.IntegerField(verbose_name="Ordem", help_text="Ordem de exibição no CRM (menor número aparece primeiro)")
    cor = models.CharField(max_length=7, default='#6c757d', verbose_name="Cor", help_text="Cor em hexadecimal (ex: #6c757d)")
    status = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper() if self.nome else None
        super(TabulacaoCRM, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.ordem} - {self.nome}"
    
    class Meta:
        verbose_name = "Tabulação CRM"
        verbose_name_plural = "Tabulações CRM"
        ordering = ['ordem', 'nome']

class ControleCRM(models.Model):
    """Controle de clientes no CRM"""
    cpf = models.CharField(max_length=14, verbose_name="CPF do Cliente")
    data_contato = models.DateField(verbose_name="Data de Contato")
    hora_contato = models.TimeField(verbose_name="Hora de Contato")
    tabulacao = models.ForeignKey(TabulacaoCRM, on_delete=models.PROTECT, related_name='controles', verbose_name="Tabulação")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='controles_crm', verbose_name="Vendedor")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        import re
        self.cpf = re.sub(r'\D', '', self.cpf) if self.cpf else ''
        super(ControleCRM, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cpf} - {self.tabulacao.nome} - {self.data_contato}"
    
    class Meta:
        verbose_name = "Controle CRM"
        verbose_name_plural = "Controles CRM"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['cpf']),
            models.Index(fields=['tabulacao', 'status']),
        ]

class MetaSIAPE(models.Model):
    """Metas do SIAPE para cálculo de ranking"""
    titulo = models.CharField(max_length=255, verbose_name="Título da Meta")
    valor_meta = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor da Meta (R$)")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_final = models.DateField(verbose_name="Data Final")
    status = models.BooleanField(default=True, verbose_name="Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper() if self.titulo else None
        super(MetaSIAPE, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.titulo} - R$ {self.valor_meta}"
    
    class Meta:
        verbose_name = "Meta SIAPE"
        verbose_name_plural = "Metas SIAPE"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['data_inicio', 'data_final']),
            models.Index(fields=['status']),
        ]

def get_crm_upload_path(instance, filename):
    """Define o diretório como 'crm/<tipo>/<controle_id>/<filename>'"""
    if hasattr(instance, 'reversao') and instance.reversao:
        return os.path.join('crm', 'reversao', str(instance.reversao.controle.id), filename)
    elif hasattr(instance, 'checagem') and instance.checagem:
        return os.path.join('crm', 'checagem', str(instance.checagem.controle.id), filename)
    return os.path.join('crm', 'temp', filename)

class Representante(models.Model):
    """Representantes/Responsáveis para Reversão e Checagem"""
    TIPO_CHOICES = [
        ('REVERSAO', 'Reversão'),
        ('CHECAGEM', 'Checagem'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    usuarios = models.ManyToManyField(User, related_name='representantes', verbose_name="Usuários Responsáveis")
    horario_inicio = models.TimeField(blank=True, null=True, verbose_name="Horário Início", help_text="Horário de início do atendimento")
    horario_final = models.TimeField(blank=True, null=True, verbose_name="Horário Final", help_text="Horário final do atendimento")
    tempo_call = models.IntegerField(default=30, verbose_name="Tempo de Call (minutos)", help_text="Duração de cada atendimento em minutos")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def __str__(self):
        usuarios_count = self.usuarios.count()
        return f"{self.get_tipo_display()} - {usuarios_count} responsável(is)"
    
    class Meta:
        verbose_name = "Representante"
        verbose_name_plural = "Representantes"
        ordering = ['tipo', '-data_criacao']

class DadosReversao(models.Model):
    """Dados de negociação quando card é movido para REVERSÃO"""
    controle = models.OneToOneField(ControleCRM, on_delete=models.CASCADE, related_name='dados_reversao', verbose_name="Controle CRM")
    data_para_reversao = models.DateField(verbose_name="Data para Reversão")
    horario_disponivel = models.TimeField(verbose_name="Horário Disponível")
    responsavel_por_reversao = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reversoes_responsaveis', verbose_name="Responsável por Reversão")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def __str__(self):
        return f"Reversão - {self.controle.cpf} - {self.data_para_reversao}"
    
    class Meta:
        verbose_name = "Dados de Reversão"
        verbose_name_plural = "Dados de Reversões"
        ordering = ['-data_criacao']

class ArquivoReversao(models.Model):
    """Arquivos relacionados à reversão"""
    reversao = models.ForeignKey(DadosReversao, on_delete=models.CASCADE, related_name='arquivos', verbose_name="Reversão")
    arquivo = models.FileField(upload_to=get_crm_upload_path, verbose_name="Arquivo")
    titulo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Título do Arquivo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def __str__(self):
        return f"Arquivo - {self.reversao.controle.cpf}"
    
    class Meta:
        verbose_name = "Arquivo de Reversão"
        verbose_name_plural = "Arquivos de Reversões"
        ordering = ['-data_criacao']

class DadosChecagem(models.Model):
    """Dados quando card é movido para CHECAGEM"""
    controle = models.OneToOneField(ControleCRM, on_delete=models.CASCADE, related_name='dados_checagem', verbose_name="Controle CRM")
    data_para_checagem = models.DateField(verbose_name="Data para Checagem")
    horario_disponivel = models.TimeField(verbose_name="Horário Disponível")
    responsavel_por_checagem = models.ForeignKey(User, on_delete=models.PROTECT, related_name='checagens_responsaveis', verbose_name="Responsável por Checagem")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    nome_banco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome do Banco")
    valor_af = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor AF (R$)")
    valor_repasse = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor Repasse (R$)")
    saldo_devedor = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Saldo Devedor (R$)")
    valor_parcela_atual = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor Parcela Atual (R$)")
    valor_parcela_nova_proposta = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor Parcela Nova Proposta (R$)")
    valor_troco = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="Valor Troco (R$)")
    prazo_atual = models.IntegerField(blank=True, null=True, verbose_name="Prazo Atual (meses)")
    prazo_acordado = models.IntegerField(blank=True, null=True, verbose_name="Prazo Acordado (meses)")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def save(self, *args, **kwargs):
        if self.nome_banco:
            self.nome_banco = self.nome_banco.upper()
        super(DadosChecagem, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"Checagem - {self.controle.cpf} - {self.data_para_checagem}"
    
    class Meta:
        verbose_name = "Dados de Checagem"
        verbose_name_plural = "Dados de Checagens"
        ordering = ['-data_criacao']

class ArquivoChecagem(models.Model):
    """Arquivos relacionados à checagem"""
    checagem = models.ForeignKey(DadosChecagem, on_delete=models.CASCADE, related_name='arquivos', verbose_name="Checagem")
    arquivo = models.FileField(upload_to=get_crm_upload_path, verbose_name="Arquivo")
    titulo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Título do Arquivo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def __str__(self):
        return f"Arquivo - {self.checagem.controle.cpf}"
    
    class Meta:
        verbose_name = "Arquivo de Checagem"
        verbose_name_plural = "Arquivos de Checagens"
        ordering = ['-data_criacao']

class HorarioDisponivel(models.Model):
    """Horários disponíveis agendados para responsáveis ligarem para clientes"""
    controle_crm = models.ForeignKey(ControleCRM, on_delete=models.CASCADE, related_name='horarios_agendados', verbose_name="Controle CRM")
    data = models.DateField(verbose_name="Data")
    hora = models.TimeField(verbose_name="Hora", help_text="Hora:minuto do agendamento")
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT, related_name='horarios_agendados', verbose_name="Responsável")
    tabulacao = models.ForeignKey(TabulacaoCRM, on_delete=models.PROTECT, related_name='horarios_agendados', verbose_name="Tabulação")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def __str__(self):
        return f"{self.data} {self.hora} - {self.responsavel.username} - {self.controle_crm.cpf}"
    
    class Meta:
        verbose_name = "Horário Disponível"
        verbose_name_plural = "Horários Disponíveis"
        ordering = ['data', 'hora']
        unique_together = [['controle_crm', 'data', 'hora', 'responsavel', 'tabulacao']]
        indexes = [
            models.Index(fields=['data', 'hora', 'responsavel']),
            models.Index(fields=['tabulacao', 'status']),
        ]


# --- Esteira comercial + financeiro (integração apps.contratos_v2) ---

class ClassificacaoValor(models.Model):
    """Percentual do consultor sobre a base TC (ranking / Pago TC)."""
    titulo = models.CharField(max_length=120, verbose_name='Título')
    percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Percentual',
        help_text='Ex.: 50.00 para 50%',
    )
    status = models.BooleanField(default=True, verbose_name='Ativo')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')

    class Meta:
        verbose_name = 'Classificação de valor'
        verbose_name_plural = 'Classificações de valor'
        ordering = ['-data_criacao']

    def __str__(self):
        return f'{self.titulo} - {self.percentual}%'


class CarteiraClientes(models.Model):
    """Núcleo da esteira comercial: cliente SIAPE + vínculos operacionais (contratos v2)."""
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
    ]
    STATUS_COMERCIAL_CHOICES = [
        ('EM_NEGOCIACAO', 'Em Negociação'),
        ('AGENDAR', 'Agendar'),
        ('SEM_INTERESSE', 'Sem Interesse'),
        ('NAO_E_O_CLIENTE', 'Não é o Cliente'),
        ('AGUARDANDO_DOCUMENTOS', 'Aguardando Documentos'),
        ('DESISTENCIA', 'Desistência'),
        ('NEGOCIO_FECHADO', 'Negócio Fechado'),
        ('SIMULACAO', 'Simulação'),
        ('OPERACIONAL', 'Operacional'),
        ('SOLICITACAO_PROPOSTAS', 'Solicitação de Propostas'),
        ('PROPOSTAS', 'Propostas'),
        ('INELEGIVEL', 'Inelegível'),
        ('DIGITACAO', 'Digitação'),
        ('FINALIZADA', 'Finalizada'),
    ]
    SUB_STATUS_PROPOSTA_COMERCIAL_CHOICES = [
        ('ACEITE', 'Aceite'),
        ('VERIFICANDO', 'Verificando'),
        ('VERIFICADO', 'Verificado'),
    ]
    TAG_PROPOSTA_CONTAINER_CHOICES = [
        ('AGUARDANDO', 'Aguardando'),
        ('SUCESSO', 'Sucesso'),
        ('INELEGIVEL', 'Inelegível'),
    ]
    TAG_STATUS_OPERACIONAL_CHOICES = [
        ('AGUARDANDO_SIMULACAO', 'Aguardando Simulação'),
        ('AGUARDANDO_PROPOSTA', 'Aguardando Proposta'),
        ('AGUARDANDO_DIGITACAO', 'Aguardando Digitação'),
        ('EM_DIGITACAO', 'Em Digitação'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='carteira_clientes',
        verbose_name='Cliente',
    )
    cliente_operacional = models.ForeignKey(
        'contratos_v2.ClienteDadosPessoais',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='carteiras_siape',
        verbose_name='Cliente operacional (contratos)',
    )
    simulacoes_operacionais = models.ManyToManyField(
        'contratos_v2.Simulacao',
        blank=True,
        related_name='carteiras_siape',
        verbose_name='Simulações (operacional)',
    )
    contratos_operacionais = models.ManyToManyField(
        'contratos_v2.ContratoExecucao',
        blank=True,
        related_name='carteiras_siape',
        verbose_name='Contratos (operacional)',
    )
    propostas_operacionais = models.ManyToManyField(
        'contratos_v2.PropostaDados',
        blank=True,
        related_name='carteiras_siape_propostas',
        verbose_name='Propostas (operacional)',
    )
    user_responsavel = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='carteira_como_responsavel',
        verbose_name='Usuário responsável',
    )
    user_repasse = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carteira_como_repasse',
        verbose_name='Usuário repasse',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ATIVO',
        db_index=True,
        verbose_name='Status',
    )
    status_comercial = models.CharField(
        max_length=30,
        choices=STATUS_COMERCIAL_CHOICES,
        default='EM_NEGOCIACAO',
        db_index=True,
        blank=True,
        null=True,
        verbose_name='Status comercial',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    tabulacao_operacional = models.CharField(
        max_length=140,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Tabulação operacional (agregada)',
    )
    tags_operacionais = models.TextField(blank=True, null=True, verbose_name='Tags operacionais')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')
    tag_proposta_container = models.CharField(
        max_length=20,
        choices=TAG_PROPOSTA_CONTAINER_CHOICES,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Tag container propostas',
    )
    sub_status_propostas_comercial = models.CharField(
        max_length=20,
        choices=SUB_STATUS_PROPOSTA_COMERCIAL_CHOICES,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Sub-status propostas (comercial)',
    )
    tag_status_operacional = models.CharField(
        max_length=40,
        choices=TAG_STATUS_OPERACIONAL_CHOICES,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Tag status operacional',
    )

    class Meta:
        verbose_name = 'Carteira de cliente'
        verbose_name_plural = 'Carteira de clientes'
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['user_responsavel']),
            models.Index(fields=['user_repasse']),
            models.Index(fields=['status']),
            models.Index(fields=['status_comercial']),
        ]

    def __str__(self):
        return f'Carteira - {self.cliente.nome}'


class ArquivoCarteiraCliente(models.Model):
    carteira_clientes = models.ForeignKey(
        CarteiraClientes,
        on_delete=models.CASCADE,
        related_name='arquivos_carteira',
        verbose_name='Carteira',
    )
    arquivo = models.FileField(upload_to='carteira_clientes/%Y/%m/', verbose_name='Arquivo')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='arquivos_carteira_enviados',
        verbose_name='Usuário',
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')

    class Meta:
        verbose_name = 'Arquivo da carteira'
        verbose_name_plural = 'Arquivos da carteira'
        ordering = ['-data_criacao']


class TabulacaoVendedor(models.Model):
    """Histórico de tabulação comercial da carteira."""
    TIPO_CHOICES = CarteiraClientes.STATUS_COMERCIAL_CHOICES

    carteira_clientes = models.ForeignKey(
        CarteiraClientes,
        on_delete=models.CASCADE,
        related_name='tabulacoes_vendedor',
        verbose_name='Carteira',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tabulacoes_vendedor',
        verbose_name='Usuário',
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, db_index=True, verbose_name='Tipo')
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')

    class Meta:
        verbose_name = 'Tabulação vendedor'
        verbose_name_plural = 'Tabulações vendedor'
        ordering = ['-data_criacao']


class RegisterMoney(models.Model):
    """Registro financeiro (TC/CMS) vinculado ao contrato operacional."""
    CLASSIFICADOR_TC_CHOICES = (
        ('M1', 'M1 (100% - Novo)'),
        ('M2', 'M2 (50% - Retrabalho)'),
        ('M3', 'M3 (0% - Manual)'),
    )
    TIPO_CLASSIFICACAO_CHOICES = (
        ('NOVO', 'Novo'),
        ('RETRABALHO', 'Retrabalho'),
        ('MANUAL', 'Manual M3'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário')
    loja = models.ForeignKey(
        'rh_admin.Loja',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Loja',
    )
    cpf_cliente = models.CharField(max_length=14, blank=True, null=True, db_index=True)
    produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Produto',
    )
    valor_est = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Valor estimado (TC)',
    )
    valor_pago_acumulado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='TC pago acumulado',
    )
    af = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='AF')
    valor_cms_recebido = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='CMS recebido'
    )
    valor_cms_repassado = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='CMS repassado'
    )
    valor_cms_plastico = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='CMS plástico'
    )
    flag_cms_pago = models.BooleanField(default=False, verbose_name='CMS pago')
    classificador_auto = models.CharField(
        max_length=2,
        choices=CLASSIFICADOR_TC_CHOICES,
        blank=True,
        null=True,
        db_index=True,
    )
    tipo_classificacao = models.CharField(
        max_length=15,
        choices=TIPO_CLASSIFICACAO_CHOICES,
        blank=True,
        null=True,
    )
    status = models.BooleanField(default=True, blank=True, null=True, verbose_name='Ativo')
    data = models.DateTimeField(default=timezone.now, blank=True, null=True, db_index=True)
    data_pago = models.DateTimeField(blank=True, null=True, db_index=True)
    empresa = models.ForeignKey(
        'rh_admin.Empresa',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='registros_financeiros',
    )
    departamento = models.ForeignKey(
        'rh_admin.Departamento',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='registros_financeiros',
    )
    setor = models.ForeignKey(
        'rh_admin.Setor',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='registros_financeiros',
    )
    equipe = models.ForeignKey(
        'rh_admin.Equipe',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='registros_financeiros',
    )
    flg_ponta = models.BooleanField(default=False, blank=True, null=True, verbose_name='Flag ponta')
    classificacao_valor = models.ForeignKey(
        ClassificacaoValor,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='registros_financeiros',
    )
    contrato_execucao = models.ForeignKey(
        'contratos_v2.ContratoExecucao',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='registros_financeiros_tc',
    )
    flag_repasse = models.BooleanField(default=False, verbose_name='Linha de repasse')

    class Meta:
        verbose_name = 'Registro financeiro'
        verbose_name_plural = 'Registros financeiros'
        ordering = ['-data']

    def __str__(self):
        return f'RM #{self.pk} - {self.cpf_cliente or "-"}'

