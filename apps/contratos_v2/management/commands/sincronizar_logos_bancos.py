# -*- coding: utf-8 -*-
"""Preenche domínios (COMPE/título) e baixa logos dos bancos do catálogo."""
from django.core.management.base import BaseCommand

from apps.contratos_v2.models import Banco
from apps.contratos_v2.services import banco_logo as logo_svc


class Command(BaseCommand):
    help = (
        'Aplica domínios COMPE/título nos Banco existentes e sincroniza logos '
        '(requer LOGO_DEV_TOKEN e/ou BRANDFETCH_API_KEY no .env).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apenas-dominios',
            action='store_true',
            help='Só preenche codigo/dominio/nome_curto, sem baixar imagens.',
        )
        parser.add_argument(
            '--forcar',
            action='store_true',
            help='Rebaixa logo mesmo se já existir arquivo local.',
        )
        parser.add_argument(
            '--banco-id',
            type=int,
            default=None,
            help='Processar apenas um banco (pk).',
        )

    def handle(self, *args, **options):
        n_dom = logo_svc.aplicar_dominios_todos_bancos()
        self.stdout.write(self.style.SUCCESS(f'Domínios atualizados em {n_dom} banco(s).'))

        if options['apenas_dominios']:
            return

        qs = Banco.objects.filter(status=True).exclude(dominio__isnull=True).exclude(dominio='')
        if options['banco_id']:
            qs = qs.filter(pk=options['banco_id'])

        ok = err = 0
        for b in qs:
            sucesso, msg = logo_svc.sincronizar_logo_banco(b, forcar=options['forcar'])
            if sucesso:
                ok += 1
                self.stdout.write(f'  OK {b.titulo}: {msg}')
            else:
                err += 1
                self.stdout.write(self.style.WARNING(f'  -- {b.titulo}: {msg}'))

        self.stdout.write(self.style.SUCCESS(f'Logos: {ok} ok, {err} falha(s).'))
