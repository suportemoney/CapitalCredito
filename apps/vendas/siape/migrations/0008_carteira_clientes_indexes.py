# Índices de CarteiraClientes (Meta do models.py; não estavam no 0005)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('siape', '0007_carteira_vinculos_contratos_v2'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['user_responsavel'], name='siape_cart_user_resp_idx'),
        ),
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['user_repasse'], name='siape_cart_user_rep_idx'),
        ),
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['status'], name='siape_cart_status_idx'),
        ),
        migrations.AddIndex(
            model_name='carteiraclientes',
            index=models.Index(fields=['status_comercial'], name='siape_cart_st_com_idx'),
        ),
    ]
