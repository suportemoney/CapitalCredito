"""
Management command para sincronizar permissões com o servidor de teste.
Garante que os IDs, nomes e tipos sejam exatamente iguais aos do servidor de teste.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from apps.seguranca.permissoes.models import Acesso, AcessoHierarquia, ControleAcessos
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Sincroniza permissões com o servidor de teste (mesmos IDs, nomes e tipos)'

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
        self.stdout.write(self.style.SUCCESS('Iniciando sincronização de permissões com servidor de teste...'))
        
        if options['reset']:
            self.stdout.write(self.style.WARNING('Removendo permissões existentes...'))
            # Remover relacionamentos primeiro
            ControleAcessos.objects.all().delete()
            AcessoHierarquia.objects.all().delete()
            Acesso.objects.all().delete()
            # Resetar auto-increment do MySQL
            with connection.cursor() as cursor:
                table_name = Acesso._meta.db_table
                cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1;")
                self.stdout.write(self.style.SUCCESS(f'✓ Auto-increment resetado para tabela {table_name}'))
        
        # Estrutura EXATA do servidor de teste
        # Baseado nos dados fornecidos pelo usuário
        permissoes_teste = [
            # CATEGORIAS (CT) - IDs: 1-5
            {'id': 1, 'codigo': 'CT1', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'GERAL', 'descricao': 'Categoria Geral do sistema'},
            {'id': 2, 'codigo': 'CT2', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'RECURSOS HUMANOS', 'descricao': 'Categoria de Recursos Humanos'},
            {'id': 3, 'codigo': 'CT3', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'SEGURANCA', 'descricao': 'Categoria de Segurança'},
            {'id': 4, 'codigo': 'CT4', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'TESOURARIA', 'descricao': 'Categoria de Tesouraria'},
            {'id': 5, 'codigo': 'CT5', 'tipo': Acesso.CATEGORIA_APP, 'nome': 'VENDAS', 'descricao': 'Categoria de Vendas'},
            
            # SUBCATEGORIAS (SCT) - IDs: 6-13
            {'id': 6, 'codigo': 'SCT6', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'GERAL | COMUNICADOS', 'descricao': 'SubCategoria de Comunicados', 'pai': 'CT1'},
            {'id': 7, 'codigo': 'SCT7', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'RECURSOS HUMANOS | ADMINISTRATIVO', 'descricao': 'SubCategoria Administrativa', 'pai': 'CT2'},
            {'id': 8, 'codigo': 'SCT8', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'RECURSOS HUMANOS | FUNCIONARIOS', 'descricao': 'SubCategoria de Funcionários', 'pai': 'CT2'},
            {'id': 9, 'codigo': 'SCT9', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'RECURSOS HUMANOS | USUARIOS', 'descricao': 'SubCategoria de Usuários', 'pai': 'CT2'},
            {'id': 10, 'codigo': 'SCT10', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'SEGURANCA | PERMISSOES', 'descricao': 'SubCategoria de Permissões', 'pai': 'CT3'},
            {'id': 11, 'codigo': 'SCT11', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'TESOURARIA | FINANCEIRO GERAL', 'descricao': 'SubCategoria Financeiro Geral', 'pai': 'CT4'},
            {'id': 12, 'codigo': 'SCT12', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'VENDAS | SIAPE', 'descricao': 'SubCategoria SIAPE', 'pai': 'CT5'},
            {'id': 13, 'codigo': 'SCT13', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'VENDAS | FINANCEIRO VENDAS', 'descricao': 'SubCategoria Financeiro Vendas', 'pai': 'CT5'},
            {'id': 44, 'codigo': 'SCT44', 'tipo': Acesso.SUBCATEGORIA_RENDER, 'nome': 'TESOURARIA | BONIFICACOES', 'descricao': 'SubCategoria Bonificações', 'pai': 'CT4'},
            
            # SESSÕES (SS) - IDs: 14-31, 45
            {'id': 14, 'codigo': 'SS14', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'GERAL | COMUNICADOS | MURAL', 'descricao': 'Acesso ao mural de comunicados', 'pai': 'SCT6'},
            {'id': 15, 'codigo': 'SS15', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'GERAL | COMUNICADOS | GERENCIADOR', 'descricao': 'Acesso ao gerenciador de comunicados', 'pai': 'SCT6'},
            {'id': 16, 'codigo': 'SS16', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'RECURSOS HUMANOS | ADMINISTRATIVO | GERENCIAMENTO GERAL', 'descricao': 'Acesso ao gerenciamento administrativo geral', 'pai': 'SCT7'},
            {'id': 17, 'codigo': 'SS17', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'RECURSOS HUMANOS | FUNCIONARIOS | NOVO ACESSO', 'descricao': 'Acesso para criar novo funcionário', 'pai': 'SCT8'},
            {'id': 18, 'codigo': 'SS18', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'RECURSOS HUMANOS | FUNCIONARIOS | GERENCIADOR', 'descricao': 'Acesso ao gerenciador de funcionários', 'pai': 'SCT8'},
            {'id': 19, 'codigo': 'SS19', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'RECURSOS HUMANOS | USUARIOS | GERENCIADOR', 'descricao': 'Acesso ao gerenciador de usuários', 'pai': 'SCT9'},
            {'id': 20, 'codigo': 'SS20', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'SEGURANCA | PERMISSOES | GERENCIAMENTO DE PERMISSOES', 'descricao': 'Acesso ao gerenciamento de permissões', 'pai': 'SCT10'},
            {'id': 21, 'codigo': 'SS21', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | FINANCEIRO GERAL | ADICIONAR A PAGAR', 'descricao': 'Acesso para adicionar contas a pagar', 'pai': 'SCT11'},
            {'id': 22, 'codigo': 'SS22', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | FINANCEIRO GERAL | ADICIONAR A RECEBER', 'descricao': 'Acesso para adicionar contas a receber', 'pai': 'SCT11'},
            {'id': 23, 'codigo': 'SS23', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | FINANCEIRO GERAL | GERENCIAMENTO GERAL', 'descricao': 'Acesso ao gerenciamento financeiro geral', 'pai': 'SCT11'},
            {'id': 24, 'codigo': 'SS24', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | RANKING', 'descricao': 'Acesso ao ranking SIAPE', 'pai': 'SCT12'},
            {'id': 25, 'codigo': 'SS25', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | CONSULTA CLIENTE', 'descricao': 'Acesso à consulta de cliente SIAPE', 'pai': 'SCT12'},
            {'id': 26, 'codigo': 'SS26', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | CRM', 'descricao': 'Acesso ao CRM SIAPE', 'pai': 'SCT12'},
            {'id': 27, 'codigo': 'SS27', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | FINANCEIRO VENDAS | GERENCIAMENTO DE VENDAS', 'descricao': 'Acesso ao gerenciamento financeiro de vendas', 'pai': 'SCT13'},
            {'id': 28, 'codigo': 'SS28', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | PRODUTOS', 'descricao': 'Acesso aos produtos SIAPE', 'pai': 'SCT12'},
            {'id': 29, 'codigo': 'SS29', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | FINANCEIRO | CLASSIFICADOR', 'descricao': 'Acesso ao classificador de vendas', 'pai': 'SCT13'},
            {'id': 30, 'codigo': 'SS30', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | METAS', 'descricao': 'Acesso às metas SIAPE', 'pai': 'SCT12'},
            {'id': 31, 'codigo': 'SS31', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'VENDAS | SIAPE | RESP REP CHE', 'descricao': 'Acesso aos responsáveis de revisão/checagem', 'pai': 'SCT12'},
            {'id': 45, 'codigo': 'SS45', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | BONIFICACOES | CONFIG', 'descricao': 'Acesso à configuração de Bonificações (Regras, Vínculos, Reduções, Cálculos)', 'pai': 'SCT44'},
            {'id': 46, 'codigo': 'SS46', 'tipo': Acesso.SESSAO_SECTION, 'nome': 'TESOURARIA | BONIFICACOES | CALC', 'descricao': 'Acesso ao cálculo de Bonificações por mês', 'pai': 'SCT44'},
        ]
        
        acessos_criados = {}
        hierarquias_criadas = []
        
        with transaction.atomic():
            # FASE 1: Criar todas as permissões com IDs específicos
            self.stdout.write(self.style.SUCCESS('\n--- Fase 1: Criando Permissões com IDs Específicos ---'))
            
            for perm_data in permissoes_teste:
                id_esperado = perm_data['id']
                codigo = perm_data['codigo']
                tipo = perm_data['tipo']
                nome = perm_data['nome']
                descricao = perm_data.get('descricao', '')
                
                # Verificar se já existe com o ID correto
                acesso_existente = Acesso.objects.filter(id=id_esperado).first()
                
                if acesso_existente:
                    # Atualizar existente
                    acesso_existente.tipo = tipo
                    acesso_existente.nome = nome
                    acesso_existente.descricao = descricao
                    acesso_existente.status = True
                    acesso_existente.save()
                    acesso = acesso_existente
                    self.stdout.write(self.style.WARNING(f'  → Atualizado: {acesso.gerar_codigo()} (ID: {acesso.id}) - {acesso.nome}'))
                else:
                    # Criar novo com ID específico (usando SQL direto para MySQL)
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f"INSERT INTO {Acesso._meta.db_table} (id, nome, tipo, descricao, status, data_criacao) VALUES (%s, %s, %s, %s, %s, NOW())",
                                [id_esperado, nome, tipo, descricao, True]
                            )
                        
                        acesso = Acesso.objects.get(id=id_esperado)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Criado: {acesso.gerar_codigo()} (ID: {acesso.id}) - {acesso.nome}'))
                    except Exception as e:
                        # Se falhar, criar normalmente e tentar atualizar ID depois
                        self.stdout.write(self.style.ERROR(f'  ✗ Erro ao criar {codigo} com ID {id_esperado}: {str(e)}'))
                        # Tentar criar normalmente
                        acesso = Acesso.objects.create(
                            nome=nome,
                            tipo=tipo,
                            descricao=descricao,
                            status=True
                        )
                        if acesso.id != id_esperado:
                            self.stdout.write(self.style.WARNING(f'  ⚠ ID gerado ({acesso.id}) diferente do esperado ({id_esperado}) para {codigo}'))
                
                acessos_criados[codigo] = acesso
            
            # FASE 2: Criar hierarquias
            self.stdout.write(self.style.SUCCESS('\n--- Fase 2: Criando Hierarquias ---'))
            
            for perm_data in permissoes_teste:
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
                            hierarquias_criadas.append(f'{pai.gerar_codigo()} -> {filho.gerar_codigo()}')
                            self.stdout.write(self.style.SUCCESS(f'  ✓ Hierarquia: {pai.gerar_codigo()} -> {filho.gerar_codigo()}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ {len(acessos_criados)} permissões criadas/atualizadas'))
        self.stdout.write(self.style.SUCCESS(f'✓ {len(hierarquias_criadas)} hierarquias criadas'))
        
        # Aplicar permissões aos superusers
        if options['aplicar_superuser']:
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
        
        self.stdout.write(self.style.SUCCESS('\n✓ Sincronização concluída com sucesso!'))
        
        # Mostrar mapeamento
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('MAPEAMENTO DE CÓDIGOS SINCRONIZADOS:'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        categorias = Acesso.objects.filter(tipo=Acesso.CATEGORIA_APP).order_by('id')
        self.stdout.write(self.style.SUCCESS('\n📁 CATEGORIAS (CT):'))
        for cat in categorias:
            self.stdout.write(f'  ✓ {cat.gerar_codigo():4} (ID: {cat.id:2}) - {cat.nome}')
        
        subcategorias = Acesso.objects.filter(tipo=Acesso.SUBCATEGORIA_RENDER).order_by('id')
        self.stdout.write(self.style.SUCCESS('\n📂 SUBCATEGORIAS (SCT):'))
        for sct in subcategorias:
            self.stdout.write(f'  ✓ {sct.gerar_codigo():5} (ID: {sct.id:2}) - {sct.nome}')
        
        sessoes = Acesso.objects.filter(tipo=Acesso.SESSAO_SECTION).order_by('id')
        self.stdout.write(self.style.SUCCESS('\n📄 SESSÕES (SS):'))
        for ss in sessoes:
            self.stdout.write(f'  ✓ {ss.gerar_codigo():4} (ID: {ss.id:2}) - {ss.nome}')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))

