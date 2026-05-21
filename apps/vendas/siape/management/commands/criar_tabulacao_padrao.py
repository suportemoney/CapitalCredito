"""
Comando para criar tabulação padrão do CRM
"""
from django.core.management.base import BaseCommand
from apps.vendas.siape.models import TabulacaoCRM

class Command(BaseCommand):
    help = 'Cria a tabulação padrão "EM NEGOCIACAO" do CRM'

    def handle(self, *args, **options):
        tabulacao, created = TabulacaoCRM.objects.get_or_create(
            nome='EM NEGOCIACAO',
            defaults={
                'ordem': 1,
                'cor': '#007bff',
                'status': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Tabulação "EM NEGOCIACAO" criada com sucesso!'))
        else:
            self.stdout.write(self.style.WARNING('Tabulação "EM NEGOCIACAO" já existe.'))

