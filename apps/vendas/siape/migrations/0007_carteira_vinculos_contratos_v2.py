# Vínculos M2M e FKs da carteira com contratos_v2 (após contratos_v2.0001_initial)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contratos_v2', '0001_initial'),
        ('siape', '0005_carteira_operacional_contratos'),
    ]

    operations = [
        migrations.AddField(
            model_name='carteiraclientes',
            name='cliente_operacional',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='carteiras_siape',
                to='contratos_v2.clientedadospessoais',
                verbose_name='Cliente operacional (contratos)',
            ),
        ),
        migrations.AddField(
            model_name='carteiraclientes',
            name='contratos_operacionais',
            field=models.ManyToManyField(
                blank=True,
                related_name='carteiras_siape',
                to='contratos_v2.contratoexecucao',
                verbose_name='Contratos (operacional)',
            ),
        ),
        migrations.AddField(
            model_name='carteiraclientes',
            name='propostas_operacionais',
            field=models.ManyToManyField(
                blank=True,
                related_name='carteiras_siape_propostas',
                to='contratos_v2.propostadados',
                verbose_name='Propostas (operacional)',
            ),
        ),
        migrations.AddField(
            model_name='carteiraclientes',
            name='simulacoes_operacionais',
            field=models.ManyToManyField(
                blank=True,
                related_name='carteiras_siape',
                to='contratos_v2.simulacao',
                verbose_name='Simulações (operacional)',
            ),
        ),
        migrations.AddField(
            model_name='registermoney',
            name='contrato_execucao',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='registros_financeiros_tc',
                to='contratos_v2.contratoexecucao',
            ),
        ),
    ]
