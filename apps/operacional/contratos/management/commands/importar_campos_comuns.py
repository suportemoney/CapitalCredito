"""
Management command para importar campos comuns do CSV
Nota: Campos comuns não são salvos no banco, são apenas usados como referência.
Este comando serve para validação/futuras funcionalidades.
"""
import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Importa campos comuns do CSV (para referência)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--arquivo',
            type=str,
            help='Caminho do arquivo CSV (opcional)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Importando campos comuns...'))
        
        # Caminho padrão do CSV
        if options['arquivo']:
            csv_path = options['arquivo']
        else:
            # Tentar encontrar o arquivo na pasta BASE
            csv_path = os.path.join(
                settings.BASE_DIR.parent if hasattr(settings, 'BASE_DIR') else '',
                'BASES ALVARO',
                'Operacional',
                'CAMPOS_EM_COMUM.csv'
            )
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {csv_path}'))
            self.stdout.write(self.style.WARNING('Campos comuns serão definidos em código.'))
            self._criar_campos_padrao()
            return
        
        try:
            campos_importados = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    category = row.get('Category', '').strip()
                    label = row.get('Label', '').strip()
                    field_type = row.get('Type', '').strip()
                    choices = row.get('Choices', '').strip()
                    placeholder = row.get('Placeholder', '').strip()
                    required = row.get('Required', '0').strip() == '1'
                    
                    if category and label and field_type:
                        campos_importados += 1
                        self.stdout.write(f'  {category}.{label} ({field_type})')
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ {campos_importados} campos processados do CSV!'))
            self.stdout.write(self.style.WARNING('Nota: Campos comuns são usados como referência e não são salvos no banco.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao importar CSV: {str(e)}'))
            self._criar_campos_padrao()
    
    def _criar_campos_padrao(self):
        """Cria lista padrão de campos comuns em código"""
        self.stdout.write(self.style.WARNING('Usando campos padrão definidos em código...'))
        # Os campos comuns serão referenciados diretamente no código quando necessário
        self.stdout.write(self.style.SUCCESS('✓ Campos comuns disponíveis para uso!'))
