"""
Views para renderizar templates (apenas renders)
"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from apps.seguranca.permissoes.decorators import controle_acess
from apps.rh.admin.models import Setor
from apps.vendas.siape.models import Produto
from .models import Classificador

@login_required
@controle_acess('SS27')
def render_index(request):
    """Página inicial do módulo Financeiro Vendas"""
    setores = Setor.objects.filter(status=True).order_by('nome')
    # Passar TODOS os produtos e classificadores (ativos e inativos) para os selects da tabela
    # Isso garante que contratos com produtos/classificadores inativos ainda possam ser exibidos/editados
    produtos = Produto.objects.all().order_by('nome')
    classificadores = Classificador.objects.all().order_by('titulo')
    usuarios = User.objects.filter(is_active=True).select_related('funcionario_profile').order_by('username')
    
    # Serializar produtos e classificadores para JSON seguro
    produtos_json = json.dumps([{'id': p.id, 'nome': p.nome} for p in produtos], ensure_ascii=False)
    classificadores_json = json.dumps([{'id': c.id, 'titulo': c.titulo, 'percentual': float(c.percentual)} for c in classificadores], ensure_ascii=False)
    
    context = {
        'setores': setores,
        'produtos': produtos,
        'classificadores': classificadores,
        'usuarios': usuarios,
        'produtos_json': produtos_json,
        'classificadores_json': classificadores_json,
    }
    return render(request, 'financeiro_vendas/index.html', context)

@login_required
@controle_acess('SS29')
def render_classificador(request):
    """Página de gerenciamento de classificadores"""
    return render(request, 'financeiro_vendas/classificador.html')
