# -*- coding: utf-8 -*-
"""Modelos do fluxo de contratos pós-contato (cliente operacional, propostas, execução)."""
import secrets
import string

from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.contratos_v2.fluxo_constants import (
    EstadoSolicitacaoProposta,
    EstadoSolicitacaoDigitacao,
    EtapaOperacional,
    FaseContratoExecucao,
    SubStatusOperacional,
    TagFinanceiraContrato,
)


# Caminhos estáveis (alinhados à migração 0023)
UPLOAD_CLIENTE_ARQUIVO = 'contratos/cliente_arquivos/%Y/%m/'
UPLOAD_SOLICITACAO_PDF = 'contratos/solicitacoes_digitacao/%Y/%m/'
UPLOAD_CONTRATO_VIDEO = 'contratos/videos/%Y/%m/'


def contrato_video_upload_path(instance, filename):
    """
    Compatibilidade com migrações antigas (ex.: 0001_initial).

    Mantém o upload do vídeo em MEDIA_ROOT dentro de `contratos/videos/YYYY/MM/`.
    """
    dt = timezone.now()
    return f"contratos/videos/{dt:%Y/%m}/{filename}"


def anexo_contrato_upload_path(instance, filename):
    """
    Compatibilidade com migrações antigas (ex.: 0001_initial).

    Caminho dos anexos do contrato operacional legado.
    """
    dt = timezone.now()
    return f"contratos/anexos/{dt:%Y/%m}/{filename}"


def gerar_codigo_proposta_numerico():
    """12 dígitos numéricos únicos (token proposta)."""
    return ''.join(secrets.choice(string.digits) for _ in range(12))


