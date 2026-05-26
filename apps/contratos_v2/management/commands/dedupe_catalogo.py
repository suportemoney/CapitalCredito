# -*- coding: utf-8 -*-
"""Consolida duplicatas legadas no catálogo (Banco / Convenio / Produto).

Critério de canonicidade: mantém o registro mais ANTIGO (menor pk) cujo título
normalizado (Lower + colapso de espaços) seja idêntico. Os demais são tratados
como duplicatas: suas FKs de `TabelaCms` são reapontadas para o canônico e o
registro duplicado fica com `status=False` (soft delete).

Uso:
    python manage.py dedupe_catalogo            # dry-run (apenas mostra o plano)
    python manage.py dedupe_catalogo --apply    # executa em transação atômica
    python manage.py dedupe_catalogo --apply --modelo banco
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contratos_v2.models import Banco, Convenio, Produto, TabelaCms


def _normalizar(v: str) -> str:
    """Mesma normalização usada pelas APIs de catálogo."""
    return ' '.join((v or '').strip().split()).lower()


class Command(BaseCommand):
    help = 'Consolida duplicatas de Banco / Convenio / Produto pelo título normalizado.'

    MODELOS = {
        'banco': (Banco, 'banco'),
        'convenio': (Convenio, 'convenio'),
        'produto': (Produto, 'produto'),
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Executa as alterações. Sem este flag o comando roda em dry-run.',
        )
        parser.add_argument(
            '--modelo',
            choices=list(self.MODELOS.keys()) + ['all'],
            default='all',
            help='Escopo: banco | convenio | produto | all (padrão).',
        )

    def handle(self, *args, **opts):
        apply_changes = opts['apply']
        escopo = opts['modelo']

        modos = [escopo] if escopo != 'all' else list(self.MODELOS.keys())
        relatorios = []

        for chave in modos:
            model_cls, fk_name = self.MODELOS[chave]
            relatorios.append(self._processar(model_cls, fk_name, apply_changes))

        total = sum(r['duplicatas'] for r in relatorios)
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Resumo: {total} duplicatas detectadas ==="
        ))
        for r in relatorios:
            self.stdout.write(
                f"  {r['modelo']:<10} grupos={r['grupos']:<4} duplicatas={r['duplicatas']:<4} "
                f"tabelas_cms_reapontadas={r['fks_reapontadas']}"
            )
        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "\nDry-run: nada foi gravado. Rode com --apply para consolidar."
            ))

    def _processar(self, model_cls, fk_name, apply_changes):
        nome = model_cls.__name__
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n▶ {nome}"))

        # Agrupa por título normalizado.
        grupos = {}
        for obj in model_cls.objects.all().order_by('pk'):
            chave = _normalizar(obj.titulo)
            if not chave:
                continue
            grupos.setdefault(chave, []).append(obj)

        duplicados = {k: v for k, v in grupos.items() if len(v) > 1}
        total_duplicatas = sum(len(v) - 1 for v in duplicados.values())
        fks_reapontadas = 0

        if not duplicados:
            self.stdout.write('  Nenhuma duplicata.')
            return {
                'modelo': nome, 'grupos': 0, 'duplicatas': 0, 'fks_reapontadas': 0,
            }

        with transaction.atomic():
            for chave, registros in duplicados.items():
                canonico = registros[0]  # menor pk
                perdedores = registros[1:]
                perdedores_ids = [p.pk for p in perdedores]

                # Reaponta FKs em TabelaCms para o canônico.
                qs = TabelaCms.objects.filter(**{f'{fk_name}_id__in': perdedores_ids})
                qtd = qs.count()
                fks_reapontadas += qtd

                self.stdout.write(
                    f"  [{chave}] canonico=#{canonico.pk} '{canonico.titulo}' "
                    f"duplicatas={perdedores_ids} cms_reapontadas={qtd}"
                )
                if apply_changes:
                    qs.update(**{f'{fk_name}_id': canonico.pk})
                    # Inativa os duplicados (soft delete).
                    model_cls.objects.filter(pk__in=perdedores_ids).update(status=False)

            if not apply_changes:
                # Desfaz qualquer efeito colateral (defesa em profundidade).
                transaction.set_rollback(True)

        return {
            'modelo': nome,
            'grupos': len(duplicados),
            'duplicatas': total_duplicatas,
            'fks_reapontadas': fks_reapontadas,
        }
