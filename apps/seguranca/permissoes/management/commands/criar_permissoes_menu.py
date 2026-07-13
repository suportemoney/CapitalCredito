"""
Management command para criar permissões baseadas exatamente no menu lateral.
Cria permissões na ordem correta para que os IDs correspondam aos códigos do menu.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from apps.seguranca.permissoes.models import Acesso, AcessoHierarquia
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Cria permissões baseadas no menu lateral com IDs exatos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove todas as permissões existentes antes de criar',
        )
        parser.add_argument(
            '--aplicar-superuser',
            action='store_true',
            help='Aplica todas as permissões aos superusers',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando criação de permissões do menu lateral...'))
        
        if options['reset']:
            self.stdout.write(self.style.WARNING('Removendo permissões existentes...'))
            AcessoHierarquia.objects.all().delete()
            Acesso.objects.all().delete()
            # Resetar auto-increment do MySQL
            with connection.cursor() as cursor:
                table_name = Acesso._meta.db_table
                cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1;")
                self.stdout.write(self.style.SUCCESS(f'✓ Auto-increment resetado para tabela {table_name}'))
        
        # Estrutura EXATA do menu lateral com códigos esperados
        # Nota: Códigos duplicados (SCT6, SS5, SS25) são a mesma permissão usada em contextos diferentes
        permissoes_menu = [
            # CATEGORIAS (CT) - IDs: 1-5
            {'codigo': 'CT1', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'GERAL', 'descricao': 'Categoria Geral do sistema'},
            {'codigo': 'CT2', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'RECURSOS HUMANOS', 'descricao': 'Categoria de Recursos Humanos'},
            {'codigo': 'CT3', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'SEGURANCA', 'descricao': 'Categoria de Segurança'},
            {'codigo': 'CT4', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'TESOURARIA', 'descricao': 'Categoria de Tesouraria'},
            {'codigo': 'CT5', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'VENDAS', 'descricao': 'Categoria de Vendas'},
            
            # SUBCATEGORIAS (SCT) - IDs: 2, 3, 4, 5, 6, 12, 13
            {'codigo': 'SCT2', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'RECURSOS HUMANOS | ADMINISTRATIVO', 'descricao': 'SubCategoria Administrativa', 'pai': 'CT2'},
            {'codigo': 'SCT3', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'RECURSOS HUMANOS | FUNCIONARIOS', 'descricao': 'SubCategoria de Funcionários', 'pai': 'CT2'},
            {'codigo': 'SCT4', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'RECURSOS HUMANOS | USUARIOS', 'descricao': 'SubCategoria de Usuários', 'pai': 'CT2'},
            {'codigo': 'SCT5', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'SEGURANCA | PERMISSOES', 'descricao': 'SubCategoria de Permissões', 'pai': 'CT3'},
            {'codigo': 'SCT6', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'COMUNICADOS / FINANCEIRO GERAL', 'descricao': 'SubCategoria de Comunicados (CT1) e Financeiro Geral (CT4)', 'pai': 'CT1'},
            {'codigo': 'SCT12', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'VENDAS | SIAPE', 'descricao': 'SubCategoria SIAPE', 'pai': 'CT5'},
            {'codigo': 'SCT13', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'VENDAS | FINANCEIRO VENDAS', 'descricao': 'SubCategoria Financeiro Vendas', 'pai': 'CT5'},
            {'codigo': 'SCT52', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'FINANCEIRO | PAGAMENTO TC', 'descricao': 'Sistema para pagar TC e enviar ranking', 'pai': 'SCT13'},
            
            # SESSÕES (SS) - IDs: 3, 5, 7, 8, 9, 10, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31
            {'codigo': 'SS3', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'RECURSOS HUMANOS | ADMINISTRATIVO | GERENCIAMENTO GERAL', 'descricao': 'Acesso ao gerenciamento administrativo geral', 'pai': 'SCT2'},
            {'codigo': 'SS5', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'FUNCIONARIOS / PERMISSOES', 'descricao': 'Acesso a funcionários e permissões', 'pai': 'SCT3'},
            {'codigo': 'SS7', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'RECURSOS HUMANOS | USUARIOS | GERENCIAR', 'descricao': 'Acesso ao gerenciador de usuários', 'pai': 'SCT4'},
            {'codigo': 'SS8', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | FINANCEIRO GERAL | ADICIONAR A PAGAR', 'descricao': 'Acesso para adicionar contas a pagar', 'pai': 'SCT6'},
            {'codigo': 'SS9', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | FINANCEIRO GERAL | ADICIONAR A RECEBER', 'descricao': 'Acesso para adicionar contas a receber', 'pai': 'SCT6'},
            {'codigo': 'SS10', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | FINANCEIRO GERAL | GERENCIAMENTO GERAL', 'descricao': 'Acesso ao gerenciamento financeiro geral', 'pai': 'SCT6'},
            {'codigo': 'SS14', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'GERAL | COMUNICADOS | MURAL', 'descricao': 'Acesso ao mural de comunicados', 'pai': 'SCT6'},
            {'codigo': 'SS15', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'GERAL | COMUNICADOS | GERENCIADOR', 'descricao': 'Acesso ao gerenciador de comunicados', 'pai': 'SCT6'},
            {'codigo': 'SS24', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | RANKING', 'descricao': 'Acesso ao ranking SIAPE', 'pai': 'SCT12'},
            {'codigo': 'SS25', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | CONSULTA / CAMPANHAS', 'descricao': 'Acesso à consulta de cliente e campanhas SIAPE', 'pai': 'SCT12'},
            {'codigo': 'SS26', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | CRM', 'descricao': 'Acesso ao CRM SIAPE', 'pai': 'SCT12'},
            {'codigo': 'SS27', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | FINANCEIRO VENDAS | GERENCIAMENTO DE VENDAS', 'descricao': 'Acesso ao gerenciamento financeiro de vendas', 'pai': 'SCT13'},
            {'codigo': 'SS28', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | PRODUTOS', 'descricao': 'Acesso aos produtos SIAPE', 'pai': 'SCT12'},
            {'codigo': 'SS29', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | FINANCEIRO VENDAS | CLASSIFICADOR', 'descricao': 'Acesso ao classificador de vendas', 'pai': 'SCT13'},
            {'codigo': 'SS30', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | METAS SIAPE', 'descricao': 'Acesso às metas SIAPE', 'pai': 'SCT12'},
            {'codigo': 'SS31', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | RESPONSAVEIS REV/CHEC', 'descricao': 'Acesso aos responsáveis de revisão/checagem', 'pai': 'SCT12'},
        ]
        
        # Mapeamento de hierarquias adicionais (SCT6 também é filho de CT4)
        hierarquias_extra = [
            {'pai': 'CT4', 'filho': 'SCT6'},  # SCT6 também é filho de CT4 (Financeiro Geral)
        ]
        
        acessos_criados = {}
        hierarquias_criadas = []
        
        with transaction.atomic():
            # FASE 1: Criar todas as permissões na ordem exata
            self.stdout.write(self.style.SUCCESS('\n--- Fase 1: Criando Permissões ---'))
            
            # Processar permissões únicas (evitar duplicatas)
            permissoes_unicas = {}
            for perm_data in permissoes_menu:
                codigo = perm_data['codigo']
                if codigo not in permissoes_unicas:
                    permissoes_unicas[codigo] = perm_data
            
            for codigo_esperado, perm_data in permissoes_unicas.items():
                tipo = perm_data['tipo']
                nome = perm_data['nome']
                descricao = perm_data.get('descricao', '')
                
                # Extrair número do código esperado
                numero_esperado = int(''.join(filter(str.isdigit, codigo_esperado)))
                
                # Verificar se já existe com o ID correto
                acesso_existente = Acesso.objects.filter(id=numero_esperado).first()
                
                if acesso_existente:
                    # Atualizar existente
                    acesso_existente.tipo = tipo
                    acesso_existente.nome = nome
                    acesso_existente.descricao = descricao
                    acesso_existente.status = True
                    acesso_existente.save()
                    acesso = acesso_existente
                    self.stdout.write(self.style.WARNING(f'  → Atualizado: {acesso.gerar_codigo()} - {acesso.nome}'))
                else:
                    # Criar novo com ID específico (usando SQL direto para MySQL)
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f"INSERT INTO {Acesso._meta.db_table} (id, nome, tipo, descricao, status, data_criacao) VALUES (%s, %s, %s, %s, %s, NOW())",
                                [numero_esperado, nome, tipo, descricao, True]
                            )
                        
                        acesso = Acesso.objects.get(id=numero_esperado)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Criado: {acesso.gerar_codigo()} - {acesso.nome}'))
                    except Exception as e:
                        # Se falhar, criar normalmente e atualizar depois
                        acesso = Acesso.objects.create(
                            nome=nome,
                            tipo=tipo,
                            descricao=descricao,
                            status=True
                        )
                        # Se o ID não for o esperado, tentar atualizar manualmente
                        if acesso.id != numero_esperado:
                            self.stdout.write(self.style.WARNING(f'  ⚠ ID gerado ({acesso.id}) diferente do esperado ({numero_esperado}) para {codigo_esperado}'))
                
                acessos_criados[codigo_esperado] = acesso
            
            # FASE 2: Criar hierarquias
            self.stdout.write(self.style.SUCCESS('\n--- Fase 2: Criando Hierarquias ---'))
            
            for perm_data in permissoes_menu:
                if 'pai' in perm_data:
                    codigo_filho = perm_data['codigo']
                    codigo_pai = perm_data['pai']
                    
                    filho = acessos_criados.get(codigo_filho)
                    pai = acessos_criados.get(codigo_pai)
                    
                    if filho and pai:
                        hierarquia, created = AcessoHierarquia.objects.get_or_create(
                            pai=pai,
                            defaults={'status': True}
                        )
                        
                        if filho.id not in hierarquia.filhos.values_list('id', flat=True):
                            hierarquia.filhos.add(filho)
                            if created:
                                hierarquias_criadas.append(f'{pai.gerar_codigo()} -> {filho.gerar_codigo()}')
                                self.stdout.write(self.style.SUCCESS(f'  ✓ Hierarquia: {pai.gerar_codigo()} -> {filho.gerar_codigo()}'))
            
            # Criar hierarquias extras (SCT6 também é filho de CT4)
            for hier_extra in hierarquias_extra:
                codigo_pai = hier_extra['pai']
                codigo_filho = hier_extra['filho']
                
                pai = acessos_criados.get(codigo_pai)
                filho = acessos_criados.get(codigo_filho)
                
                if filho and pai:
                    hierarquia, created = AcessoHierarquia.objects.get_or_create(
                        pai=pai,
                        defaults={'status': True}
                    )
                    
                    if filho.id not in hierarquia.filhos.values_list('id', flat=True):
                        hierarquia.filhos.add(filho)
                        if not created:
                            hierarquias_criadas.append(f'{pai.gerar_codigo()} -> {filho.gerar_codigo()}')
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Hierarquia extra: {pai.gerar_codigo()} -> {filho.gerar_codigo()}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ {len(acessos_criados)} permissões criadas/atualizadas'))
        self.stdout.write(self.style.SUCCESS(f'✓ {len(hierarquias_criadas)} hierarquias criadas'))
        
        # Aplicar permissões aos superusers
        if options['aplicar_superuser']:
            from apps.seguranca.permissoes.models import ControleAcessos
            self.stdout.write(self.style.SUCCESS('\nAplicando permissões aos superusers...'))
            superusers = User.objects.filter(is_superuser=True)
            
            for superuser in superusers:
                controle, created = ControleAcessos.objects.get_or_create(
                    user=superuser,
                    defaults={'status': True}
                )
                
                if not controle.status:
                    controle.status = True
                    controle.save()
                
                todas_permissoes = Acesso.objects.filter(status=True)
                controle.acessos.set(todas_permissoes)
                
                self.stdout.write(self.style.SUCCESS(f'✓ Permissões aplicadas ao superuser: {superuser.username}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Permissões do menu lateral criadas com sucesso!'))
        
        # Mostrar mapeamento
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('MAPEAMENTO DE CÓDIGOS CRIADOS:'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        categorias = Acesso.objects.filter(tipo=Acesso.CATEGORIA_APP).order_by('id')
        self.stdout.write(self.style.SUCCESS('\n📁 CATEGORIAS (CT):'))
        for cat in categorias:
            self.stdout.write(f'  ✓ {cat.gerar_codigo():4} - {cat.nome}')
        
        subcategorias = Acesso.objects.filter(tipo=Acesso.SUBCATEGORIA_RENDER).order_by('id')
        self.stdout.write(self.style.SUCCESS('\n📂 SUBCATEGORIAS (SCT):'))
        for sct in subcategorias:
            self.stdout.write(f'  ✓ {sct.gerar_codigo():5} - {sct.nome}')
        
        sessoes = Acesso.objects.filter(tipo=Acesso.SESSAO_SECTION).order_by('id')
        self.stdout.write(self.style.SUCCESS('\n📄 SESSÕES (SS):'))
        for ss in sessoes:
            self.stdout.write(f'  ✓ {ss.gerar_codigo():4} - {ss.nome}')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))

