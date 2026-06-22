from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class StatusChoice(models.Model):
    IMPACTO_CHOICES = (
        ('NEGATIVO', 'Negativo'),
        ('POSITIVO', 'Positivo'),
    )

    COMPORTAMENTO_CHOICES = (
        ('REPETIR', 'Repetir - Pode ser entregue a outro user'),
        ('NAO_ENTREGAR_MAIS', 'Não entregar mais o cliente - Nessa ou em qualquer campanha'),
        ('NAO_ENTREGAR_CAMPANHA', 'Não entregar mais o cliente nessa campanha - Se o CPF aparecer em campanha diferente pode ser chamado'),
    )

    nome = models.CharField(max_length=50, unique=True)
    cor_tag = models.CharField(max_length=6, default='6c757d', help_text='Cor de identificação em formato hexadecimal (sem #)')
    impacto = models.CharField(max_length=10, choices=IMPACTO_CHOICES, default='NEGATIVO')
    comportamento = models.CharField(max_length=30, choices=COMPORTAMENTO_CHOICES, default='REPETIR')
    conversao = models.BooleanField(default=False, help_text='Cliente de sucesso - tabulação positiva')
    cpc = models.BooleanField(default=False, help_text='Contato com cliente certo - número estava correto')
    oportunidade = models.BooleanField(default=False, help_text='Cliente em potencial - ainda não chegou a acordo mas é faturavel')
    data_criacao = models.DateTimeField(auto_now_add=True)
    status_booleano = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text='Ordem de evolução (0 = primeiro, maior = depois)')

    class Meta:
        verbose_name = 'Status Choice'
        verbose_name_plural = 'Status Choices'
        ordering = ['order', 'nome']

    def __str__(self):
        return self.nome


class Equipe(models.Model):
    nome = models.CharField(max_length=255)
    participantes = models.ManyToManyField(User, blank=True, related_name='equipes_plus')
    status = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Equipe Plus'
        verbose_name_plural = 'Equipes Plus'

    def __str__(self):
        return self.nome
