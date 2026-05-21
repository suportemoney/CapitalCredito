from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import os

# --- Configuração de Armazenamento ---

def get_comunicado_upload_path(instance, filename):
    """Define o diretório como 'comunicados/<tipo>/<comunicado_id>/<filename>'"""
    if instance.pk:
        return os.path.join('comunicados', instance.tipo.lower(), str(instance.pk), filename)
    return os.path.join('comunicados', 'temp', filename)

# --- Modelos ---

class CategoriaComunicado(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da Categoria")
    cor = models.CharField(
        max_length=7, 
        default="#FFD700", 
        verbose_name="Cor da Categoria",
        help_text="Cor em hexadecimal (ex: #FFD700)"
    )
    icone = models.CharField(
        max_length=50, 
        default="bx-message-square-detail",
        verbose_name="Ícone",
        help_text="Classe do ícone Boxicons (ex: bx-message-square-detail)"
    )
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordem",
        help_text="Ordem de exibição (0 = maior prioridade)"
    )
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(CategoriaComunicado, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Categoria de Comunicado"
        verbose_name_plural = "Categorias de Comunicados"
        ordering = ['ordem', 'nome']

class Comunicado(models.Model):
    TIPO_CHOICES = [
        ('AVISO', 'Aviso'),
        ('ATUALIZACAO', 'Atualização do Sistema'),
        ('EVENTO_FUTURO', 'Evento Futuro'),
        ('EVENTO_PASSADO', 'Evento Passado'),
        ('TAREFA', 'Tarefa/Coisa a Fazer'),
        ('GERAL', 'Geral'),
    ]

    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('NORMAL', 'Normal'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    titulo = models.CharField(max_length=255, verbose_name="Título")
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='GERAL',
        verbose_name="Tipo de Comunicado"
    )
    categoria = models.ForeignKey(
        CategoriaComunicado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comunicados',
        verbose_name="Categoria"
    )
    conteudo = models.TextField(verbose_name="Conteúdo", help_text="Texto do comunicado")
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default='NORMAL',
        verbose_name="Prioridade"
    )
    banner = models.ImageField(
        upload_to=get_comunicado_upload_path,
        verbose_name="Banner",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'webp'])
        ]
    )
    data_evento = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Data do Evento",
        help_text="Data do evento (para eventos futuros ou passados)"
    )
    status = models.BooleanField(default=True, verbose_name="Ativo")
    fixo = models.BooleanField(
        default=False,
        verbose_name="Fixo no Topo",
        help_text="Se marcado, o comunicado ficará sempre no topo do mural"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='comunicados_criados',
        verbose_name="Criado por"
    )

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "Comunicado"
        verbose_name_plural = "Comunicados"
        ordering = ['-fixo', '-prioridade', '-data_criacao']

class ArquivoComunicado(models.Model):
    comunicado = models.ForeignKey(
        Comunicado,
        on_delete=models.CASCADE,
        related_name='arquivos',
        verbose_name="Comunicado"
    )
    arquivo = models.FileField(
        upload_to=get_comunicado_upload_path,
        verbose_name="Arquivo"
    )
    titulo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Título do Arquivo")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return f"Arquivo: {os.path.basename(self.arquivo.name)} - {self.comunicado.titulo}"

    class Meta:
        verbose_name = "Arquivo de Comunicado"
        verbose_name_plural = "Arquivos de Comunicados"
        ordering = ['-data_criacao']

class VisualizacaoComunicado(models.Model):
    comunicado = models.ForeignKey(
        Comunicado,
        on_delete=models.CASCADE,
        related_name='visualizacoes',
        verbose_name="Comunicado"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comunicados_visualizados',
        verbose_name="Usuário"
    )
    visualizado = models.BooleanField(default=False, verbose_name="Visualizado")
    data_visualizacao = models.DateTimeField(null=True, blank=True, verbose_name="Data da Visualização")

    class Meta:
        verbose_name = "Visualização de Comunicado"
        verbose_name_plural = "Visualizações de Comunicados"
        unique_together = ['comunicado', 'usuario']
        ordering = ['-data_visualizacao']

    def __str__(self):
        status = "Visualizado" if self.visualizado else "Não visualizado"
        return f"{self.comunicado.titulo} - {self.usuario.username} ({status})"
