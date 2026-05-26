# -*- coding: utf-8 -*-
"""Legado removido: modelo TabulacaoContrato não existe mais neste app."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando descontinuado (estrutura antiga de tabulações removida).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Nada a fazer: use fluxo ContratoExecucao / fases em fluxo_constants.'))
