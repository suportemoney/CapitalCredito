from django.db import migrations, models
import string
import random


def gerar_numero_serie_unico(apps):
    """Gera um número de série único"""
    ContratoOperacional = apps.get_model('contratos', 'ContratoOperacional')
    caracteres = string.ascii_uppercase + string.digits
    
    while True:
        parte1 = ''.join(random.choices(caracteres, k=3))
        parte2 = ''.join(random.choices(caracteres, k=4))
        parte3 = ''.join(random.choices(caracteres, k=4))
        numero = f"{parte1}-{parte2}-{parte3}"
        
        if not ContratoOperacional.objects.filter(numero_serie=numero).exists():
            return numero


def gerar_numeros_serie_existentes(apps, schema_editor):
    """Gera números de série para contratos existentes"""
    ContratoOperacional = apps.get_model('contratos', 'ContratoOperacional')
    
    for contrato in ContratoOperacional.objects.filter(numero_serie__isnull=True):
        contrato.numero_serie = gerar_numero_serie_unico(apps)
        contrato.save(update_fields=['numero_serie'])
    
    # Para contratos que ficaram com string vazia
    for contrato in ContratoOperacional.objects.filter(numero_serie=''):
        contrato.numero_serie = gerar_numero_serie_unico(apps)
        contrato.save(update_fields=['numero_serie'])


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0006_tabulacoes_e_campos_contrato'),
    ]

    operations = [
        # Adicionar campo como nullable primeiro
        migrations.AddField(
            model_name='contratooperacional',
            name='numero_serie',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=30,
                verbose_name='Número de Série',
                help_text='Identificador único do contrato (5-30 caracteres)'
            ),
        ),
        # Popular dados existentes
        migrations.RunPython(gerar_numeros_serie_existentes, migrations.RunPython.noop),
        # Agora tornar unique e não nullable
        migrations.AlterField(
            model_name='contratooperacional',
            name='numero_serie',
            field=models.CharField(
                max_length=30,
                unique=True,
                verbose_name='Número de Série',
                help_text='Identificador único do contrato (5-30 caracteres)'
            ),
        ),
        # Adicionar índice
        migrations.AddIndex(
            model_name='contratooperacional',
            index=models.Index(fields=['numero_serie'], name='contratos_c_numero__idx'),
        ),
    ]
