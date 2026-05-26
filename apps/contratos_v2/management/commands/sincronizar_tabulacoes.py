# -*- coding: utf-8 -*-
"""
Sincroniza tabulações/estados desatualizados em todas as entidades operacionais.

Corrige:
  1. ContratoExecucao — campo `fase` (legado) dessincronizado de etapa+sub
  2. CarteiraClientes — `tabulacao_operacional` e `tags_operacionais` (agregado)
  3. CarteiraClientes — `tag_proposta_container` e `tag_status_operacional`
     reconstruídos a partir das simulações e digitações vinculadas
  4. SolicitacaoPropostaCliente — estados com valores não reconhecidos (diagnóstico)
  5. SolicitacaoDigitacao — estados com valores não reconhecidos (diagnóstico)

Uso:
  python manage.py sincronizar_tabulacoes
  python manage.py sincronizar_tabulacoes --dry-run
  python manage.py sincronizar_tabulacoes --apenas-contratos
  python manage.py sincronizar_tabulacoes --apenas-carteiras
  python manage.py sincronizar_tabulacoes --apenas-diagnostico
  python manage.py sincronizar_tabulacoes --chunk-size 500
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contratos_v2.fluxo_constants import (
    EstadoSolicitacaoDigitacao,
    EstadoSolicitacaoProposta,
    EtapaOperacional,
)
from apps.contratos_v2.fluxo_transicoes import par_etapa_sub_valido, sincronizar_fase_legada
from apps.contratos_v2.models import (
    ContratoExecucao,
    SolicitacaoDigitacao,
    SolicitacaoPropostaCliente,
)
from apps.vendas.siape.models import CarteiraClientes


_ESTADOS_SIM_VALIDOS = {c[0] for c in EstadoSolicitacaoProposta.CHOICES}
_ESTADOS_DIG_VALIDOS = {c[0] for c in EstadoSolicitacaoDigitacao.CHOICES}
_ETAPAS_VALIDAS = {c[0] for c in EtapaOperacional.CHOICES}


class Command(BaseCommand):
    help = (
        'Sincroniza tabulações e estados operacionais desatualizados: '
        'fase de contratos, agregado de carteiras e diagnóstico de simulações/digitações.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas lista o que seria corrigido, sem gravar no banco.',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=200,
            help='Tamanho do lote para iteração. Padrão: 200.',
        )
        parser.add_argument(
            '--apenas-contratos',
            action='store_true',
            help='Executa somente a sincronização de fase dos ContratoExecucao.',
        )
        parser.add_argument(
            '--apenas-carteiras',
            action='store_true',
            help='Executa somente o recálculo do agregado das CarteiraClientes.',
        )
        parser.add_argument(
            '--apenas-diagnostico',
            action='store_true',
            help='Executa somente o diagnóstico de estados inválidos (não grava nada).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        chunk = options['chunk_size'] or 200
        so_contratos = options['apenas_contratos']
        so_carteiras = options['apenas_carteiras']
        so_diag = options['apenas_diagnostico']

        # Se nenhum filtro específico, roda tudo
        tudo = not (so_contratos or so_carteiras or so_diag)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODO DRY-RUN — nada será gravado ==='))

        if tudo or so_contratos:
            self._sincronizar_contratos(dry_run, chunk)

        if tudo or so_carteiras:
            self._sincronizar_carteiras(dry_run, chunk)

        if tudo or so_diag:
            self._diagnosticar_simulacoes(chunk)
            self._diagnosticar_digitacoes(chunk)

        self.stdout.write(self.style.SUCCESS('\nConcluído.'))

    # ──────────────────────────────────────────────
    # 1. ContratoExecucao — sincronizar campo `fase`
    # ──────────────────────────────────────────────
    def _sincronizar_contratos(self, dry_run, chunk):
        self.stdout.write('\n[1/3] Sincronizando fase legada de ContratoExecucao...')

        qs = (
            ContratoExecucao.objects
            .filter(status=True)
            .exclude(etapa_operacional=None)
            .only('id', 'fase', 'etapa_operacional', 'sub_status_operacional')
            .order_by('id')
        )
        total = qs.count()
        self.stdout.write(f'     Contratos ativos encontrados: {total}')

        corrigidos = 0
        invalidos = 0

        for ce in qs.iterator(chunk_size=chunk):
            if not par_etapa_sub_valido(ce.etapa_operacional, ce.sub_status_operacional):
                invalidos += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  [INVÁLIDO] contrato_id={ce.id} '
                        f'etapa={ce.etapa_operacional} sub={ce.sub_status_operacional}'
                    )
                )
                continue

            # Calcula fase esperada
            fase_antes = ce.fase
            sincronizar_fase_legada(ce)
            fase_depois = ce.fase

            if fase_antes == fase_depois:
                continue

            corrigidos += 1
            self.stdout.write(
                f'  contrato_id={ce.id}: fase {fase_antes!r} → {fase_depois!r}'
            )
            if not dry_run:
                ContratoExecucao.objects.filter(pk=ce.pk).update(fase=fase_depois)

        self.stdout.write(
            self.style.SUCCESS(f'  Contratos corrigidos: {corrigidos} | inválidos: {invalidos}')
        )

    # ──────────────────────────────────────────────
    # 2. CarteiraClientes — recalcular agregado operacional
    # ──────────────────────────────────────────────
    def _sincronizar_carteiras(self, dry_run, chunk):
        self.stdout.write('\n[2/3] Recalculando agregado operacional de CarteiraClientes...')

        try:
            from apps.vendas.siape.services.operacional_agregado import (
                construir_agregado_operacional,
                sincronizar_agregado_operacional,
            )
        except ImportError as exc:
            self.stdout.write(self.style.ERROR(f'  Não foi possível importar o serviço: {exc}'))
            return

        qs = (
            CarteiraClientes.objects
            .filter(status='ATIVO')
            .only('id', 'tabulacao_operacional', 'tags_operacionais',
                  'tag_proposta_container', 'tag_status_operacional',
                  'status_comercial', 'cliente_operacional_id', 'cliente_id')
            .select_related('cliente')
            .order_by('id')
        )
        total = qs.count()
        self.stdout.write(f'     Carteiras ativas encontradas: {total}')

        atualizadas = 0
        erros = 0

        for cart in qs.iterator(chunk_size=chunk):
            try:
                novo_agregado = construir_agregado_operacional(cart)
                nova_tab = novo_agregado['tabulacao_operacional']
                import json
                novas_tags = json.dumps(novo_agregado['tags_operacionais'], ensure_ascii=False)

                mudou = (
                    cart.tabulacao_operacional != nova_tab
                    or cart.tags_operacionais != novas_tags
                )

                if not mudou:
                    continue

                atualizadas += 1
                self.stdout.write(
                    f'  carteira_id={cart.id}: tab {cart.tabulacao_operacional!r} → {nova_tab!r}'
                )

                if not dry_run:
                    with transaction.atomic():
                        sincronizar_agregado_operacional(cart, salvar=True)

            except Exception as exc:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(f'  [ERRO] carteira_id={cart.id}: {exc}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'  Carteiras atualizadas: {atualizadas} | erros: {erros}')
        )

    # ──────────────────────────────────────────────
    # 3a. Diagnóstico SolicitacaoPropostaCliente
    # ──────────────────────────────────────────────
    def _diagnosticar_simulacoes(self, chunk):
        self.stdout.write('\n[3a/3] Diagnóstico de estados de SolicitacaoPropostaCliente...')

        invalidos = 0
        total = SolicitacaoPropostaCliente.objects.count()

        qs = (
            SolicitacaoPropostaCliente.objects
            .only('id', 'estado')
            .order_by('id')
        )

        for sol in qs.iterator(chunk_size=chunk):
            if sol.estado not in _ESTADOS_SIM_VALIDOS:
                invalidos += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  [INVÁLIDO] simulacao_id={sol.id} estado={sol.estado!r}'
                        f' (válidos: {sorted(_ESTADOS_SIM_VALIDOS)})'
                    )
                )

        if invalidos == 0:
            self.stdout.write(
                self.style.SUCCESS(f'  OK — {total} simulações, nenhum estado inválido.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'  {invalidos}/{total} simulações com estado não reconhecido.')
            )

    # ──────────────────────────────────────────────
    # 3b. Diagnóstico SolicitacaoDigitacao
    # ──────────────────────────────────────────────
    def _diagnosticar_digitacoes(self, chunk):
        self.stdout.write('\n[3b/3] Diagnóstico de estados de SolicitacaoDigitacao...')

        invalidos = 0
        total = SolicitacaoDigitacao.objects.count()

        qs = (
            SolicitacaoDigitacao.objects
            .only('id', 'estado')
            .order_by('id')
        )

        for sol in qs.iterator(chunk_size=chunk):
            if sol.estado not in _ESTADOS_DIG_VALIDOS:
                invalidos += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  [INVÁLIDO] digitacao_id={sol.id} estado={sol.estado!r}'
                        f' (válidos: {sorted(_ESTADOS_DIG_VALIDOS)})'
                    )
                )

        if invalidos == 0:
            self.stdout.write(
                self.style.SUCCESS(f'  OK — {total} digitações, nenhum estado inválido.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'  {invalidos}/{total} digitações com estado não reconhecido.')
            )
