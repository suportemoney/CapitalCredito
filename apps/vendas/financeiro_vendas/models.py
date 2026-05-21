from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import re

class Classificador(models.Model):
    """Classificadores para cálculo de repasse"""
    titulo = models.CharField(max_length=255, unique=True, verbose_name="Título")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Percentual (%)", help_text="Percentual de 0 a 100")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper() if self.titulo else None
        if self.percentual < 0:
            self.percentual = 0
        if self.percentual > 100:
            self.percentual = 100
        super(Classificador, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.titulo} ({self.percentual}%)"
    
    class Meta:
        verbose_name = "Classificador"
        verbose_name_plural = "Classificadores"
        ordering = ['titulo']

class ContratoPagamento(models.Model):
    """Contratos de pagamento do financeiro de vendas"""
    STATUS_CHOICES = [
        ('A_PAGAR', 'A Pagar'),
        ('PAGO', 'Pago'),
        ('NAO_PAGO', 'Não Pago'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='contratos_pagamento', verbose_name="Vendedor")
    setor = models.ForeignKey('rh_admin.Setor', on_delete=models.PROTECT, related_name='contratos_pagamento', verbose_name="Setor")
    cliente_cpf = models.CharField(max_length=14, verbose_name="CPF do Cliente")
    cliente_nome = models.CharField(max_length=255, verbose_name="Nome do Cliente")
    produto = models.ForeignKey('siape.Produto', on_delete=models.PROTECT, related_name='contratos_pagamento', verbose_name="Produto")
    banco = models.CharField(max_length=255, verbose_name="Banco")
    valor_af = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor AF (R$)")
    valor_repasse = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor Repasse (R$)")
    flg_ponta = models.BooleanField(default=False, verbose_name="Ponta", help_text="Marcado se NÃO for contrato novo/ponta")
    classificador = models.ForeignKey(Classificador, on_delete=models.PROTECT, related_name='contratos_pagamento', verbose_name="Classificador")
    data_contrato = models.DateField(verbose_name="Data do Contrato")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='A_PAGAR', verbose_name="Status")
    data_pagamento = models.DateField(blank=True, null=True, verbose_name="Data de Pagamento")
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    def save(self, *args, **kwargs):
        self.cliente_cpf = re.sub(r'\D', '', self.cliente_cpf) if self.cliente_cpf else ''
        self.cliente_nome = self.cliente_nome.upper() if self.cliente_nome else None
        self.banco = self.banco.upper() if self.banco else None
        if self.status == 'PAGO' and not self.data_pagamento:
            self.data_pagamento = timezone.now().date()
        super(ContratoPagamento, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.cliente_nome} - {self.produto.nome} - R$ {self.valor_af}"
    
    class Meta:
        verbose_name = "Contrato de Pagamento"
        verbose_name_plural = "Contratos de Pagamento"
        ordering = ['-data_contrato', '-data_criacao']
        indexes = [
            models.Index(fields=['cliente_cpf']),
            models.Index(fields=['status', 'status_ativo']),
            models.Index(fields=['user', 'status']),
        ]
