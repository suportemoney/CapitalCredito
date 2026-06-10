from django.db import models
from django.utils import timezone

class CategoriaConta(models.Model):
    """Categorias para contas (gastos da empresa)."""
    nome = models.CharField(max_length=255, verbose_name="Nome")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        super(CategoriaConta, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome or ''

    class Meta:
        verbose_name = "Categoria de Conta"
        verbose_name_plural = "Categorias de Contas"
        ordering = ['nome']

class SubcategoriaConta(models.Model):
    """Subcategorias vinculadas a uma categoria de conta."""
    categoria = models.ForeignKey(CategoriaConta, on_delete=models.CASCADE, related_name='subcategorias', verbose_name="Categoria")
    nome = models.CharField(max_length=255, verbose_name="Nome")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        super(SubcategoriaConta, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.categoria.nome})"

    class Meta:
        verbose_name = "Subcategoria de Conta"
        verbose_name_plural = "Subcategorias de Contas"
        ordering = ['categoria', 'nome']

class TipoBeneficio(models.Model):
    """Tipos de benefício (Vale Transporte, Vale Refeição, etc.)."""
    nome = models.CharField(max_length=255, verbose_name="Nome")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        super(TipoBeneficio, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome or ''

    class Meta:
        verbose_name = "Tipo de Benefício"
        verbose_name_plural = "Tipos de Benefícios"
        ordering = ['nome']

class Conta(models.Model):
    """Contas da empresa (gastos) - vinculadas a categoria/subcategoria."""
    descricao = models.CharField(max_length=500, verbose_name="Descrição")
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor (R$)")
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    data_pagamento = models.DateField(blank=True, null=True, verbose_name="Data de Pagamento")
    pago = models.BooleanField(default=False, verbose_name="Pago")
    categoria = models.ForeignKey(CategoriaConta, on_delete=models.PROTECT, related_name='contas', verbose_name="Categoria")
    subcategoria = models.ForeignKey(SubcategoriaConta, on_delete=models.PROTECT, related_name='contas', null=True, blank=True, verbose_name="Subcategoria")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    anexo = models.FileField(upload_to='tesouraria/anexos/%Y/%m/', blank=True, null=True, verbose_name="Anexo geral")
    comprovante = models.FileField(upload_to='tesouraria/comprovantes/%Y/%m/', blank=True, null=True, verbose_name="Comprovante de pagamento")
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def save(self, *args, **kwargs):
        if self.pago and not self.data_pagamento:
            self.data_pagamento = timezone.now().date()
        if self.descricao:
            self.descricao = self.descricao.upper()
        super(Conta, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"

    class Meta:
        verbose_name = "Conta (empresa)"
        verbose_name_plural = "Contas (empresa)"
        ordering = ['-data_vencimento', '-data_criacao']

class Salario(models.Model):
    """Salários - vinculados a funcionário (ativo ou inativo)."""
    descricao = models.CharField(max_length=500, verbose_name="Descrição")
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor (R$)")
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    data_pagamento = models.DateField(blank=True, null=True, verbose_name="Data de Pagamento")
    pago = models.BooleanField(default=False, verbose_name="Pago")
    funcionario = models.ForeignKey('funcionarios.Funcionario', on_delete=models.PROTECT, related_name='salarios_tesouraria', verbose_name="Funcionário")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    anexo = models.FileField(upload_to='tesouraria/anexos/%Y/%m/', blank=True, null=True, verbose_name="Anexo geral")
    comprovante = models.FileField(upload_to='tesouraria/comprovantes/%Y/%m/', blank=True, null=True, verbose_name="Comprovante de pagamento")
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def save(self, *args, **kwargs):
        if self.pago and not self.data_pagamento:
            self.data_pagamento = timezone.now().date()
        if self.descricao:
            self.descricao = self.descricao.upper()
        super(Salario, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.descricao} - R$ {self.valor}"

    class Meta:
        verbose_name = "Salário"
        verbose_name_plural = "Salários"
        ordering = ['-data_vencimento', '-data_criacao']

class Beneficio(models.Model):
    """Benefícios (Vale Transporte, Refeição, etc.) - vinculados a funcionário e tipo de benefício."""
    descricao = models.CharField(max_length=500, verbose_name="Descrição")
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor (R$)")
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    data_pagamento = models.DateField(blank=True, null=True, verbose_name="Data de Pagamento")
    pago = models.BooleanField(default=False, verbose_name="Pago")
    funcionario = models.ForeignKey('funcionarios.Funcionario', on_delete=models.PROTECT, related_name='beneficios_tesouraria', verbose_name="Funcionário")
    tipo_beneficio = models.ForeignKey(TipoBeneficio, on_delete=models.PROTECT, related_name='beneficios', verbose_name="Tipo de Benefício")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    anexo = models.FileField(upload_to='tesouraria/anexos/%Y/%m/', blank=True, null=True, verbose_name="Anexo geral")
    comprovante = models.FileField(upload_to='tesouraria/comprovantes/%Y/%m/', blank=True, null=True, verbose_name="Comprovante de pagamento")
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def save(self, *args, **kwargs):
        if self.pago and not self.data_pagamento:
            self.data_pagamento = timezone.now().date()
        if self.descricao:
            self.descricao = self.descricao.upper()
        super(Beneficio, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.tipo_beneficio.nome} - R$ {self.valor}"

    class Meta:
        verbose_name = "Benefício"
        verbose_name_plural = "Benefícios"
        ordering = ['-data_vencimento', '-data_criacao']

class BonificacaoAPagar(models.Model):
    """Bonificação a pagar (lançamento manual)."""
    funcionario = models.ForeignKey('funcionarios.Funcionario', on_delete=models.PROTECT, related_name='bonificacoes_a_pagar', verbose_name="Funcionário")
    valor_bonificacao = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor da Bonificação (R$)")
    mes_referente = models.CharField(max_length=20, verbose_name="Mês Referente")
    chave_pix = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave PIX")
    data_pagamento = models.DateField(blank=True, null=True, verbose_name="Data de Pagamento")
    comprovante = models.FileField(upload_to='tesouraria/comprovantes/%Y/%m/', blank=True, null=True, verbose_name="Comprovante de pagamento")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    status_pagamento = models.BooleanField(default=False, verbose_name="Pago")
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.mes_referente} - R$ {self.valor_bonificacao}"
    class Meta:
        verbose_name = "Bonificação a Pagar"
        verbose_name_plural = "Bonificações a Pagar"
        ordering = ['status_pagamento', '-data_criacao', 'funcionario__nome_completo']

class ContaReceber(models.Model):
    """Contas a receber."""
    descricao = models.CharField(max_length=500, verbose_name="Descrição")
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor (R$)")
    data_prevista = models.DateField(verbose_name="Data Prevista")
    data_recebimento = models.DateField(blank=True, null=True, verbose_name="Data de Recebimento")
    recebido = models.BooleanField(default=False, verbose_name="Recebido")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def save(self, *args, **kwargs):
        if self.recebido and not self.data_recebimento:
            self.data_recebimento = timezone.now().date()
        if self.descricao:
            self.descricao = self.descricao.upper()
        super(ContaReceber, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"

    class Meta:
        verbose_name = "Conta a Receber"
        verbose_name_plural = "Contas a Receber"
        ordering = ['-data_prevista', '-data_criacao']
