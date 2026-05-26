# Carteira comercial + RegisterMoney para integração contratos v2

import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('rh_admin', '0001_initial'),
        ('siape', '0004_remove_contrato_siape_contr_matricu_cc5060_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassificacaoValor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=120, verbose_name='Título')),
                ('percentual', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Percentual')),
                ('status', models.BooleanField(default=True, verbose_name='Ativo')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')),
            ],
            options={
                'verbose_name': 'Classificação de valor',
                'verbose_name_plural': 'Classificações de valor',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='CarteiraClientes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(db_index=True, default='ATIVO', max_length=20, verbose_name='Status')),
                ('status_comercial', models.CharField(blank=True, db_index=True, default='EM_NEGOCIACAO', max_length=30, null=True, verbose_name='Status comercial')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('tabulacao_operacional', models.CharField(blank=True, db_index=True, max_length=140, null=True, verbose_name='Tabulação operacional (agregada)')),
                ('tags_operacionais', models.TextField(blank=True, null=True, verbose_name='Tags operacionais')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')),
                ('tag_proposta_container', models.CharField(blank=True, choices=[('AGUARDANDO', 'Aguardando'), ('SUCESSO', 'Sucesso'), ('INELEGIVEL', 'Inelegível')], db_index=True, max_length=20, null=True, verbose_name='Tag container propostas')),
                ('sub_status_propostas_comercial', models.CharField(blank=True, choices=[('ACEITE', 'Aceite'), ('VERIFICANDO', 'Verificando'), ('VERIFICADO', 'Verificado')], db_index=True, max_length=20, null=True, verbose_name='Sub-status propostas (comercial)')),
                ('tag_status_operacional', models.CharField(blank=True, choices=[('AGUARDANDO_SIMULACAO', 'Aguardando Simulação'), ('AGUARDANDO_PROPOSTA', 'Aguardando Proposta'), ('AGUARDANDO_DIGITACAO', 'Aguardando Digitação'), ('EM_DIGITACAO', 'Em Digitação')], db_index=True, max_length=40, null=True, verbose_name='Tag status operacional')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carteira_clientes', to='siape.cliente', verbose_name='Cliente')),
                ('user_repasse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='carteira_como_repasse', to=settings.AUTH_USER_MODEL, verbose_name='Usuário repasse')),
                ('user_responsavel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carteira_como_responsavel', to=settings.AUTH_USER_MODEL, verbose_name='Usuário responsável')),
            ],
            options={
                'verbose_name': 'Carteira de cliente',
                'verbose_name_plural': 'Carteira de clientes',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='TabulacaoVendedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('EM_NEGOCIACAO', 'Em Negociação'), ('AGENDAR', 'Agendar'), ('SEM_INTERESSE', 'Sem Interesse'), ('NAO_E_O_CLIENTE', 'Não é o Cliente'), ('AGUARDANDO_DOCUMENTOS', 'Aguardando Documentos'), ('DESISTENCIA', 'Desistência'), ('NEGOCIO_FECHADO', 'Negócio Fechado'), ('SIMULACAO', 'Simulação'), ('OPERACIONAL', 'Operacional'), ('SOLICITACAO_PROPOSTAS', 'Solicitação de Propostas'), ('PROPOSTAS', 'Propostas'), ('INELEGIVEL', 'Inelegível'), ('DIGITACAO', 'Digitação'), ('FINALIZADA', 'Finalizada')], db_index=True, max_length=30, verbose_name='Tipo')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')),
                ('carteira_clientes', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tabulacoes_vendedor', to='siape.carteiraclientes', verbose_name='Carteira')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tabulacoes_vendedor', to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Tabulação vendedor',
                'verbose_name_plural': 'Tabulações vendedor',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='RegisterMoney',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cpf_cliente', models.CharField(blank=True, db_index=True, max_length=14, null=True)),
                ('valor_est', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Valor estimado (TC)')),
                ('valor_pago_acumulado', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='TC pago acumulado')),
                ('af', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='AF')),
                ('valor_cms_recebido', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('valor_cms_repassado', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('valor_cms_plastico', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('flag_cms_pago', models.BooleanField(default=False, verbose_name='CMS pago')),
                ('classificador_auto', models.CharField(blank=True, choices=[('M1', 'M1 (100% - Novo)'), ('M2', 'M2 (50% - Retrabalho)'), ('M3', 'M3 (0% - Manual)')], db_index=True, max_length=2, null=True)),
                ('tipo_classificacao', models.CharField(blank=True, choices=[('NOVO', 'Novo'), ('RETRABALHO', 'Retrabalho'), ('MANUAL', 'Manual M3')], max_length=15, null=True)),
                ('status', models.BooleanField(blank=True, default=True, null=True, verbose_name='Ativo')),
                ('data', models.DateTimeField(blank=True, db_index=True, default=django.utils.timezone.now, null=True)),
                ('data_pago', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('flg_ponta', models.BooleanField(blank=True, default=False, null=True, verbose_name='Flag ponta')),
                ('flag_repasse', models.BooleanField(default=False, verbose_name='Linha de repasse')),
                ('classificacao_valor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_financeiros', to='siape.classificacaovalor')),
                ('departamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_financeiros', to='rh_admin.departamento')),
                ('empresa', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_financeiros', to='rh_admin.empresa')),
                ('equipe', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_financeiros', to='rh_admin.equipe')),
                ('loja', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='rh_admin.loja', verbose_name='Loja')),
                ('produto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='siape.produto', verbose_name='Produto')),
                ('setor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_financeiros', to='rh_admin.setor')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Registro financeiro',
                'verbose_name_plural': 'Registros financeiros',
                'ordering': ['-data'],
            },
        ),
        migrations.CreateModel(
            name='ArquivoCarteiraCliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(upload_to='carteira_clientes/%Y/%m/', verbose_name='Arquivo')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')),
                ('carteira_clientes', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arquivos_carteira', to='siape.carteiraclientes', verbose_name='Carteira')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arquivos_carteira_enviados', to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Arquivo da carteira',
                'verbose_name_plural': 'Arquivos da carteira',
                'ordering': ['-data_criacao'],
            },
        ),
    ]
