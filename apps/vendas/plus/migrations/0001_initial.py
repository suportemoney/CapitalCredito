# Generated manually for apps.vendas.plus

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StatusChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=50, unique=True)),
                ('cor_tag', models.CharField(default='6c757d', help_text='Cor de identificação em formato hexadecimal (sem #)', max_length=6)),
                ('impacto', models.CharField(choices=[('NEGATIVO', 'Negativo'), ('POSITIVO', 'Positivo')], default='NEGATIVO', max_length=10)),
                ('comportamento', models.CharField(choices=[('REPETIR', 'Repetir - Pode ser entregue a outro user'), ('NAO_ENTREGAR_MAIS', 'Não entregar mais o cliente - Nessa ou em qualquer campanha'), ('NAO_ENTREGAR_CAMPANHA', 'Não entregar mais o cliente nessa campanha - Se o CPF aparecer em campanha diferente pode ser chamado')], default='REPETIR', max_length=30)),
                ('conversao', models.BooleanField(default=False, help_text='Cliente de sucesso - tabulação positiva')),
                ('cpc', models.BooleanField(default=False, help_text='Contato com cliente certo - número estava correto')),
                ('oportunidade', models.BooleanField(default=False, help_text='Cliente em potencial - ainda não chegou a acordo mas é faturavel')),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('status_booleano', models.BooleanField(default=True)),
                ('order', models.IntegerField(default=0, help_text='Ordem de evolução (0 = primeiro, maior = depois)')),
            ],
            options={
                'verbose_name': 'Status Choice',
                'verbose_name_plural': 'Status Choices',
                'ordering': ['order', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='Equipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('status', models.BooleanField(default=True)),
                ('data_criacao', models.DateTimeField(default=django.utils.timezone.now)),
                ('participantes', models.ManyToManyField(blank=True, related_name='equipes_plus', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Equipe Plus',
                'verbose_name_plural': 'Equipes Plus',
            },
        ),
        migrations.CreateModel(
            name='CampanhaV2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('descricao', models.TextField(blank=True, null=True)),
                ('status', models.BooleanField(default=True)),
                ('tipo_campanha', models.CharField(choices=[('SIAPE', 'SIAPE'), ('OUTROS', 'Outros'), ('MISTA', 'Mista')], default='MISTA', max_length=10)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('equipes', models.ManyToManyField(blank=True, related_name='campanhas_v2', to='plus.equipe')),
            ],
            options={
                'verbose_name': 'Campanha Plus',
                'verbose_name_plural': 'Campanhas Plus',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='ClienteCampanhaV2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpf', models.CharField(db_index=True, max_length=11)),
                ('tipo', models.CharField(choices=[('SIAPE', 'SIAPE'), ('OUTROS', 'Outros')], max_length=10)),
                ('dados_json', models.JSONField(blank=True, default=None, null=True)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('campanha', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clientes', to='plus.campanhav2')),
            ],
            options={
                'verbose_name': 'Cliente Campanha Plus',
                'verbose_name_plural': 'Clientes Campanha Plus',
                'ordering': ['cpf'],
                'unique_together': {('campanha', 'cpf')},
            },
        ),
        migrations.CreateModel(
            name='ControleClienteV2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campanha', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='controles', to='plus.campanhav2')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='controles', to='plus.clientecampanhav2')),
                ('tabulacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='plus_controles_v2', to='plus.statuschoice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plus_controles_v2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Controle Cliente Plus',
                'verbose_name_plural': 'Controles Cliente Plus',
                'ordering': ['-updated_at'],
                'unique_together': {('campanha', 'cliente', 'user')},
            },
        ),
        migrations.CreateModel(
            name='ImportacaoCsvV2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('colunas_schema', models.JSONField(default=list)),
                ('arquivo_nome', models.CharField(max_length=255)),
                ('total_linhas', models.PositiveIntegerField(default=0)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('campanha', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='importacoes', to='plus.campanhav2')),
                ('criado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='plus_importacoes_csv_v2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Importação CSV Plus',
                'verbose_name_plural': 'Importações CSV Plus',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='AgendamentoV2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia_agendamento', models.DateField()),
                ('hora', models.TimeField()),
                ('responsavel', models.CharField(max_length=255)),
                ('observacao', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('EM_ESPERA', 'Em Espera'), ('REALIZADO', 'Realizado'), ('INATIVO', 'Inativo')], default='EM_ESPERA', max_length=20)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('controle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agendamentos', to='plus.controleclientev2')),
            ],
            options={
                'verbose_name': 'Agendamento Plus',
                'verbose_name_plural': 'Agendamentos Plus',
                'ordering': ['-dia_agendamento', 'hora'],
            },
        ),
    ]
