# Generated manually - separa anexo geral de comprovante de pagamento

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro_geral', '0005_bonificacaoapagar_chave_pix'),
    ]

    operations = [
        migrations.AddField(
            model_name='conta',
            name='anexo',
            field=models.FileField(blank=True, null=True, upload_to='tesouraria/anexos/%Y/%m/', verbose_name='Anexo geral'),
        ),
        migrations.AddField(
            model_name='salario',
            name='anexo',
            field=models.FileField(blank=True, null=True, upload_to='tesouraria/anexos/%Y/%m/', verbose_name='Anexo geral'),
        ),
        migrations.AddField(
            model_name='beneficio',
            name='anexo',
            field=models.FileField(blank=True, null=True, upload_to='tesouraria/anexos/%Y/%m/', verbose_name='Anexo geral'),
        ),
    ]
