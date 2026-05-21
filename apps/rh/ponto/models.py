from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.rh.funcionarios.models import Funcionario, HorarioTrabalho
import os

# --- Configuração de Armazenamento ---

def get_justificativa_upload_path(instance, filename):
    """Define o diretório como 'ponto/justificativas/<funcionario_nome>/<filename>'"""
    if hasattr(instance, 'justificativa') and instance.justificativa and instance.justificativa.funcionario:
        nome_completo = instance.justificativa.funcionario.nome_completo.replace(' ', '_').upper()
        return os.path.join('ponto', 'justificativas', nome_completo, filename)
    return os.path.join('ponto', 'justificativas', 'sem_nome', filename)

# --- Models ---

class RegistroPonto(models.Model):
    TIPO_ENTRADA = 'ENTRADA'
    TIPO_SAIDA = 'SAIDA'
    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SAIDA, 'Saída'),
    ]
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='registros_ponto', verbose_name="Funcionário")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo")
    numero = models.IntegerField(verbose_name="Número", help_text="1 ou 2 - primeira ou segunda entrada/saída")
    data_hora = models.DateTimeField(verbose_name="Data e Hora")
    data = models.DateField(verbose_name="Data", help_text="Apenas a data, para facilitar consultas")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    def clean(self):
        if self.numero not in [1, 2]:
            raise ValidationError({'numero': 'Número deve ser 1 ou 2'})
        if self.tipo not in [self.TIPO_ENTRADA, self.TIPO_SAIDA]:
            raise ValidationError({'tipo': 'Tipo deve ser ENTRADA ou SAIDA'})
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_display()} {self.numero} - {self.data_hora.strftime('%d/%m/%Y %H:%M:%S')}"
    class Meta:
        verbose_name = "Registro de Ponto"
        verbose_name_plural = "Registros de Ponto"
        ordering = ['-data', '-data_hora']
        unique_together = ['funcionario', 'data', 'tipo', 'numero']

class Justificativa(models.Model):
    TIPO_FERIAS = 'FERIAS'
    TIPO_ABONO = 'ABONO'
    TIPO_ATESTADO = 'ATESTADO'
    TIPO_FERIADO = 'FERIADO'
    TIPO_CHOICES = [
        (TIPO_FERIAS, 'Férias'),
        (TIPO_ABONO, 'Abono'),
        (TIPO_ATESTADO, 'Atestado'),
        (TIPO_FERIADO, 'Feriado'),
    ]
    titulo = models.CharField(max_length=255, verbose_name="Título")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='justificativas', null=True, blank=True, verbose_name="Funcionário", help_text="Null para justificativas em lote")
    data_inicio = models.DateField(verbose_name="Data Início")
    data_fim = models.DateField(verbose_name="Data Fim")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='justificativas_criadas', verbose_name="Criado por")
    def clean(self):
        if self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'Data fim não pode ser anterior à data início'})
    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper()
        super(Justificativa, self).save(*args, **kwargs)
    def __str__(self):
        funcionario_nome = self.funcionario.nome_completo if self.funcionario else "Em Lote"
        return f"{self.titulo} - {funcionario_nome} ({self.data_inicio} a {self.data_fim})"
    class Meta:
        verbose_name = "Justificativa"
        verbose_name_plural = "Justificativas"
        ordering = ['-data_criacao']

class JustificativaArquivo(models.Model):
    justificativa = models.ForeignKey(Justificativa, on_delete=models.CASCADE, related_name='arquivos', verbose_name="Justificativa")
    arquivo = models.FileField(upload_to=get_justificativa_upload_path, verbose_name="Arquivo")
    titulo = models.CharField(max_length=255, verbose_name="Título do Arquivo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper()
        super(JustificativaArquivo, self).save(*args, **kwargs)
    def __str__(self):
        return f"{self.titulo} - {self.justificativa.titulo}"
    class Meta:
        verbose_name = "Arquivo de Justificativa"
        verbose_name_plural = "Arquivos de Justificativas"
        ordering = ['-data_criacao']

class ConfiguracaoHorarioFuncionario(models.Model):
    DIAS_SEMANA_CHOICES = [
        ('SEGUNDA', 'Segunda-feira'),
        ('TERCA', 'Terça-feira'),
        ('QUARTA', 'Quarta-feira'),
        ('QUINTA', 'Quinta-feira'),
        ('SEXTA', 'Sexta-feira'),
        ('SABADO', 'Sábado'),
        ('DOMINGO', 'Domingo'),
    ]
    funcionario = models.OneToOneField(Funcionario, on_delete=models.CASCADE, related_name='configuracao_horario', verbose_name="Funcionário")
    horario_trabalho = models.ForeignKey(HorarioTrabalho, on_delete=models.SET_NULL, null=True, blank=True, related_name='configuracoes_funcionarios', verbose_name="Horário de Trabalho Padrão")
    trabalha_fim_semana = models.BooleanField(default=False, verbose_name="Trabalha em Fins de Semana")
    horarios_por_dia = models.JSONField(default=dict, verbose_name="Horários por Dia", help_text="JSON com horários específicos para cada dia da semana")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.horario_trabalho.nome if self.horario_trabalho else 'Horário personalizado'}"
    class Meta:
        verbose_name = "Configuração de Horário do Funcionário"
        verbose_name_plural = "Configurações de Horário dos Funcionários"
        ordering = ['funcionario__nome_completo']
