"""
Template tags para verificação de permissões/acessos nos templates.
"""
from django import template
from django.contrib.auth.models import User
from apps.seguranca.permissoes.utils import user_has_access

register = template.Library()

@register.simple_tag
def has_access(user, code):
    """
    Template tag para verificar se o usuário tem acesso.
    
    Uso:
        {% load permissoes_tags %}
        {% if has_access user 'CT1' %}
            <a href="...">Link</a>
        {% endif %}
    """
    return user_has_access(user, code)

@register.filter(name='has_access')
def has_access_filter(user, code):
    """
    Template filter para verificar se o usuário tem acesso.
    
    Uso:
        {% load permissoes_tags %}
        {% if user|has_access:'CT1' %}
            <a href="...">Link</a>
        {% endif %}
    """
    return user_has_access(user, code)

@register.tag(name='if_container')
def if_container(parser, token):
    """
    Template tag condicional para containers (CX).
    
    Uso:
        {% load permissoes_tags %}
        {% if_container user 'CX1' %}
            <div class="container">
                Conteúdo visível apenas com permissão
            </div>
        {% endif_container %}
    """
    try:
        tag_name, user_var, code = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            f"{token.contents.split()[0]} tag requires exactly 2 arguments: user and code"
        )
    
    nodelist = parser.parse(('endif_container',))
    parser.delete_first_token()
    
    return ContainerNode(user_var, code, nodelist)

@register.tag(name='if_container')
def if_container(parser, token):
    """
    Template tag condicional para containers.
    
    Uso:
        {% load permissoes_tags %}
        {% if_container user 'CX1' %}
            <div class="container">
                Conteúdo visível apenas com permissão
            </div>
        {% endif_container %}
    """
    try:
        tag_name, user_var, code = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            f"{token.contents.split()[0]} tag requires exactly 2 arguments: user and code"
        )
    
    nodelist = parser.parse(('endif_container',))
    parser.delete_first_token()
    
    return ContainerNode(user_var, code, nodelist)

class ContainerNode(template.Node):
    def __init__(self, user_var, code, nodelist):
        self.user_var = template.Variable(user_var)
        self.code = code.strip('"\'')
        self.nodelist = nodelist
    
    def render(self, context):
        try:
            user = self.user_var.resolve(context)
            if user_has_access(user, self.code):
                return self.nodelist.render(context)
        except template.VariableDoesNotExist:
            pass
        return ''

