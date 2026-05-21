"""
Management command para criar tabulações iniciais baseadas no fluxograma
"""
from django.core.management.base import BaseCommand
from apps.operacional.contratos.models import TabulacaoContrato

class Command(BaseCommand):
    help = 'Cria as tabulações iniciais do sistema de contratos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove todas as tabulações existentes antes de criar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Criando tabulações iniciais...'))
        
        if options['reset']:
            self.stdout.write(self.style.WARNING('Removendo tabulações existentes...'))
            TabulacaoContrato.objects.all().delete()
        
        tabulacoes = [
            {'nome': 'ENVIADO', 'ordem': 1, 'cor': '#007bff', 'descricao': 'Vendedor enviou contrato'},
            {'nome': 'INCOMPLETO', 'ordem': 2, 'cor': '#ffc107', 'descricao': 'Falta dados/documentos'},
            {'nome': 'FORMALIZACAO ENVIADA', 'ordem': 3, 'cor': '#17a2b8', 'descricao': 'Operacional enviou link de formalização'},
            {'nome': 'CLIENTE ASSINOU', 'ordem': 4, 'cor': '#28a745', 'descricao': 'Vendedor informou que cliente assinou'},
            {'nome': 'EM ANALISE', 'ordem': 5, 'cor': '#6f42c1', 'descricao': 'Operacional analisando valores'},
            {'nome': 'ANUENCIA/AVERBACAO', 'ordem': 6, 'cor': '#e83e8c', 'descricao': 'Processo SIAPE/INSS'},
            {'nome': 'LIBERACAO', 'ordem': 7, 'cor': '#20c997', 'descricao': 'Contrato liberado'},
            {'nome': 'ENVIO PARA PAGAMENTO', 'ordem': 8, 'cor': '#fd7e14', 'descricao': 'Enviado para pagamento'},
            {'nome': 'PAGO', 'ordem': 9, 'cor': '#28a745', 'descricao': 'Contrato pago'},
            {'nome': 'NAO PAGO/CANCELADO', 'ordem': 10, 'cor': '#dc3545', 'descricao': 'Não pago ou cancelado'},
            {'nome': 'CLIENTE FINALIZADO', 'ordem': 11, 'cor': '#28a745', 'descricao': 'Cliente finalizado com sucesso'},
            {'nome': 'CANCELADO/DESISTIU', 'ordem': 12, 'cor': '#6c757d', 'descricao': 'Cliente desistiu ou banco rejeitou'},
        ]
        
        created_count = 0
        for tab in tabulacoes:
            obj, created = TabulacaoContrato.objects.get_or_create(
                nome=tab['nome'],
                defaults={
                    'ordem': tab['ordem'],
                    'cor': tab['cor'],
                    'status': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Tabulação criada: {tab["nome"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'  Tabulação já existe: {tab["nome"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ {created_count} tabulações criadas com sucesso!'))
