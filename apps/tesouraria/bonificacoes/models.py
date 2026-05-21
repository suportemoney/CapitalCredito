from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

class TipoRegraChoices(models.TextChoices):
    PERCENTUAL = 'percentual', 'Percentual Simples'
    GATILHO_PERCENTUAL = 'gatilho_percentual', 'Gatilho + Percentual'
    GATILHO_VALOR_FIXO = 'gatilho_valor_fixo', 'Gatilho + Valor Fixo'

class CampoValorChoices(models.TextChoices):
    VALOR_AF = 'valor_af', 'Valor AF'
    VALOR_REPASSE = 'valor_repasse', 'Valor Repasse'

class BonificacaoRegra(models.Model):
    nome = models.CharField(max_length=120, verbose_name="Nome da Regra")
    tipo_regra = models.CharField(max_length=50, choices=TipoRegraChoices.choices, verbose_name="Tipo de Regra")
    campo_valor = models.CharField(max_length=20, choices=CampoValorChoices.choices, default=CampoValorChoices.VALOR_REPASSE, verbose_name="Campo de Valor")
    percentual_padrao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Percentual Padrão (%)",
        help_text="Usado apenas quando a regra é Percentual sem gatilho")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def clean(self):
        if self.tipo_regra == TipoRegraChoices.PERCENTUAL and not self.percentual_padrao:
            raise ValidationError({'percentual_padrao': 'Percentual padrão é obrigatório para regras do tipo Percentual Simples.'})
        if self.tipo_regra in [TipoRegraChoices.GATILHO_PERCENTUAL, TipoRegraChoices.GATILHO_VALOR_FIXO] and self.percentual_padrao:
            raise ValidationError({'percentual_padrao': 'Percentual padrão não deve ser preenchido para regras com gatilho.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_regra_display()})"

    class Meta:
        verbose_name = "Regra de Bonificação"
        verbose_name_plural = "Regras de Bonificação"
        ordering = ['-ativo', '-data_criacao', 'nome']

class BonificacaoGatilho(models.Model):
    regra = models.ForeignKey(BonificacaoRegra, on_delete=models.CASCADE, related_name='gatilhos', verbose_name="Regra")
    valor_minimo = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Valor Mínimo",
        help_text="Valor mínimo da faixa para ativar este gatilho")
    valor_fixo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, verbose_name="Valor Fixo (R$)",
        help_text="Usado apenas para regras do tipo Gatilho + Valor Fixo")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Percentual (%)",
        help_text="Usado apenas para regras do tipo Gatilho + Percentual")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    def clean(self):
        if self.valor_minimo < 0:
            raise ValidationError({'valor_minimo': 'O valor mínimo não pode ser negativo.'})
        if self.regra.tipo_regra == TipoRegraChoices.GATILHO_PERCENTUAL:
            if not self.percentual:
                raise ValidationError({'percentual': 'Percentual é obrigatório para regras do tipo Gatilho + Percentual.'})
            if self.valor_fixo:
                raise ValidationError({'valor_fixo': 'Valor fixo não deve ser preenchido para regras do tipo Gatilho + Percentual.'})
        elif self.regra.tipo_regra == TipoRegraChoices.GATILHO_VALOR_FIXO:
            if not self.valor_fixo:
                raise ValidationError({'valor_fixo': 'Valor fixo é obrigatório para regras do tipo Gatilho + Valor Fixo.'})
            if self.percentual:
                raise ValidationError({'percentual': 'Percentual não deve ser preenchido para regras do tipo Gatilho + Valor Fixo.'})
        q = BonificacaoGatilho.objects.filter(regra=self.regra, valor_minimo=self.valor_minimo)
        if self.pk:
            q = q.exclude(pk=self.pk)
        if q.exists():
            raise ValidationError({'valor_minimo': 'Já existe gatilho com este valor mínimo nesta regra.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        tipo_valor = f"{self.percentual}%" if self.percentual else f"R$ {self.valor_fixo}"
        return f"{self.regra.nome} - ≥ R$ {self.valor_minimo} → {tipo_valor}"

    class Meta:
        verbose_name = "Gatilho de Bonificação"
        verbose_name_plural = "Gatilhos de Bonificação"
        ordering = ['valor_minimo']

class BonificacaoFuncionarioRegra(models.Model):
    funcionario = models.ForeignKey('funcionarios.Funcionario', on_delete=models.CASCADE, related_name='regras_bonificacao', verbose_name="Funcionário")
    regra = models.ForeignKey(BonificacaoRegra, on_delete=models.CASCADE, related_name='funcionarios', verbose_name="Regra")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_inicio = models.DateField(null=True, blank=True, verbose_name="Data de Início")
    data_fim = models.DateField(null=True, blank=True, verbose_name="Data de Fim")
    prioridade = models.PositiveIntegerField(default=0, verbose_name="Prioridade",
        help_text="Maior prioridade = primeiro na ordem de aplicação (1º)")

    def clean(self):
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'A data de fim não pode ser anterior à data de início.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.funcionario.nome_completo} → {self.regra.nome}"

    class Meta:
        verbose_name = "Vínculo Funcionário-Regra"
        verbose_name_plural = "Vínculos Funcionário-Regra"
        unique_together = ['funcionario', 'regra']
        ordering = ['-prioridade', 'regra__nome']

class ReducaoBonificacaoRegra(models.Model):
    titulo = models.CharField(max_length=120, verbose_name="Título")
    percentual = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Percentual de Redução (%)",
        help_text="Ex: 20 = reduzir 20% do valor atual")
    ordem = models.PositiveIntegerField(default=1, verbose_name="Ordem")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def clean(self):
        if self.percentual < 0:
            raise ValidationError({'percentual': 'O percentual não pode ser negativo.'})
        if self.percentual > 100:
            raise ValidationError({'percentual': 'O percentual não pode ser maior que 100%.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ordem}. {self.titulo} (-{self.percentual}%)"

    class Meta:
        verbose_name = "Regra de Redução (Bonificação)"
        verbose_name_plural = "Regras de Redução (Bonificação)"
        ordering = ['ordem', 'titulo']

class ReducaoBonificacaoFuncionario(models.Model):
    funcionario = models.ForeignKey('funcionarios.Funcionario', on_delete=models.CASCADE, related_name='reducoes_bonificacao', verbose_name="Funcionário")
    regra_reducao = models.ForeignKey(ReducaoBonificacaoRegra, on_delete=models.PROTECT, related_name='lancamentos', verbose_name="Regra de Redução")
    data_evento = models.DateField(verbose_name="Data do Evento",
        help_text="Data em que a ocorrência aconteceu (usado para filtrar no período)")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.regra_reducao} ({self.data_evento})"

    class Meta:
        verbose_name = "Redução aplicada ao Funcionário"
        verbose_name_plural = "Reduções aplicadas aos Funcionários"
        ordering = ['regra_reducao__ordem', 'data_criacao']
        indexes = [
            models.Index(fields=['funcionario', 'data_evento']),
            models.Index(fields=['regra_reducao', 'data_criacao']),
        ]

class BonificacaoCalculada(models.Model):
    funcionario = models.ForeignKey('funcionarios.Funcionario', on_delete=models.CASCADE, related_name='bonificacoes_calculadas', verbose_name="Funcionário")
    regra = models.ForeignKey(BonificacaoRegra, on_delete=models.PROTECT, related_name='calculos', verbose_name="Regra")
    periodo_inicio = models.DateField(verbose_name="Período Início")
    periodo_fim = models.DateField(verbose_name="Período Fim")
    valor_base = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Valor Base",
        help_text="Valor total encontrado no período")
    valor_bonificacao = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Valor da Bonificação")
    valor_bonificacao_final = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, verbose_name="Valor da Bonificação (Final)",
        help_text="Valor da bonificação após aplicar reduções (se houver)")
    reducoes_aplicadas = models.JSONField(null=True, blank=True, verbose_name="Reduções Aplicadas (JSON)")
    gatilho_aplicado = models.ForeignKey(BonificacaoGatilho, on_delete=models.SET_NULL, null=True, blank=True, related_name='calculos_aplicados', verbose_name="Gatilho Aplicado")
    data_calculo = models.DateTimeField(auto_now_add=True, verbose_name="Data do Cálculo")

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.regra.nome} - {self.periodo_inicio} a {self.periodo_fim}"

    class Meta:
        verbose_name = "Bonificação Calculada"
        verbose_name_plural = "Bonificações Calculadas"
        ordering = ['-data_calculo']
        indexes = [
            models.Index(fields=['funcionario', 'periodo_inicio', 'periodo_fim']),
            models.Index(fields=['regra', 'data_calculo']),
        ]