def gerar_codigo_contrato_alfanumerico():
    """12 caracteres maiúsculos + dígitos (token contrato)."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))


class ClienteDadosPessoais(models.Model):
    """Raiz dos dados cadastrais do cliente no fluxo de contratos."""
    nome_completo = models.CharField(max_length=255, verbose_name='Nome completo')
    sexo = models.CharField(max_length=20, blank=True, null=True, verbose_name='Sexo')
    data_nascimento = models.DateField(blank=True, null=True, verbose_name='Data de nascimento')
    naturalidade = models.CharField(max_length=120, blank=True, null=True, verbose_name='Naturalidade')
    pais_origem = models.CharField(max_length=80, blank=True, null=True, verbose_name='País de origem')
    cpf = models.CharField(max_length=14, unique=True, db_index=True, verbose_name='CPF')
    numero_rg = models.CharField(max_length=30, blank=True, null=True, verbose_name='Número RG')
    orgao_emissor_rg = models.CharField(max_length=20, blank=True, null=True, verbose_name='Órgão emissor RG')
    uf_emissao_rg = models.CharField(max_length=2, blank=True, null=True, verbose_name='UF emissão RG')
    data_emissao_rg = models.DateField(blank=True, null=True, verbose_name='Data emissão RG')
    nome_pai = models.CharField(max_length=255, blank=True, null=True, verbose_name='Nome do pai')
    nome_mae = models.CharField(max_length=255, blank=True, null=True, verbose_name='Nome da mãe')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última atualização')

    class Meta:
        verbose_name = 'Cliente — dados pessoais'
        verbose_name_plural = 'Cliente — dados pessoais'
        ordering = ['-data_criacao']

    def __str__(self):
        return f'{self.nome_completo} ({self.cpf})'


class ClienteContato(models.Model):
    cliente_dados_pessoais = models.OneToOneField(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='contato',
        verbose_name='Dados pessoais',
    )
    email = models.EmailField(blank=True, null=True, verbose_name='E-mail')
    email_secundario = models.EmailField(blank=True, null=True, verbose_name='E-mail secundário')
    telefone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Telefone')
    telefone_residencial = models.CharField(max_length=30, blank=True, null=True, verbose_name='Telefone residencial')

    class Meta:
        verbose_name = 'Cliente — contato'
        verbose_name_plural = 'Cliente — contatos'


class ClienteEndereco(models.Model):
    cliente_dados_pessoais = models.OneToOneField(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='endereco',
        verbose_name='Dados pessoais',
    )
    cep = models.CharField(max_length=12, blank=True, null=True, verbose_name='CEP')
    logradouro = models.CharField(max_length=255, blank=True, null=True, verbose_name='Logradouro')

    class Meta:
        verbose_name = 'Cliente — endereço'
        verbose_name_plural = 'Cliente — endereços'


class ClienteBancario(models.Model):
    """Dados bancários: conta de recebimento do cliente (DP) ou vínculo por proposta/contrato."""
    cliente_dados_pessoais = models.OneToOneField(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bancario',
        verbose_name='Dados pessoais',
    )
    proposta_dados = models.OneToOneField(
        'PropostaDados',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='dados_bancarios',
        verbose_name='Proposta',
    )
    contrato_execucao = models.OneToOneField(
        'ContratoExecucao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dados_bancarios',
        verbose_name='Contrato (se gerado)',
    )
    banco          = models.CharField(max_length=120, blank=True, null=True, verbose_name='Banco')
    agencia        = models.CharField(max_length=20,  blank=True, null=True, verbose_name='Agência')
    dv_agencia     = models.CharField(max_length=5,   blank=True, null=True, verbose_name='DV agência')
    conta          = models.CharField(max_length=30,  blank=True, null=True, verbose_name='Conta')
    dv_conta       = models.CharField(max_length=5,   blank=True, null=True, verbose_name='DV conta')
    tipo_conta     = models.CharField(max_length=40,  blank=True, null=True, verbose_name='Tipo de conta')
    tipo_pagamento = models.CharField(max_length=40,  blank=True, null=True, verbose_name='Tipo de pagamento')
    incluir_seguro = models.BooleanField(default=False, verbose_name='Incluir seguro')
    matricula      = models.CharField(max_length=80,  blank=True, null=True, verbose_name='Matrícula')
    senha          = models.CharField(max_length=120, blank=True, null=True, verbose_name='Senha (evitar texto puro em produção)')

    class Meta:
        verbose_name = 'Cliente — dados bancários'
        verbose_name_plural = 'Cliente — dados bancários'


class ClienteRepresentante(models.Model):
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='representantes',
        verbose_name='Dados pessoais',
    )
    nome_representante = models.CharField(max_length=255, blank=True, null=True, verbose_name='Nome representante')
    cpf_representante  = models.CharField(max_length=14,  blank=True, null=True, verbose_name='CPF representante')

    class Meta:
        verbose_name = 'Cliente — representante'
        verbose_name_plural = 'Cliente — representantes'
        ordering = ['id']


class ClienteArquivo(models.Model):
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='arquivos',
        verbose_name='Dados pessoais',
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    tipo = models.CharField(max_length=20, blank=True, null=True, verbose_name='Tipo (extensão)')
    arquivo = models.FileField(upload_to=UPLOAD_CLIENTE_ARQUIVO, verbose_name='Arquivo')
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')
    status = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Cliente — arquivo'
        verbose_name_plural = 'Cliente — arquivos'
        ordering = ['-data_criacao']


class Banco(models.Model):
    titulo = models.CharField(max_length=150, verbose_name='Título')
    codigo = models.CharField(max_length=30, blank=True, null=True, verbose_name='Código')
    ispb = models.CharField(max_length=20, blank=True, null=True, verbose_name='ISPB')
    nome_curto = models.CharField(max_length=50, blank=True, null=True, verbose_name='Nome curto')
    dominio = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Domínio oficial',
        help_text='Ex.: bb.com.br — usado para buscar logo (Brandfetch / Logo.dev).',
    )
    logo_url = models.URLField(blank=True, null=True, verbose_name='URL do logo (remoto)')
    logo = models.ImageField(
        upload_to='bancos/logos/',
        blank=True,
        null=True,
        verbose_name='Logo (cache local)',
    )
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')
    status = models.BooleanField(default=True, db_index=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Banco (catálogo contratos)'
        verbose_name_plural = 'Bancos (catálogo contratos)'
        ordering = ['titulo']
        # Bloqueio case-insensitive contra duplicidade ("BANCO X" == "Banco X").
        constraints = [
            models.UniqueConstraint(
                Lower('titulo'),
                name='uniq_banco_titulo_lower',
            ),
        ]
        # Índice explícito sobre Lower(titulo) acelera buscas iexact/icontains.
        indexes = [
            models.Index(Lower('titulo'), name='idx_banco_titulo_lower'),
        ]

    def __str__(self):
        return self.titulo

    @property
    def logo_exibicao_url(self):
        """Prioriza cache local em /media/; senão URL remota."""
        if self.logo:
            return self.logo.url
        return self.logo_url or None


class Convenio(models.Model):
    titulo = models.CharField(max_length=150, verbose_name='Título')
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')
    status = models.BooleanField(default=True, db_index=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Convênio (catálogo contratos)'
        verbose_name_plural = 'Convênios (catálogo contratos)'
        ordering = ['titulo']
        constraints = [
            models.UniqueConstraint(
                Lower('titulo'),
                name='uniq_convenio_titulo_lower',
            ),
        ]
        indexes = [
            models.Index(Lower('titulo'), name='idx_convenio_titulo_lower'),
        ]

    def __str__(self):
        return self.titulo


class Produto(models.Model):
    titulo = models.CharField(max_length=150, verbose_name='Título')
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')
    status = models.BooleanField(default=True, db_index=True, verbose_name='Ativo')
    flag_port_mais_refin = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Port + Refin',
        help_text='Ao confirmar Pago Cliente, gera contrato REFIN vinculado.',
    )
    flag_refin_da_port = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Refin da Port',
        help_text='Produto filho usado na segunda proposta/contrato do par Port+Refin.',
    )

    class Meta:
        verbose_name = 'Produto (catálogo contratos)'
        verbose_name_plural = 'Produtos (catálogo contratos)'
        ordering = ['titulo']
        constraints = [
            models.UniqueConstraint(
                Lower('titulo'),
                name='uniq_produto_titulo_lower',
            ),
        ]
        indexes = [
            models.Index(Lower('titulo'), name='idx_produto_titulo_lower'),
        ]

    def __str__(self):
        return self.titulo


class TabelaCms(models.Model):
    # Rótulo informativo "Classificador Banco" (M1 = 100% / M2 = 50% / M3 = 0%).
    # Não confunde com o Classificador de TC do RegisterMoney (esse é calculado
    # automaticamente novo/retrabalho 90 dias, ver apps/siape/apis/classificador.py).
    #
    # Decisão de schema (validação item [1] catálogo):
    # NÃO aplicamos UniqueConstraint(banco, convenio, produto) porque o negócio
    # admite múltiplas tabelas ativas para a mesma combinação — cada uma com um
    # classificador_banco distinto (M1/M2/M3) ou com taxas específicas de campanha.
    # A unicidade efetiva deve ser pelo `titulo` dentro da combinação, mas como o
    # catálogo permite renomear tabelas mantendo histórico, preferimos controlar
    # duplicidade via UI (alerta) e via o comando management dedupe_catalogo.
    CLASSIFICADOR_BANCO_CHOICES = (
        ('M1', 'M1 (100%)'),
        ('M2', 'M2 (50%)'),
        ('M3', 'M3 (0%)'),
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, related_name='tabelas_cms', verbose_name='Banco')
    convenio = models.ForeignKey(Convenio, on_delete=models.PROTECT, related_name='tabelas_cms', verbose_name='Convênio')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='tabelas_cms', verbose_name='Produto')
    # db_index=True: preparado para filtros no Relatório CMS e segmentações por tier (M1/M2/M3).
    # Custo de storage/índice é desprezível (char(2)) e evita full scans em volumes grandes.
    classificador_banco = models.CharField(
        max_length=2,
        choices=CLASSIFICADOR_BANCO_CHOICES,
        default='M1',
        db_index=True,
        verbose_name='Classificador Banco',
        help_text='Rótulo da tabela: M1 (100%) / M2 (50%) / M3 (0%).',
    )
    taxa_recebido = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True, verbose_name='Taxa recebido')
    taxa_repasse = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True, verbose_name='Taxa repasse')
    taxa_plastico = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True, verbose_name='Taxa plástico')
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')
    data_ultima_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última atualização')
    status = models.BooleanField(default=True, db_index=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Tabela CMS'
        verbose_name_plural = 'Tabelas CMS'
        ordering = ['-data_criacao']

    def __str__(self):
        return self.titulo


class LogCatalogoContratos(models.Model):
    """Auditoria de alterações nos catálogos (Banco, Convênio, Produto, Tabela CMS)."""

    ACAO_CHOICES = (
        ('criar', 'Criação'),
        ('editar', 'Edição'),
        ('inativar', 'Inativação'),
        ('reativar', 'Reativação'),
        ('excluir', 'Exclusão definitiva'),
        ('importar_csv', 'Importação CSV'),
    )
    ENTIDADE_CHOICES = (
        ('banco', 'Banco'),
        ('convenio', 'Convênio'),
        ('produto', 'Produto'),
        ('tabela_cms', 'Tabela CMS'),
    )

    acao = models.CharField(max_length=20, choices=ACAO_CHOICES, db_index=True, verbose_name='Ação')
    entidade = models.CharField(max_length=20, choices=ENTIDADE_CHOICES, db_index=True, verbose_name='Entidade')
    registro_id = models.PositiveIntegerField(null=True, blank=True, db_index=True, verbose_name='ID do registro')
    registro_titulo = models.CharField(max_length=200, blank=True, default='', verbose_name='Título / identificador')
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_catalogo_contratos',
        verbose_name='Usuário',
    )
    data = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')
    dados_antes = models.JSONField(null=True, blank=True, verbose_name='Dados antes')
    dados_depois = models.JSONField(null=True, blank=True, verbose_name='Dados depois')
    resumo = models.TextField(blank=True, default='', verbose_name='Resumo')

    class Meta:
        verbose_name = 'Log catálogo contratos'
        verbose_name_plural = 'Logs catálogo contratos'
        ordering = ['-data']

    def __str__(self):
        return f'{self.get_entidade_display()} #{self.registro_id or "?"} — {self.get_acao_display()}'


class SolicitacaoPropostaCliente(models.Model):
    """Primeiro envio: vendedor preenche dados e operacional responde Propostas ou Inelegível."""
    carteira_clientes = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.CASCADE,
        related_name='solicitacoes_proposta_contrato',
        verbose_name='Carteira',
    )
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='solicitacoes_proposta',
        verbose_name='Dados pessoais',
    )
    estado = models.CharField(
        max_length=40,
        choices=EstadoSolicitacaoProposta.CHOICES,
        default=EstadoSolicitacaoProposta.ENVIADA,
        db_index=True,
        verbose_name='Estado',
    )
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='solicitacoes_proposta_criadas',
        verbose_name='Criado por (vendedor)',
    )
    respondido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_proposta_respondidas',
        verbose_name='Respondido por (operacional)',
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')
    data_resposta = models.DateTimeField(blank=True, null=True, verbose_name='Data da resposta')
    observacao_resposta = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observação do retorno (operacional)',
        help_text='Texto geral do operacional ao responder (não por proposta).',
    )

    class Meta:
        verbose_name = 'Solicitação de proposta (cliente)'
        verbose_name_plural = 'Solicitações de proposta'
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['carteira_clientes', '-data_criacao']),
            models.Index(fields=['estado']),
        ]


class PropostaDados(models.Model):
    """Proposta operacional com código numérico 12 posições."""
    codigo = models.CharField(max_length=12, unique=True, db_index=True, blank=True, null=True, verbose_name='Código (token)')
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='propostas_dados',
        verbose_name='Cliente',
    )
    solicitacao_origem = models.ForeignKey(
        SolicitacaoPropostaCliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='propostas_geradas',
        verbose_name='Solicitação de origem',
    )
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, related_name='propostas_dados', verbose_name='Banco')
    convenio = models.ForeignKey(Convenio, on_delete=models.PROTECT, related_name='propostas_dados', verbose_name='Convênio')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='propostas_dados', verbose_name='Produto')
    # Tabela CMS escolhida pelo vendedor no wizard de envio; opcional para compatibilidade com registros antigos.
    # No operacional, essa tabela é usada como default ao gerar o ContratoExecucao.
    tabela_cms = models.ForeignKey(
        TabelaCms,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='propostas_dados',
        verbose_name='Tabela CMS',
    )
    valor_parcela = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor parcela')
    prazo = models.PositiveIntegerField(blank=True, null=True, verbose_name='Prazo')
    # Coeficiente usado para calcular AF (AF = parcela / coeficiente). 6 casas decimais para precisão bancária.
    coeficiente = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True, verbose_name='Coeficiente')
    valor_af = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor AF')
    valor_tc = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor TC')
    valor_liberado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor liberado')
    valor_saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Valor saldo',
        help_text='Informado no Pago Cliente para produtos PORT.',
    )
    aceita_pelo_cliente = models.BooleanField(default=False, verbose_name='Aceita pelo cliente')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='propostas_dados_criadas',
        verbose_name='Criado por',
    )
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')
    proposta_vinculo_port = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='propostas_refin_geradas',
        verbose_name='Proposta PORT (origem)',
    )

    class Meta:
        verbose_name = 'Proposta (dados)'
        verbose_name_plural = 'Propostas (dados)'
        ordering = ['-data_criacao']

    def save(self, *args, **kwargs):
        if not self.codigo:
            for _ in range(32):
                c = gerar_codigo_proposta_numerico()
                if not PropostaDados.objects.filter(codigo=c).exists():
                    self.codigo = c
                    break
            else:
                self.codigo = gerar_codigo_proposta_numerico()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Proposta {self.codigo}'


class ContratoPortado(models.Model):
    """Contrato existente a portar, informado pelo vendedor (opcional). Vinculado à proposta; contrato em execução preenchido após digitação."""

    proposta_dados = models.ForeignKey(
        PropostaDados,
        on_delete=models.CASCADE,
        related_name='contratos_portados',
        verbose_name='Proposta',
    )
    contrato_execucao = models.ForeignKey(
        'ContratoExecucao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contratos_portados_origem',
        verbose_name='Contrato digitado (quando existir)',
    )
    banco = models.ForeignKey(
        Banco,
        on_delete=models.PROTECT,
        related_name='contratos_portados',
        verbose_name='Banco (origem)',
        null=True,
        blank=True,
    )
    numero_contrato = models.CharField(max_length=80, blank=True, null=True, verbose_name='Número do contrato')
    valor_parcela = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor parcela')
    valor_af = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor AF')
    valor_devedor_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor devedor total')
    prazo_total = models.PositiveIntegerField(blank=True, null=True, verbose_name='Prazo total')
    prazo_restante = models.PositiveIntegerField(blank=True, null=True, verbose_name='Prazo restante')
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name='Data de criação')

    class Meta:
        verbose_name = 'Contrato existente (portado)'
        verbose_name_plural = 'Contratos existentes (portados)'
        ordering = ['-data_criacao']

    def clean(self):
        from django.core.exceptions import ValidationError

        tem_banco = self.banco_id
        tem_vf = self.valor_af is not None
        tem_vp = self.valor_parcela is not None
        tem_pt = self.prazo_total is not None
        tem_pr = self.prazo_restante is not None
        tem_num = bool((self.numero_contrato or '').strip())
        tem_dev = self.valor_devedor_total is not None
        algum = tem_banco or tem_vf or tem_vp or tem_pt or tem_pr or tem_num or tem_dev
        if not algum:
            return
        gatilho = tem_banco or tem_vf
        if gatilho:
            erros = {}
            if not tem_banco:
                erros['banco'] = 'Obrigatório ao informar dados do contrato existente.'
            if not tem_vf:
                erros['valor_af'] = 'Obrigatório ao informar dados do contrato existente.'
            if not tem_vp:
                erros['valor_parcela'] = 'Obrigatório ao informar dados do contrato existente.'
            if not tem_pt:
                erros['prazo_total'] = 'Obrigatório ao informar dados do contrato existente.'
            if not tem_pr:
                erros['prazo_restante'] = 'Obrigatório ao informar dados do contrato existente.'
            if erros:
                raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Contrato existente #{self.id}'


class SolicitacaoDigitacao(models.Model):
    """Uma linha por proposta quando o vendedor solicita contrato (PDF + obs)."""
    proposta_dados = models.ForeignKey(
        PropostaDados,
        on_delete=models.CASCADE,
        related_name='solicitacoes_digitacao',
        verbose_name='Proposta',
    )
    carteira_clientes = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.CASCADE,
        related_name='solicitacoes_digitacao',
        verbose_name='Carteira',
    )
    observacoes = models.TextField(blank=True, null=True, verbose_name='Observações')
    # Preenchidos pelo vendedor no modal de correção pré-contrato (antes de existir ContratoExecucao).
    numero_contrato_banco_pre = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name='Nº contrato (banco) — pré-geração',
    )
    link_formalizacao_pre = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Link formalização — pré-geração',
    )
    arquivo_pdf_proposta = models.FileField(
        upload_to=UPLOAD_SOLICITACAO_PDF,
        blank=True,
        null=True,
        verbose_name='PDF da proposta enviada ao cliente',
    )
    estado = models.CharField(
        max_length=40,
        choices=EstadoSolicitacaoDigitacao.CHOICES,
        default=EstadoSolicitacaoDigitacao.PENDENTE_OPERACIONAL,
        db_index=True,
        verbose_name='Estado',
    )
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='solicitacoes_digitacao_criadas',
        verbose_name='Vendedor',
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')

    class Meta:
        verbose_name = 'Solicitação de digitação'
        verbose_name_plural = 'Solicitações de digitação'
        ordering = ['-data_criacao']


class Simulacao(models.Model):
    """Simulação operacional associada ao cliente (nexos)."""
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='simulacoes',
        verbose_name='Cliente',
    )
    titulo = models.CharField(max_length=120, blank=True, null=True, verbose_name='Título')
    dados = models.JSONField(blank=True, null=True, verbose_name='Dados da simulação')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='simulacoes_contratos_criadas',
        verbose_name='Criado por',
    )
    data_criacao = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Data de criação')
    status = models.BooleanField(default=True, db_index=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Simulação (contratos)'
        verbose_name_plural = 'Simulações (contratos)'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Simulação {self.id}"


class ContratoExecucao(models.Model):
    """Contrato gerado pelo operacional; token alfanumérico; fases do fluxo."""

    class NivelRiscoChecagemSupervisor(models.TextChoices):
        """Avaliação do supervisor ao tabular como Checado (contratos v2)."""
        BAIXO = 'BAIXO', 'Baixo'
        ALTO = 'ALTO', 'Alto'

    codigo = models.CharField(max_length=30, unique=True, db_index=True, blank=True, null=True, verbose_name='Nº Contrato')
    proposta_dados = models.ForeignKey(
        PropostaDados,
        on_delete=models.PROTECT,
        related_name='contratos_execucao',
        verbose_name='Proposta',
    )
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.PROTECT,
        related_name='contratos_execucao',
        verbose_name='Cliente',
    )
    solicitacao_digitacao = models.OneToOneField(
        SolicitacaoDigitacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contrato_execucao',
        verbose_name='Solicitação de digitação',
    )
    simulacao_origem = models.ForeignKey(
        Simulacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contratos',
        verbose_name='Simulação (origem)',
    )
    contrato_vinculo_port = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='contratos_refin_gerados',
        verbose_name='Contrato PORT (origem)',
    )
    carteira_clientes_snapshot = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contratos_execucao_snapshot_carteira',
        verbose_name='Carteira (snapshot no fechamento)',
        help_text='Carteira SIAPE no momento da geração do contrato (repasse/auditoria).',
    )
    user_repasse_snapshot = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contratos_execucao_como_repasse_snapshot',
        verbose_name='Usuário repasse (snapshot)',
        help_text='Quem repassou o cliente à carteira no momento da geração do contrato.',
    )
    fase = models.CharField(
        max_length=40,
        choices=FaseContratoExecucao.CHOICES,
        default=FaseContratoExecucao.DIGITACAO_AGUARDANDO,
        db_index=True,
        verbose_name='Fase / tabulação operacional (legado, sincronizada)',
    )
    etapa_operacional = models.CharField(
        max_length=20,
        choices=EtapaOperacional.CHOICES,
        default=EtapaOperacional.DIGITACAO,
        db_index=True,
        verbose_name='Etapa operacional (nexos)',
    )
    sub_status_operacional = models.CharField(
        max_length=40,
        choices=SubStatusOperacional.CHOICES,
        default=SubStatusOperacional.DIG_AGUARDANDO,
        db_index=True,
        verbose_name='Sub-status operacional',
    )
    portabilidade = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Portabilidade (CIP/Refin manual)',
    )
    nivel_risco_checagem_supervisor = models.CharField(
        max_length=10,
        choices=NivelRiscoChecagemSupervisor.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Nível de risco (checagem supervisor)',
    )
    observacao_checagem_consultor = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observação do consultor para checagem (+OBS)',
        help_text='Texto enviado pelo consultor em Link disponível; visível ao supervisor no modal de checagem.',
    )
    pendencia_etapa_origem = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Pendência — etapa de origem',
    )
    pendencia_sub_origem = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name='Pendência — sub-status de origem',
    )
    tag_financeira = models.CharField(
        max_length=40,
        choices=TagFinanceiraContrato.CHOICES,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Tag financeira (referência)',
    )
    destaque_vendedor = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Destacar para vendedor (ex.: piscar vermelho)',
    )
    link_formalizacao = models.URLField(max_length=500, blank=True, null=True, verbose_name='Link de formalização')
    video_cliente = models.FileField(upload_to=UPLOAD_CONTRATO_VIDEO, blank=True, null=True, verbose_name='Vídeo do cliente')
    video_tamanho = models.PositiveIntegerField(blank=True, null=True, verbose_name='Tamanho do vídeo (bytes)')
    flag_video_enviado = models.BooleanField(default=False, verbose_name='Vídeo de conscientização enviado')
    data_criacao = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Data de criação')
    data_ultima_atualizacao = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name='Última atualização',
    )
    status = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Contrato (execução)'
        verbose_name_plural = 'Contratos (execução)'
        ordering = ['-data_ultima_atualizacao']
        indexes = [
            models.Index(fields=['fase', 'destaque_vendedor']),
            models.Index(fields=['etapa_operacional', 'sub_status_operacional']),
            models.Index(fields=['contrato_vinculo_port'], name='idx_ce_vinculo_port'),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo:
            for _ in range(32):
                c = gerar_codigo_contrato_alfanumerico()
                if not ContratoExecucao.objects.filter(codigo=c).exists():
                    self.codigo = c
                    break
            else:
                self.codigo = gerar_codigo_contrato_alfanumerico()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo


class HistoricoTransicaoContrato(models.Model):
    """Histórico de mudanças de etapa/sub-status (auditoria)."""
    contrato_execucao = models.ForeignKey(
        ContratoExecucao,
        on_delete=models.CASCADE,
        related_name='historico_transicoes',
        verbose_name='Contrato',
    )
    etapa_anterior = models.CharField(max_length=20, blank=True, default='', verbose_name='Etapa anterior')
    sub_anterior = models.CharField(max_length=40, blank=True, default='', verbose_name='Sub anterior')
    etapa_nova = models.CharField(max_length=20, verbose_name='Etapa nova')
    sub_nova = models.CharField(max_length=40, verbose_name='Sub nova')
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historicos_transicao_contrato',
        verbose_name='Usuário',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data')

    class Meta:
        verbose_name = 'Histórico de transição (contrato)'
        verbose_name_plural = 'Históricos de transição (contratos)'
        ordering = ['-data']


class HistoricoEventoSimulacao(models.Model):
    """Auditoria de mudanças de estado em SolicitacaoPropostaCliente."""
    solicitacao = models.ForeignKey(
        SolicitacaoPropostaCliente,
        on_delete=models.CASCADE,
        related_name='historico_eventos',
        verbose_name='Solicitação',
    )
    estado_anterior = models.CharField(max_length=40, blank=True, default='', verbose_name='Estado anterior')
    estado_novo = models.CharField(max_length=40, verbose_name='Estado novo')
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historicos_evento_simulacao',
        verbose_name='Usuário',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data')

    class Meta:
        verbose_name = 'Histórico de evento (simulação)'
        verbose_name_plural = 'Históricos de eventos (simulação)'
        ordering = ['data']


class HistoricoEventoDigitacao(models.Model):
    """Auditoria de mudanças de estado em SolicitacaoDigitacao."""
    solicitacao = models.ForeignKey(
        SolicitacaoDigitacao,
        on_delete=models.CASCADE,
        related_name='historico_eventos',
        verbose_name='Solicitação de digitação',
    )
    estado_anterior = models.CharField(max_length=40, blank=True, default='', verbose_name='Estado anterior')
    estado_novo = models.CharField(max_length=40, verbose_name='Estado novo')
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historicos_evento_digitacao',
        verbose_name='Usuário',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data')

    class Meta:
        verbose_name = 'Histórico de evento (digitação)'
        verbose_name_plural = 'Históricos de eventos (digitação)'
        ordering = ['data']


class ContratoDadosOperacionais(models.Model):
    """Snapshot operacional no fechamento da digitação (tabela CMS + valores)."""
    contrato_execucao = models.OneToOneField(
        ContratoExecucao,
        on_delete=models.CASCADE,
        related_name='dados_operacionais',
        verbose_name='Contrato',
    )
    banco = models.ForeignKey(Banco, on_delete=models.PROTECT, verbose_name='Banco')
    convenio = models.ForeignKey(Convenio, on_delete=models.PROTECT, verbose_name='Convênio')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, verbose_name='Produto')
    tabela_cms = models.ForeignKey(
        TabelaCms,
        on_delete=models.PROTECT,
        verbose_name='Tabela CMS',
    )
    valor_parcela = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor parcela')
    prazo = models.PositiveIntegerField(blank=True, null=True, verbose_name='Prazo')
    valor_af = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor AF')
    valor_tc = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor TC')
    valor_liberado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Valor liberado')
    valor_saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Valor saldo (snapshot)',
    )

    # Snapshot da tabela CMS no fechamento (imutável por FK; auditoria em data_att_cms)
    tabela_cms_titulo_snapshot = models.CharField(
        max_length=200, blank=True, default='', verbose_name='Título da tabela CMS (snapshot)'
    )
    taxa_recebido_snapshot = models.DecimalField(
        max_digits=7, decimal_places=4, blank=True, null=True, verbose_name='Taxa recebido (snapshot)'
    )
    taxa_repasse_snapshot = models.DecimalField(
        max_digits=7, decimal_places=4, blank=True, null=True, verbose_name='Taxa repasse (snapshot)'
    )
    taxa_plastico_snapshot = models.DecimalField(
        max_digits=7, decimal_places=4, blank=True, null=True, verbose_name='Taxa plástico (snapshot)'
    )
    data_att_cms = models.DateTimeField(blank=True, null=True, verbose_name='Última alteração manual dos percentuais (CMS)')
    user_att_cms = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='contratos_cms_snapshot_editados',
        verbose_name='Usuário da última alteração CMS (contrato)',
    )
    # Percentual manual (0–100) sobre AF para cálculo de CMS no Relatório Financeiro; não altera AF original.
    percentual_af_manual = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name='Percentual manual sobre AF (financeiro)',
        help_text='Opcional. Quando preenchido, a base para CMS no relatório = AF × (percentual/100).',
    )
    # Base monetária explícita para CMS (financeiro); tem precedência sobre percentual_af_manual.
    valor_af_base_cms = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='AF base para cálculo CMS (financeiro)',
        help_text='Quando preenchido, substitui AF × % na base dos flats; não altera o AF original do contrato.',
    )
    # Override do tier M1/M2/M3 sem alterar o registro da TabelaCms no catálogo.
    classificador_banco_operacional = models.CharField(
        max_length=2,
        choices=TabelaCms.CLASSIFICADOR_BANCO_CHOICES,
        blank=True,
        null=True,
        verbose_name='Classificador banco (override financeiro)',
        help_text='Opcional. Quando preenchido, usado no relatório e sincronizado ao RegisterMoney.',
    )

    class Meta:
        verbose_name = 'Contrato — dados operacionais'
        verbose_name_plural = 'Contratos — dados operacionais'


class TagStatusOperacional(models.Model):
    """Histórico de tags de status operacional por carteira (Simulação, Proposta, Digitação)."""
    TAG_CHOICES = [
        ('AGUARDANDO_SIMULACAO', 'Aguardando Simulação'),
        ('AGUARDANDO_PROPOSTA',  'Aguardando Proposta'),
        ('AGUARDANDO_DIGITACAO', 'Aguardando Digitação'),
        ('EM_DIGITACAO',         'Em Digitação'),
    ]
    carteira_clientes = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.CASCADE,
        related_name='tags_status_operacional',
        verbose_name='Carteira',
    )
    tag = models.CharField(
        max_length=40,
        choices=TAG_CHOICES,
        db_index=True,
        verbose_name='Tag',
    )
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tags_status_operacional_criadas',
        verbose_name='Criado por',
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')

    class Meta:
        verbose_name = 'Tag status operacional'
        verbose_name_plural = 'Tags status operacional'
        ordering = ['-data_criacao']

    def __str__(self):
        return f'{self.get_tag_display()} — carteira {self.carteira_clientes_id}'


class ClienteContatoDinamico(models.Model):
    """Contatos dinâmicos do cliente (celular, telefone fixo, e-mail), múltiplos por cliente."""
    TIPO_CHOICES = [
        ('CELULAR',       'Celular'),
        ('TELEFONE_FIXO', 'Telefone fixo'),
        ('EMAIL',         'E-mail'),
    ]
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='contatos_dinamicos',
        verbose_name='Dados pessoais',
    )
    tipo  = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True, verbose_name='Tipo')
    valor = models.CharField(max_length=255, verbose_name='Valor')

    class Meta:
        verbose_name = 'Cliente — contato (dinâmico)'
        verbose_name_plural = 'Cliente — contatos (dinâmicos)'
        ordering = ['id']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.valor}'


class ClienteEnderecoDinamico(models.Model):
    """Endereços dinâmicos do cliente, múltiplos por cliente com flag de principal."""
    cliente_dados_pessoais = models.ForeignKey(
        ClienteDadosPessoais,
        on_delete=models.CASCADE,
        related_name='enderecos_dinamicos',
        verbose_name='Dados pessoais',
    )
    cep        = models.CharField(max_length=12, blank=True, null=True, verbose_name='CEP')
    logradouro = models.CharField(max_length=255, blank=True, null=True, verbose_name='Logradouro')
    principal  = models.BooleanField(default=False, db_index=True, verbose_name='Endereço principal')

    class Meta:
        verbose_name = 'Cliente — endereço (dinâmico)'
        verbose_name_plural = 'Cliente — endereços (dinâmicos)'
        ordering = ['-principal', 'id']

    def __str__(self):
        flag = ' [principal]' if self.principal else ''
        return f'{self.cep} — {self.logradouro}{flag}'


class Pendencia(models.Model):
    """Pendência tipada criada pelo operacional/supervisor no fluxo do contrato.

    Substitui o modelo informal anterior (apenas estado transitório em
    `ContratoExecucao.pendencia_etapa_origem/sub_origem`). Uma pendência tem:
    tipo (dados cliente / dados proposta / falta arquivo), observação obrigatória,
    autor, e ciclo aberta/resolvida. O modal do consultor lista APENAS os tipos
    marcados, com permissões restritas (editar campos / anexar arquivos; nunca
    excluir arquivos existentes; campos obrigatórios não podem ser zerados).
    """

    TIPO_DADOS_CLIENTE = 'DADOS_CLIENTE'
    TIPO_DADOS_PROPOSTA = 'DADOS_PROPOSTA'
    TIPO_FALTA_ARQUIVO = 'FALTA_ARQUIVO'
    TIPO_CHOICES = (
        (TIPO_DADOS_CLIENTE, 'Dados do Cliente'),
        (TIPO_DADOS_PROPOSTA, 'Dados da Proposta'),
        (TIPO_FALTA_ARQUIVO, 'Falta de Arquivo'),
    )

    contrato_execucao = models.ForeignKey(
        'ContratoExecucao',
        on_delete=models.CASCADE,
        related_name='pendencias',
        verbose_name='Contrato',
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True, verbose_name='Tipo')
    observacao = models.TextField(verbose_name='Observação (obrigatória)')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pendencias_criadas',
        verbose_name='Criado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')
    resolvido_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pendencias_resolvidas',
        blank=True, null=True,
        verbose_name='Resolvido por',
    )
    resolvido_em = models.DateTimeField(blank=True, null=True, verbose_name='Resolvido em')
    resolvido = models.BooleanField(default=False, db_index=True, verbose_name='Resolvido')

    class Meta:
        verbose_name = 'Pendência (contrato)'
        verbose_name_plural = 'Pendências (contratos)'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['contrato_execucao', 'resolvido']),
            models.Index(fields=['tipo', 'resolvido']),
        ]

    def __str__(self):
        return f'Pendência {self.get_tipo_display()} — contrato #{self.contrato_execucao_id}'


class EnvioComprovantePagamentoVendedor(models.Model):
    """Anexo enviado pelo vendedor (somente título + arquivo); sem valor monetário.

    Valores e transição de status ficam com o operacional (ComprovanteTC / esteira).
    """

    contrato_execucao = models.ForeignKey(
        'ContratoExecucao',
        on_delete=models.CASCADE,
        related_name='envios_comprovante_pagamento_vendedor',
        verbose_name='Contrato',
    )
    titulo = models.CharField(max_length=255, verbose_name='Título')
    arquivo = models.FileField(
        upload_to='contratos/comprovantes_pagamento_vendedor/%Y/%m/',
        verbose_name='Arquivo',
    )
    enviado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='envios_comprovante_pagamento_contrato',
        verbose_name='Enviado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Envio de comprovante (vendedor)'
        verbose_name_plural = 'Envios de comprovantes (vendedor)'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['contrato_execucao', '-criado_em']),
        ]

    def __str__(self):
        return f'Envio #{self.pk} — contrato #{self.contrato_execucao_id} — {self.titulo}'


class ComprovanteTC(models.Model):
    """Comprovantes de pagamento de TC (parcial ou total).

    O status Parcial/Total do contrato é definido pela SOMA dos comprovantes
    vs. valor_tc do contrato:
      - soma < valor_tc → PG_PAGO_TC_PARCIAL
      - soma >= valor_tc → PG_PAGO_TC_TOTAL
    A cada novo comprovante o RegisterMoney é incrementado (acumulado)
    preservando a classificação M1/M2/M3 do PRIMEIRO pagamento.
    """

    contrato_execucao = models.ForeignKey(
        'ContratoExecucao',
        on_delete=models.CASCADE,
        related_name='comprovantes_tc',
        verbose_name='Contrato',
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Valor pago (TC)')
    arquivo = models.FileField(upload_to='contratos/comprovantes_tc/%Y/%m/', verbose_name='Arquivo')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='comprovantes_tc_criados',
        verbose_name='Criado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')
    status = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Comprovante TC'
        verbose_name_plural = 'Comprovantes TC'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Comprovante TC R$ {self.valor} — contrato #{self.contrato_execucao_id}'


class HistoricoTransacaoSimulacao(models.Model):
    """Log técnico de transações da solicitação/simulação (uso interno — superuser/admin)."""

    ACAO_CRIACAO = 'CRIACAO'
    ACAO_TRANSICAO = 'TRANSICAO'
    ACAO_RESPOSTA = 'RESPOSTA_PROPOSTAS'
    ACAO_INELEGIVEL = 'INELEGIVEL'
    ACAO_TABULACAO = 'TABULACAO'
    ACAO_CHOICES = (
        (ACAO_CRIACAO, 'Criação'),
        (ACAO_TRANSICAO, 'Transição de estado'),
        (ACAO_RESPOSTA, 'Resposta com propostas'),
        (ACAO_INELEGIVEL, 'Inelegível'),
        (ACAO_TABULACAO, 'Tabulação comercial'),
    )

    correlacao_id = models.UUIDField(db_index=True, editable=False, verbose_name='ID de correlação')
    solicitacao = models.ForeignKey(
        SolicitacaoPropostaCliente,
        on_delete=models.CASCADE,
        related_name='historico_transacoes_tecnicas',
        verbose_name='Solicitação',
    )
    carteira_clientes = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_simulacao',
        verbose_name='Carteira',
    )
    acao = models.CharField(max_length=40, choices=ACAO_CHOICES, db_index=True, verbose_name='Ação')
    estado_anterior = models.CharField(max_length=40, blank=True, default='', verbose_name='Estado anterior')
    estado_novo = models.CharField(max_length=40, blank=True, default='', verbose_name='Estado novo')
    payload = models.JSONField(default=dict, blank=True, verbose_name='Payload técnico')
    proposta_vinculada = models.ForeignKey(
        PropostaDados,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_simulacao',
        verbose_name='Proposta vinculada',
    )
    historico_evento = models.ForeignKey(
        HistoricoEventoSimulacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacao_tecnica',
        verbose_name='Evento linha do tempo',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacao_simulacao',
        verbose_name='Usuário',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')

    class Meta:
        verbose_name = 'Histórico transação (simulação)'
        verbose_name_plural = 'Históricos transação (simulação)'
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['solicitacao', '-data_hora']),
            models.Index(fields=['acao', '-data_hora']),
        ]

    def __str__(self):
        return f'{self.acao} — solicitação #{self.solicitacao_id}'


class HistoricoTransacaoProposta(models.Model):
    """Log técnico de transações de proposta operacional (uso interno)."""

    ACAO_CRIACAO = 'CRIACAO'
    ACAO_EDICAO = 'EDICAO'
    ACAO_ACEITE = 'ACEITE_CLIENTE'
    ACAO_ENVIO_DIGITACAO = 'ENVIO_DIGITACAO'
    ACAO_TABULACAO = 'TABULACAO'
    ACAO_CHOICES = (
        (ACAO_CRIACAO, 'Criação'),
        (ACAO_EDICAO, 'Edição'),
        (ACAO_ACEITE, 'Aceite pelo cliente'),
        (ACAO_ENVIO_DIGITACAO, 'Envio para digitação'),
        (ACAO_TABULACAO, 'Tabulação comercial'),
    )

    correlacao_id = models.UUIDField(db_index=True, editable=False, verbose_name='ID de correlação')
    proposta = models.ForeignKey(
        PropostaDados,
        on_delete=models.CASCADE,
        related_name='historico_transacoes_tecnicas',
        verbose_name='Proposta',
    )
    solicitacao_origem = models.ForeignKey(
        SolicitacaoPropostaCliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_proposta',
        verbose_name='Simulação origem',
    )
    carteira_clientes = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_proposta',
        verbose_name='Carteira',
    )
    acao = models.CharField(max_length=40, choices=ACAO_CHOICES, db_index=True, verbose_name='Ação')
    payload = models.JSONField(default=dict, blank=True, verbose_name='Payload técnico')
    contrato_vinculado = models.ForeignKey(
        ContratoExecucao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_proposta',
        verbose_name='Contrato vinculado',
    )
    historico_digitacao = models.ForeignKey(
        HistoricoEventoDigitacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacao_tecnica_proposta',
        verbose_name='Evento digitação',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacao_proposta',
        verbose_name='Usuário',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')

    class Meta:
        verbose_name = 'Histórico transação (proposta)'
        verbose_name_plural = 'Históricos transação (proposta)'
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['proposta', '-data_hora']),
            models.Index(fields=['acao', '-data_hora']),
        ]

    def __str__(self):
        return f'{self.acao} — proposta #{self.proposta_id}'


class HistoricoTransacaoContrato(models.Model):
    """Log técnico de transações de contrato (uso interno — dashboard e auditoria)."""

    ACAO_CRIACAO = 'CRIACAO'
    ACAO_TRANSICAO = 'TRANSICAO'
    ACAO_EDICAO = 'EDICAO'
    ACAO_TABULACAO = 'TABULACAO'
    ACAO_ENTRADA_PENDENCIAS = 'ENTRADA_PENDENCIAS'
    ACAO_PENDENCIA_ABERTA = 'PENDENCIA_ABERTA'
    ACAO_PENDENCIA_RESOLVIDA = 'PENDENCIA_RESOLVIDA'
    ACAO_CHOICES = (
        (ACAO_CRIACAO, 'Criação'),
        (ACAO_TRANSICAO, 'Transição de etapa'),
        (ACAO_EDICAO, 'Edição de dados'),
        (ACAO_TABULACAO, 'Tabulação'),
        (ACAO_ENTRADA_PENDENCIAS, 'Entrada em pendências'),
        (ACAO_PENDENCIA_ABERTA, 'Pendência aberta'),
        (ACAO_PENDENCIA_RESOLVIDA, 'Pendência resolvida'),
    )

    correlacao_id = models.UUIDField(db_index=True, editable=False, verbose_name='ID de correlação')
    contrato = models.ForeignKey(
        ContratoExecucao,
        on_delete=models.CASCADE,
        related_name='historico_transacoes_tecnicas',
        verbose_name='Contrato',
    )
    proposta_origem = models.ForeignKey(
        PropostaDados,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_contrato',
        verbose_name='Proposta origem',
    )
    solicitacao_digitacao = models.ForeignKey(
        SolicitacaoDigitacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_contrato',
        verbose_name='Solicitação digitação',
    )
    carteira_clientes = models.ForeignKey(
        'siape.CarteiraClientes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes_contrato',
        verbose_name='Carteira',
    )
    acao = models.CharField(max_length=40, choices=ACAO_CHOICES, db_index=True, verbose_name='Ação')
    etapa_anterior = models.CharField(max_length=20, blank=True, default='', verbose_name='Etapa anterior')
    sub_anterior = models.CharField(max_length=40, blank=True, default='', verbose_name='Sub anterior')
    etapa_nova = models.CharField(max_length=20, blank=True, default='', verbose_name='Etapa nova')
    sub_nova = models.CharField(max_length=40, blank=True, default='', verbose_name='Sub nova')
    payload = models.JSONField(default=dict, blank=True, verbose_name='Payload técnico')
    pendencia = models.ForeignKey(
        'Pendencia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacoes',
        verbose_name='Pendência',
    )
    historico_transicao = models.ForeignKey(
        HistoricoTransicaoContrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacao_tecnica',
        verbose_name='Transição linha do tempo',
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_transacao_contrato',
        verbose_name='Usuário',
    )
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')

    class Meta:
        verbose_name = 'Histórico transação (contrato)'
        verbose_name_plural = 'Históricos transação (contrato)'
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['contrato', '-data_hora']),
            models.Index(fields=['acao', '-data_hora']),
            models.Index(fields=['-data_hora', 'acao']),
        ]

    def __str__(self):
        return f'{self.acao} — contrato #{self.contrato_id}'
