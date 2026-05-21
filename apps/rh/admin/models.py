from django.db import models
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

# --- Configuração de Armazenamento ---

def get_loja_logo_upload_path(instance, filename):
    """Define o diretório como 'lojas/logos/<loja_id>/<filename>'"""
    if instance.pk:
        return os.path.join('lojas', 'logos', str(instance.pk), filename)
    return os.path.join('lojas', 'logos', 'sem_id', filename)

# --- Modelos Principais ---

class Empresa(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome")
    cnpj = models.CharField(max_length=18, unique=True, verbose_name="CNPJ")
    flg_parceira = models.BooleanField(default=False, verbose_name="Empresa Parceira")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Empresa, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nome']

class Loja(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome")
    logo = models.ImageField(upload_to=get_loja_logo_upload_path, null=True, blank=True, verbose_name="Logo")
    endereco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Endereço")
    flg_sede = models.BooleanField(default=False, verbose_name="Sede")
    flg_filial = models.BooleanField(default=False, verbose_name="Filial")
    flg_franquia = models.BooleanField(default=False, verbose_name="Franquia")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        if self.endereco:
            self.endereco = self.endereco.upper()
        super(Loja, self).save(*args, **kwargs)

    def __str__(self):
        tipo = ""
        if self.flg_sede:
            tipo = " (Sede)"
        elif self.flg_filial:
            tipo = " (Filial)"
        elif self.flg_franquia:
            tipo = " (Franquia)"
        return f'{self.nome}{tipo}'

    class Meta:
        verbose_name = "Loja"
        verbose_name_plural = "Lojas"
        ordering = ['nome']

class NivelHierarquico(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome")
    importancia = models.IntegerField(verbose_name="Importância", help_text="Valor numérico que define a hierarquia (0 = menor, maior valor = maior hierarquia)")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(NivelHierarquico, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} (Importância: {self.importancia})"

    class Meta:
        verbose_name = "Nível Hierárquico"
        verbose_name_plural = "Níveis Hierárquicos"
        ordering = ['-importancia', 'nome']

class Cargo(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome do Cargo")
    nivel_hierarquico = models.ForeignKey(NivelHierarquico, on_delete=models.PROTECT, related_name='cargos', verbose_name="Nível Hierárquico")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Cargo, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.nivel_hierarquico.nome})"

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ['nivel_hierarquico__importancia', 'nome']
        unique_together = ('nome', 'nivel_hierarquico')

class Departamento(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Departamento, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['nome']

class Setor(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Setor, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ['nome']

class Equipe(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da Equipe")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Equipe, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Equipe"
        verbose_name_plural = "Equipes"
        ordering = ['nome']
