# -*- coding: utf-8 -*-
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('siape', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contratos_v2', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricoTransacaoSimulacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('correlacao_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name='ID de correlação')),
                ('acao', models.CharField(
                    choices=[
                        ('CRIACAO', 'Criação'),
                        ('TRANSICAO', 'Transição de estado'),
                        ('RESPOSTA_PROPOSTAS', 'Resposta com propostas'),
                        ('INELEGIVEL', 'Inelegível'),
                        ('TABULACAO', 'Tabulação comercial'),
                    ],
                    db_index=True,
                    max_length=40,
                    verbose_name='Ação',
                )),
                ('estado_anterior', models.CharField(blank=True, default='', max_length=40, verbose_name='Estado anterior')),
                ('estado_novo', models.CharField(blank=True, default='', max_length=40, verbose_name='Estado novo')),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='Payload técnico')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('data_hora', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')),
                ('carteira_clientes', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_simulacao',
                    to='siape.carteiraclientes',
                    verbose_name='Carteira',
                )),
                ('historico_evento', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='transacao_tecnica',
                    to='contratos_v2.historicoeventosimulacao',
                    verbose_name='Evento linha do tempo',
                )),
                ('proposta_vinculada', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_simulacao',
                    to='contratos_v2.propostadados',
                    verbose_name='Proposta vinculada',
                )),
                ('solicitacao', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historico_transacoes_tecnicas',
                    to='contratos_v2.solicitacaopropostacliente',
                    verbose_name='Solicitação',
                )),
                ('usuario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacao_simulacao',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuário',
                )),
            ],
            options={
                'verbose_name': 'Histórico transação (simulação)',
                'verbose_name_plural': 'Históricos transação (simulação)',
                'ordering': ['-data_hora'],
            },
        ),
        migrations.CreateModel(
            name='HistoricoTransacaoProposta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('correlacao_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name='ID de correlação')),
                ('acao', models.CharField(
                    choices=[
                        ('CRIACAO', 'Criação'),
                        ('EDICAO', 'Edição'),
                        ('ACEITE_CLIENTE', 'Aceite pelo cliente'),
                        ('ENVIO_DIGITACAO', 'Envio para digitação'),
                        ('TABULACAO', 'Tabulação comercial'),
                    ],
                    db_index=True,
                    max_length=40,
                    verbose_name='Ação',
                )),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='Payload técnico')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('data_hora', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')),
                ('carteira_clientes', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_proposta',
                    to='siape.carteiraclientes',
                    verbose_name='Carteira',
                )),
                ('contrato_vinculado', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_proposta',
                    to='contratos_v2.contratoexecucao',
                    verbose_name='Contrato vinculado',
                )),
                ('historico_digitacao', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='transacao_tecnica_proposta',
                    to='contratos_v2.historicoeventodigitacao',
                    verbose_name='Evento digitação',
                )),
                ('proposta', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historico_transacoes_tecnicas',
                    to='contratos_v2.propostadados',
                    verbose_name='Proposta',
                )),
                ('solicitacao_origem', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_proposta',
                    to='contratos_v2.solicitacaopropostacliente',
                    verbose_name='Simulação origem',
                )),
                ('usuario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacao_proposta',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuário',
                )),
            ],
            options={
                'verbose_name': 'Histórico transação (proposta)',
                'verbose_name_plural': 'Históricos transação (proposta)',
                'ordering': ['-data_hora'],
            },
        ),
        migrations.CreateModel(
            name='HistoricoTransacaoContrato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('correlacao_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, verbose_name='ID de correlação')),
                ('acao', models.CharField(
                    choices=[
                        ('CRIACAO', 'Criação'),
                        ('TRANSICAO', 'Transição de etapa'),
                        ('EDICAO', 'Edição de dados'),
                        ('TABULACAO', 'Tabulação'),
                        ('ENTRADA_PENDENCIAS', 'Entrada em pendências'),
                        ('PENDENCIA_ABERTA', 'Pendência aberta'),
                        ('PENDENCIA_RESOLVIDA', 'Pendência resolvida'),
                    ],
                    db_index=True,
                    max_length=40,
                    verbose_name='Ação',
                )),
                ('etapa_anterior', models.CharField(blank=True, default='', max_length=20, verbose_name='Etapa anterior')),
                ('sub_anterior', models.CharField(blank=True, default='', max_length=40, verbose_name='Sub anterior')),
                ('etapa_nova', models.CharField(blank=True, default='', max_length=20, verbose_name='Etapa nova')),
                ('sub_nova', models.CharField(blank=True, default='', max_length=40, verbose_name='Sub nova')),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='Payload técnico')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('data_hora', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Data/hora')),
                ('carteira_clientes', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_contrato',
                    to='siape.carteiraclientes',
                    verbose_name='Carteira',
                )),
                ('contrato', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historico_transacoes_tecnicas',
                    to='contratos_v2.contratoexecucao',
                    verbose_name='Contrato',
                )),
                ('historico_transicao', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='transacao_tecnica',
                    to='contratos_v2.historicotransicaocontrato',
                    verbose_name='Transição linha do tempo',
                )),
                ('pendencia', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes',
                    to='contratos_v2.pendencia',
                    verbose_name='Pendência',
                )),
                ('proposta_origem', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_contrato',
                    to='contratos_v2.propostadados',
                    verbose_name='Proposta origem',
                )),
                ('solicitacao_digitacao', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacoes_contrato',
                    to='contratos_v2.solicitacaodigitacao',
                    verbose_name='Solicitação digitação',
                )),
                ('usuario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='historico_transacao_contrato',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuário',
                )),
            ],
            options={
                'verbose_name': 'Histórico transação (contrato)',
                'verbose_name_plural': 'Históricos transação (contrato)',
                'ordering': ['-data_hora'],
            },
        ),
        migrations.AddIndex(
            model_name='historiotransacaosimulacao',
            index=models.Index(fields=['solicitacao', '-data_hora'], name='idx_htsim_sol_dh'),
        ),
        migrations.AddIndex(
            model_name='historiotransacaosimulacao',
            index=models.Index(fields=['acao', '-data_hora'], name='idx_htsim_acao_dh'),
        ),
        migrations.AddIndex(
            model_name='historiotransacaoproposta',
            index=models.Index(fields=['proposta', '-data_hora'], name='idx_htprop_prop_dh'),
        ),
        migrations.AddIndex(
            model_name='historiotransacaoproposta',
            index=models.Index(fields=['acao', '-data_hora'], name='idx_htprop_acao_dh'),
        ),
        migrations.AddIndex(
            model_name='historiotransacaocontrato',
            index=models.Index(fields=['contrato', '-data_hora'], name='idx_htctr_ctr_dh'),
        ),
        migrations.AddIndex(
            model_name='historiotransacaocontrato',
            index=models.Index(fields=['acao', '-data_hora'], name='idx_htctr_acao_dh'),
        ),
        migrations.AddIndex(
            model_name='historiotransacaocontrato',
            index=models.Index(fields=['-data_hora', 'acao'], name='idx_htctr_dh_acao'),
        ),
    ]
