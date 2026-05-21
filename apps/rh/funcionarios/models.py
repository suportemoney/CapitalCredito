from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

# Importar models do admin
from apps.rh.admin.models import (
    Empresa, Loja, Departamento, Setor, Equipe, Cargo
)

# --- Configuração de Armazenamento ---

def get_funcionario_upload_path(instance, filename):
    """Define o diretório como 'funcionarios/<nome_completo>/<filename>'"""
    if hasattr(instance, 'funcionario') and instance.funcionario:
        nome_completo = instance.funcionario.nome_completo.replace(' ', '_').upper()
        return os.path.join('funcionarios', nome_completo, filename)
    elif hasattr(instance, 'nome_completo') and instance.nome_completo:
        nome_completo = instance.nome_completo.replace(' ', '_').upper()
        return os.path.join('funcionarios', nome_completo, filename)
    return os.path.join('funcionarios', 'sem_nome', filename)

# --- Modelos Auxiliares ---

class Genero(models.Model):
    nome = models.CharField(max_length=50, verbose_name="Nome")
    icone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ícone", help_text="Classe do ícone Boxicons")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Genero, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Gênero"
        verbose_name_plural = "Gêneros"
        ordering = ['nome']

class TipoContrato(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(TipoContrato, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tipo de Contrato"
        verbose_name_plural = "Tipos de Contrato"
        ordering = ['nome']

class HorarioTrabalho(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Horário")
    entrada = models.TimeField(verbose_name="Horário de Entrada")
    saida_almoco = models.TimeField(verbose_name="Saída para Almoço")
    volta_almoco = models.TimeField(verbose_name="Volta do Almoço")
    saida = models.TimeField(verbose_name="Horário de Saída")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(HorarioTrabalho, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.entrada} - {self.saida_almoco} / {self.volta_almoco} - {self.saida})"

    class Meta:
        verbose_name = "Horário de Trabalho"
        verbose_name_plural = "Horários de Trabalho"
        ordering = ['nome']

# --- Modelo Principal ---

class Funcionario(models.Model):
    nome_completo = models.CharField(max_length=255, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    rg = models.CharField(max_length=20, blank=True, null=True, verbose_name="RG")
    data_nascimento = models.DateField(blank=True, null=True, verbose_name="Data de Nascimento")
    usuario = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='funcionario_profile', null=True, blank=True, verbose_name="Usuário Django")
    foto = models.ImageField(upload_to=get_funcionario_upload_path, blank=True, null=True, verbose_name="Foto")
    apelido = models.CharField(max_length=100, blank=True, null=True, verbose_name="Apelido")
    chave_pix = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave PIX")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.nome_completo = self.nome_completo.upper() if self.nome_completo else None
        self.apelido = self.apelido.upper() if self.apelido else None
        super(Funcionario, self).save(*args, **kwargs)

    def __str__(self):
        display = self.apelido if self.apelido else (self.nome_completo.split()[0] if self.nome_completo else 'Sem Nome')
        return f"{display} ({self.cpf})"

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ['nome_completo']

# --- Modelos de Dados Relacionados ---

class DadosPessoais(models.Model):
    ESTADO_CIVIL_CHOICES = [
        ('SOLTEIRO', 'Solteiro(a)'),
        ('CASADO', 'Casado(a)'),
        ('DIVORCIADO', 'Divorciado(a)'),
        ('VIUVO', 'Viúvo(a)'),
        ('UNIAO_ESTAVEL', 'União Estável'),
    ]

    funcionario = models.OneToOneField(Funcionario, on_delete=models.CASCADE, related_name='dados_pessoais', verbose_name="Funcionário")
    genero = models.ForeignKey(Genero, on_delete=models.SET_NULL, null=True, blank=True, related_name='dados_pessoais', verbose_name="Gênero")
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True, null=True, verbose_name="Estado Civil")
    nacionalidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nacionalidade")
    naturalidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Naturalidade (Cidade de Nascimento)")

    def save(self, *args, **kwargs):
        if self.nacionalidade:
            self.nacionalidade = self.nacionalidade.upper()
        if self.naturalidade:
            self.naturalidade = self.naturalidade.upper()
        super(DadosPessoais, self).save(*args, **kwargs)

    def __str__(self):
        return f"Dados Pessoais - {self.funcionario.nome_completo}"

    class Meta:
        verbose_name = "Dados Pessoais"
        verbose_name_plural = "Dados Pessoais"
        ordering = ['funcionario__nome_completo']

class Contato(models.Model):
    funcionario = models.OneToOneField(Funcionario, on_delete=models.CASCADE, related_name='contato', verbose_name="Funcionário")
    email_pessoa = models.EmailField(max_length=255, blank=True, null=True, verbose_name="E-mail Pessoal")
    celular_1 = models.CharField(max_length=20, blank=True, null=True, verbose_name="Celular Principal")
    celular_2 = models.CharField(max_length=20, blank=True, null=True, verbose_name="Celular Secundário")

    def __str__(self):
        return f"Contato - {self.funcionario.nome_completo}"

    class Meta:
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"
        ordering = ['funcionario__nome_completo']

class Localizacao(models.Model):
    funcionario = models.OneToOneField(Funcionario, on_delete=models.CASCADE, related_name='localizacao', verbose_name="Funcionário")
    cep = models.CharField(max_length=9, blank=True, null=True, verbose_name="CEP")
    endereco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Endereço")
    numero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número")
    complemento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    estado = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")

    def save(self, *args, **kwargs):
        if self.endereco:
            self.endereco = self.endereco.upper()
        if self.complemento:
            self.complemento = self.complemento.upper()
        if self.bairro:
            self.bairro = self.bairro.upper()
        if self.cidade:
            self.cidade = self.cidade.upper()
        if self.estado:
            self.estado = self.estado.upper()
        super(Localizacao, self).save(*args, **kwargs)

    def __str__(self):
        return f"Localização - {self.funcionario.nome_completo}"

    class Meta:
        verbose_name = "Localização"
        verbose_name_plural = "Localizações"
        ordering = ['funcionario__nome_completo']

class DadosProfissionais(models.Model):
    funcionario = models.OneToOneField(Funcionario, on_delete=models.CASCADE, related_name='dados_profissionais', verbose_name="Funcionário")
    pis = models.CharField(max_length=20, blank=True, null=True, verbose_name="PIS")
    matricula = models.CharField(max_length=50, blank=True, null=True, verbose_name="Matrícula")
    tipo_contrato = models.ForeignKey(TipoContrato, on_delete=models.SET_NULL, null=True, blank=True, related_name='dados_profissionais', verbose_name="Tipo de Contrato")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='funcionarios', verbose_name="Empresa")
    lojas = models.ManyToManyField(Loja, blank=True, related_name='funcionarios', verbose_name="Lojas")
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name='funcionarios', verbose_name="Departamento")
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name='funcionarios', verbose_name="Setor")
    equipe = models.ForeignKey(Equipe, on_delete=models.SET_NULL, blank=True, null=True, related_name='funcionarios', verbose_name="Equipe")
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='funcionarios', verbose_name="Cargo")
    horario = models.ForeignKey(HorarioTrabalho, on_delete=models.SET_NULL, null=True, blank=True, related_name='funcionarios', verbose_name="Horário de Trabalho")
    data_admissao = models.DateField(blank=True, null=True, verbose_name="Data de Admissão")
    data_demissao = models.DateField(blank=True, null=True, verbose_name="Data de Demissão")

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.data_admissao and self.data_demissao and self.data_demissao < self.data_admissao:
            raise ValidationError({'data_demissao': "A data de demissão não pode ser anterior à data de admissão."})

    def __str__(self):
        return f"Dados Profissionais - {self.funcionario.nome_completo}"

    class Meta:
        verbose_name = "Dados Profissionais"
        verbose_name_plural = "Dados Profissionais"
        ordering = ['funcionario__nome_completo']

class Arquivos(models.Model):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='arquivos', verbose_name="Funcionário")
    titulo = models.CharField(max_length=100, verbose_name="Título do Arquivo")
    arquivo = models.FileField(upload_to=get_funcionario_upload_path, verbose_name="Arquivo")
    status = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper()
        super(Arquivos, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} - {self.funcionario.nome_completo}"

    def get_tamanho_arquivo(self):
        """Retorna o tamanho do arquivo em formato legível"""
        try:
            if self.arquivo and hasattr(self.arquivo, 'size'):
                tamanho = self.arquivo.size
                if tamanho < 1024:
                    return f"{tamanho} bytes"
                elif tamanho < 1024 * 1024:
                    return f"{tamanho/1024:.1f} KB"
                else:
                    return f"{tamanho/(1024*1024):.1f} MB"
            return "Arquivo não disponível"
        except:
            return "Erro ao calcular tamanho"

    class Meta:
        verbose_name = "Arquivo do Funcionário"
        verbose_name_plural = "Arquivos dos Funcionários"
        ordering = ['funcionario__nome_completo', '-data_criacao']
