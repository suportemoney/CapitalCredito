"""
URL configuration for setup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Apps RH
    path('rh/admin/', include('apps.rh.admin.urls')),
    path('rh/funcionarios/', include('apps.rh.funcionarios.urls')),
    path('rh/usuarios/', include('apps.rh.usuarios.urls')),
    path('rh/ponto/', include('apps.rh.ponto.urls')),
    
    # Apps Vendas - SIAPE é a rota principal
    path('', include('apps.vendas.siape.urls')),
    path('vendas/financeiro/', include('apps.vendas.financeiro_vendas.urls')),
    
    # Apps Tesouraria
    path('tesouraria/financeiro/', include('apps.tesouraria.financeiro_geral.urls')),
    path('tesouraria/bonificacoes/', include('apps.tesouraria.bonificacoes.urls')),
    
    # Apps Geral
    path('comunicados/', include('apps.geral.comunicados.urls')),
    
    # Apps Segurança
    path('seguranca/permissoes/', include('apps.seguranca.permissoes.urls')),
    
    # Apps Operacional
    path('operacional/contratos/', include('apps.operacional.contratos.urls')),
]

# Servir arquivos de mídia durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
