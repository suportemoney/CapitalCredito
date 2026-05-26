# Índices de CarteiraClientes (Meta do models.py; não estavam no 0005)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('siape', '0007_carteira_vinculos_contratos_v2'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['user_responsavel']),
        ),
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['user_repasse']),
        ),
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['status']),
        ),
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['status_comercial']),
        ),
    ]
