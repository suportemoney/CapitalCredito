import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .models import Equipe, StatusChoice


TIPO_CLIENTE_CHOICES = (
    ('SIAPE', 'SIAPE'),
    ('OUTROS', 'Outros'),
)

TIPO_CAMPANHA_CHOICES = (
    ('SIAPE', 'SIAPE'),
    ('OUTROS', 'Outros'),
    ('MISTA', 'Mista'),
)


def normalizar_cpf(cpf: str) -> str:
    """Remove máscara e garante 11 dígitos."""
    digitos = re.sub(r'\D', '', cpf or '')
    if not digitos:
        return ''
    return digitos.zfill(11)[-11:]


class CampanhaV2(models.Model):
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=True)
    tipo_campanha = models.CharField(max_length=10, choices=TIPO_CAMPANHA_CHOICES, default='MISTA')
    equipes = models.ManyToManyField(Equipe, blank=True, related_name='campanhas_v2')
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Campanha Plus'
        verbose_name_plural = 'Campanhas Plus'
        ordering = ['-data_criacao']

    def __str__(self):
        return self.nome


class ClienteCampanhaV2(models.Model):
    campanha = models.ForeignKey(
        CampanhaV2,
        on_delete=models.CASCADE,
        related_name='clientes',
    )
    cpf = models.CharField(max_length=11, db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CLIENTE_CHOICES)
    dados_json = models.JSONField(null=True, blank=True, default=None)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente Campanha Plus'
        verbose_name_plural = 'Clientes Campanha Plus'
        unique_together = ('campanha', 'cpf')
        ordering = ['cpf']

    def clean(self):
        self.cpf = normalizar_cpf(self.cpf)
        if not self.cpf or len(self.cpf) != 11:
            raise ValidationError({'cpf': 'CPF inválido.'})
        if self.tipo == 'SIAPE' and self.dados_json:
            raise ValidationError({'dados_json': 'SIAPE não deve persistir dados_json.'})

    def save(self, *args, **kwargs):
        self.cpf = normalizar_cpf(self.cpf)
        if self.tipo == 'SIAPE':
            self.dados_json = None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.cpf} ({self.tipo}) — {self.campanha.nome}'


class ControleClienteV2(models.Model):
    campanha = models.ForeignKey(
        CampanhaV2,
        on_delete=models.CASCADE,
        related_name='controles',
    )
    cliente = models.ForeignKey(
        ClienteCampanhaV2,
        on_delete=models.CASCADE,
        related_name='controles',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='plus_controles_v2',
    )
    tabulacao = models.ForeignKey(
        StatusChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plus_controles_v2',
    )
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Controle Cliente Plus'
        verbose_name_plural = 'Controles Cliente Plus'
        unique_together = ('campanha', 'cliente', 'user')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.cliente.cpf} → {self.user.username}'


class AgendamentoV2(models.Model):
    STATUS_EM_ESPERA = 'EM_ESPERA'
    STATUS_REALIZADO = 'REALIZADO'
    STATUS_INATIVO = 'INATIVO'

    STATUS_CHOICES = [
        (STATUS_EM_ESPERA, 'Em Espera'),
        (STATUS_REALIZADO, 'Realizado'),
        (STATUS_INATIVO, 'Inativo'),
    ]

    controle = models.ForeignKey(
        ControleClienteV2,
        on_delete=models.CASCADE,
        related_name='agendamentos',
    )
    dia_agendamento = models.DateField()
    hora = models.TimeField()
    responsavel = models.CharField(max_length=255)
    observacao = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_EM_ESPERA)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Agendamento Plus'
        verbose_name_plural = 'Agendamentos Plus'
        ordering = ['-dia_agendamento', 'hora']

    def __str__(self):
        return f'{self.controle.cliente.cpf} — {self.dia_agendamento}'


class ImportacaoCsvV2(models.Model):
    campanha = models.ForeignKey(
        CampanhaV2,
        on_delete=models.CASCADE,
        related_name='importacoes',
    )
    colunas_schema = models.JSONField(default=list)
    arquivo_nome = models.CharField(max_length=255)
    total_linhas = models.PositiveIntegerField(default=0)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='plus_importacoes_csv_v2',
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Importação CSV Plus'
        verbose_name_plural = 'Importações CSV Plus'
        ordering = ['-data_criacao']

    def __str__(self):
        return f'{self.arquivo_nome} ({self.total_linhas} linhas)'
