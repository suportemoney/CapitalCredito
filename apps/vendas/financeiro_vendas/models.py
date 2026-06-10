from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
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
    valor_tc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Valor TC (R$)",
        help_text="Meta de TC a pagar",
    )
    valor_tc_acumulado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="TC pago acumulado (R$)",
    )
    flg_ponta = models.BooleanField(default=False, verbose_name="Ponta", help_text="Marcado se NÃO for contrato novo/ponta")
    flag_repasse = models.BooleanField(default=False, verbose_name="Linha de repasse")
    classificador = models.ForeignKey(Classificador, on_delete=models.PROTECT, related_name='contratos_pagamento', verbose_name="Classificador")
    data_contrato = models.DateField(verbose_name="Data do Contrato")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='A_PAGAR', verbose_name="Status")
    data_pagamento = models.DateField(blank=True, null=True, verbose_name="Data de Pagamento")
    contrato_execucao = models.ForeignKey(
        'contratos_v2.ContratoExecucao',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='contratos_pagamento_financeiro',
        verbose_name="Contrato operacional (v2)",
    )
    status_ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def recalcular_tc_acumulado(self, save=True):
        """Recalcula valor_tc_acumulado e status a partir dos comprovantes ativos."""
        agg = self.comprovantes_tc.filter(status=True).aggregate(total=Sum('valor'))
        total = agg['total'] or Decimal('0')
        self.valor_tc_acumulado = total

        ultimo = (
            self.comprovantes_tc.filter(status=True)
            .order_by('-criado_em')
            .first()
        )
        if ultimo and ultimo.criado_em:
            self.data_pagamento = ultimo.criado_em.date()

        valor_meta = self.valor_tc or Decimal('0')
        if valor_meta > 0 and total >= valor_meta:
            self.status = 'PAGO'
        elif total > 0 and self.status == 'PAGO' and total < valor_meta:
            self.status = 'A_PAGAR'

        if save:
            self.save(update_fields=['valor_tc_acumulado', 'status', 'data_pagamento', 'data_atualizacao'])

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
            models.Index(fields=['contrato_execucao', 'user']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['contrato_execucao', 'user'],
                condition=models.Q(contrato_execucao__isnull=False),
                name='financeiro_cp_unique_ce_user',
            ),
        ]


class ComprovanteTC(models.Model):
    """Comprovantes de pagamento TC vinculados ao registro de ranking (financeiro vendas)."""

    contrato_pagamento = models.ForeignKey(
        ContratoPagamento,
        on_delete=models.CASCADE,
        related_name='comprovantes_tc',
        verbose_name='Contrato pagamento',
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Valor pago (TC)')
    arquivo = models.FileField(upload_to='financeiro_vendas/comprovantes_tc/%Y/%m/', verbose_name='Arquivo')
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='comprovantes_tc_financeiro_criados',
        verbose_name='Criado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')
    status = models.BooleanField(default=True, verbose_name='Ativo')
    comprovante_v2_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name='ID comprovante contratos_v2',
        help_text='Espelho do ComprovanteTC em contratos_v2 (idempotência na sync)',
    )

    class Meta:
        verbose_name = 'Comprovante TC'
        verbose_name_plural = 'Comprovantes TC'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(
                fields=['comprovante_v2_id', 'contrato_pagamento'],
                condition=models.Q(comprovante_v2_id__isnull=False),
                name='financeiro_comp_tc_unique_v2_cp',
            ),
        ]

    def __str__(self):
        return f'Comprovante TC R$ {self.valor} — contrato pagamento #{self.contrato_pagamento_id}'
