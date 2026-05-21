from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Acesso(models.Model):
    """
    Modelo para definir permissões/acessos do sistema.
    Tipos hierárquicos: CT > SCT > SS > SSS > CX
    """
    CATEGORIA_APP = 'CT'
    SUBCATEGORIA_RENDER = 'SCT'
    SESSAO_SECTION = 'SS'
    SUBSESSAO_DIV = 'SSS'
    CAIXA_BOX = 'CX'
    
    TIPO_CHOICES = [
        (CATEGORIA_APP, 'Categoria - APP (Menu Lateral)'),
        (SUBCATEGORIA_RENDER, 'SubCategoria - Render/Template/URL'),
        (SESSAO_SECTION, 'Sessão - Section/Container'),
        (SUBSESSAO_DIV, 'SubSessão - Div/Content'),
        (CAIXA_BOX, 'Caixa - div/span/box/card'),
    ]

    nome = models.CharField(max_length=100, verbose_name="Nome")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    status = models.BooleanField(default=True, verbose_name="Ativo")

    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        super(Acesso, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    def gerar_codigo(self):
        """Gera código de acesso no formato: TIPO + ID (ex: CT1, SCT5)"""
        return f"{self.tipo}{self.id}"

    class Meta:
        verbose_name = "Acesso"
        verbose_name_plural = "Acessos"
        ordering = ['tipo', 'nome']

class AcessoHierarquia(models.Model):
    """
    Modelo para associar acessos hierarquicamente.
    Um pai pode ter vários filhos, mas um filho só pode ter um pai.
    Ex: CT (pai) pode ter vários SCTs (filhos), SCT (pai) pode ter vários SSs (filhos), etc.
    """
    pai = models.ForeignKey(
        Acesso,
        on_delete=models.CASCADE,
        related_name='hierarquias_como_pai',
        verbose_name="Acesso Pai",
        help_text="Acesso que será o pai (ex: CT, SCT)"
    )
    filhos = models.ManyToManyField(
        Acesso,
        related_name='hierarquias_como_filho',
        verbose_name="Acessos Filhos",
        help_text="Acessos que serão filhos deste pai (ex: SCTs para CT, SSs para SCT)"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    status = models.BooleanField(default=True, verbose_name="Ativo")

    def clean(self):
        """Valida que os filhos são de nível hierárquico inferior ao pai"""
        hierarquia = {
            Acesso.CATEGORIA_APP: 1,      # CT
            Acesso.SUBCATEGORIA_RENDER: 2, # SCT
            Acesso.SESSAO_SECTION: 3,     # SS
            Acesso.SUBSESSAO_DIV: 4,      # SSS
            Acesso.CAIXA_BOX: 5           # CX
        }
        
        nivel_pai = hierarquia.get(self.pai.tipo)
        
        if nivel_pai is None:
            raise ValidationError('Tipo de acesso pai inválido.')
        
        # Validar que todos os filhos são de nível inferior ao pai
        for filho in self.filhos.all():
            nivel_filho = hierarquia.get(filho.tipo)
            if nivel_filho is None:
                raise ValidationError(f'Tipo de acesso filho inválido: {filho.nome}')
            if nivel_filho <= nivel_pai:
                raise ValidationError(
                    f'O acesso filho {filho.nome} ({filho.get_tipo_display()}) deve ser de nível inferior ao pai {self.pai.nome} ({self.pai.get_tipo_display()}).'
                )

    def __str__(self):
        filhos_count = self.filhos.count()
        return f"{self.pai.nome} → {filhos_count} filho(s)"

    class Meta:
        verbose_name = "Hierarquia de Acesso"
        verbose_name_plural = "Hierarquias de Acessos"
        unique_together = ['pai']
        ordering = ['pai__nome']

class GroupsAcessos(models.Model):
    """
    Modelo para agrupar acessos em grupos/perfis.
    Facilita a atribuição de múltiplas permissões de uma vez.
    """
    titulo = models.CharField(max_length=100, verbose_name="Título do Grupo")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    acessos = models.ManyToManyField(Acesso, related_name='groups_acessos', verbose_name="Acessos")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    status = models.BooleanField(default=True, verbose_name="Ativo")

    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper()
        super(GroupsAcessos, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} ({self.acessos.count()} acessos)"

    class Meta:
        verbose_name = "Grupo de Acessos"
        verbose_name_plural = "Grupos de Acessos"
        ordering = ['titulo']

class ControleAcessos(models.Model):
    """
    Modelo para controlar quais acessos cada usuário possui.
    Relacionamento Many-to-Many entre User e Acesso.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='controle_acessos',
        verbose_name="Usuário"
    )
    acessos = models.ManyToManyField(
        Acesso, 
        related_name='usuarios_controle',
        verbose_name="Acessos"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    status = models.BooleanField(default=True, verbose_name="Ativo")

    def __str__(self):
        return f"{self.user.username} – {self.acessos.count()} acessos"

    class Meta:
        verbose_name = "Controle de Acesso"
        verbose_name_plural = "Controles de Acesso"
        unique_together = ['user']
        ordering = ['user__username']
