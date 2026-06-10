# Migration manual — não executar manage.py no ambiente do projeto

from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_valor_tc(apps, schema_editor):
    ContratoPagamento = apps.get_model('financeiro_vendas', 'ContratoPagamento')
    for cp in ContratoPagamento.objects.all().iterator():
        repasse = cp.valor_repasse or Decimal('0')
        cp.valor_tc = repasse
        if cp.status == 'PAGO':
            cp.valor_tc_acumulado = repasse
        else:
            cp.valor_tc_acumulado = Decimal('0')
        cp.save(update_fields=['valor_tc', 'valor_tc_acumulado'])


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contratos_v2', '0001_initial'),
        ('financeiro_vendas', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='contratopagamento',
            name='flag_repasse',
            field=models.BooleanField(default=False, verbose_name='Linha de repasse'),
        ),
        migrations.AddField(
            model_name='contratopagamento',
            name='valor_tc',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Meta de TC a pagar',
                max_digits=15,
                verbose_name='Valor TC (R$)',
            ),
        ),
        migrations.AddField(
            model_name='contratopagamento',
            name='valor_tc_acumulado',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=15,
                verbose_name='TC pago acumulado (R$)',
            ),
        ),
        migrations.AddField(
            model_name='contratopagamento',
            name='contrato_execucao',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='contratos_pagamento_financeiro',
                to='contratos_v2.contratoexecucao',
                verbose_name='Contrato operacional (v2)',
            ),
        ),
        migrations.CreateModel(
            name='ComprovanteTC',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valor pago (TC)')),
                ('arquivo', models.FileField(upload_to='financeiro_vendas/comprovantes_tc/%Y/%m/', verbose_name='Arquivo')),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Criado em')),
                ('status', models.BooleanField(default=True, verbose_name='Ativo')),
                (
                    'comprovante_v2_id',
                    models.PositiveIntegerField(
                        blank=True,
                        db_index=True,
                        help_text='Espelho do ComprovanteTC em contratos_v2 (idempotência na sync)',
                        null=True,
                        verbose_name='ID comprovante contratos_v2',
                    ),
                ),
                (
                    'contrato_pagamento',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='comprovantes_tc',
                        to='financeiro_vendas.contratopagamento',
                        verbose_name='Contrato pagamento',
                    ),
                ),
                (
                    'criado_por',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='comprovantes_tc_financeiro_criados',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Criado por',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Comprovante TC',
                'verbose_name_plural': 'Comprovantes TC',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddIndex(
            model_name='contratopagamento',
            index=models.Index(fields=['contrato_execucao', 'user'], name='financeiro__contrat_8a1f2c_idx'),
        ),
        migrations.AddConstraint(
            model_name='contratopagamento',
            constraint=models.UniqueConstraint(
                condition=models.Q(('contrato_execucao__isnull', False)),
                fields=('contrato_execucao', 'user'),
                name='financeiro_cp_unique_ce_user',
            ),
        ),
        migrations.AddConstraint(
            model_name='comprovantetc',
            constraint=models.UniqueConstraint(
                condition=models.Q(('comprovante_v2_id__isnull', False)),
                fields=('comprovante_v2_id', 'contrato_pagamento'),
                name='financeiro_comp_tc_unique_v2_cp',
            ),
        ),
        migrations.RunPython(backfill_valor_tc, reverse_backfill),
    ]
