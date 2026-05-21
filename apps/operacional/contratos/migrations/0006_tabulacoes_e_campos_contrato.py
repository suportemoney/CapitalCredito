# Generated migration for tabulacoes iniciais e campos de contrato
from django.db import migrations, models


def criar_tabulacoes_iniciais(apps, schema_editor):
    """Criar as 15 tabulações do fluxo de contratos"""
    TabulacaoContrato = apps.get_model('contratos', 'TabulacaoContrato')
    
    tabulacoes = [
        {'ordem': 1, 'nome': 'CONTRATOS ENVIADOS', 'cor': '#17a2b8', 'status': True},
        {'ordem': 2, 'nome': 'INCOMPLETO', 'cor': '#ffc107', 'status': True},
        {'ordem': 3, 'nome': 'LINK DE FORMALIZACAO', 'cor': '#6f42c1', 'status': True},
        {'ordem': 4, 'nome': 'LINK ASSINADO', 'cor': '#20c997', 'status': True},
        {'ordem': 5, 'nome': 'FORMALIZADO', 'cor': '#28a745', 'status': True},
        {'ordem': 6, 'nome': 'SOLICITACAO DE VIDEO', 'cor': '#fd7e14', 'status': True},
        {'ordem': 7, 'nome': 'VIDEO ANEXADO', 'cor': '#6610f2', 'status': True},
        {'ordem': 8, 'nome': 'EM ANALISE', 'cor': '#007bff', 'status': True},
        {'ordem': 9, 'nome': 'ANUENCIA/AVERBACAO', 'cor': '#e83e8c', 'status': True},
        {'ordem': 10, 'nome': 'LIBERACAO', 'cor': '#20c997', 'status': True},
        {'ordem': 11, 'nome': 'ENVIO PARA PAGAMENTO', 'cor': '#17a2b8', 'status': True},
        {'ordem': 12, 'nome': 'CLIENTE PAGO', 'cor': '#28a745', 'status': True},
        {'ordem': 13, 'nome': 'CANCELADO', 'cor': '#dc3545', 'status': True},
        {'ordem': 14, 'nome': 'EMPRESA PAGA', 'cor': '#6c757d', 'status': True},
        {'ordem': 15, 'nome': 'CLIENTE FINALIZADO', 'cor': '#343a40', 'status': True},
    ]
    
    for tab_data in tabulacoes:
        TabulacaoContrato.objects.get_or_create(
            nome=tab_data['nome'],
            defaults={
                'ordem': tab_data['ordem'],
                'cor': tab_data['cor'],
                'status': tab_data['status']
            }
        )


def reverter_tabulacoes(apps, schema_editor):
    """Reverter - deletar tabulações criadas"""
    TabulacaoContrato = apps.get_model('contratos', 'TabulacaoContrato')
    nomes = [
        'CONTRATOS ENVIADOS', 'INCOMPLETO', 'LINK DE FORMALIZACAO', 'LINK ASSINADO',
        'FORMALIZADO', 'SOLICITACAO DE VIDEO', 'VIDEO ANEXADO', 'EM ANALISE',
        'ANUENCIA/AVERBACAO', 'LIBERACAO', 'ENVIO PARA PAGAMENTO', 'CLIENTE PAGO',
        'CANCELADO', 'EMPRESA PAGA', 'CLIENTE FINALIZADO'
    ]
    TabulacaoContrato.objects.filter(nome__in=nomes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0005_adicionar_paginas_schema'),
    ]

    operations = [
        # Adicionar campo observacoes_incompleto
        migrations.AddField(
            model_name='contratooperacional',
            name='observacoes_incompleto',
            field=models.TextField(blank=True, null=True, verbose_name='Observações Incompleto'),
        ),
        # Adicionar campo video_cliente
        migrations.AddField(
            model_name='contratooperacional',
            name='video_cliente',
            field=models.FileField(blank=True, null=True, upload_to='contratos/videos/%Y/%m/', verbose_name='Vídeo do Cliente'),
        ),
        # Adicionar campo video_tamanho
        migrations.AddField(
            model_name='contratooperacional',
            name='video_tamanho',
            field=models.IntegerField(blank=True, null=True, verbose_name='Tamanho do Vídeo (bytes)'),
        ),
        # Criar tabulações iniciais
        migrations.RunPython(criar_tabulacoes_iniciais, reverter_tabulacoes),
    ]
