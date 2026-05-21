"""
Management command para criar permissões base do sistema.
Cria automaticamente categorias, subcategorias e sessões definidas no menu lateral.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from apps.seguranca.permissoes.models import Acesso, AcessoHierarquia, GroupsAcessos, ControleAcessos
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Cria as permissões base do sistema (Categorias, SubCategorias e Sessões)'

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
        self.stdout.write(self.style.SUCCESS('Iniciando criação de permissões base...'))
        
        if options['reset']:
            self.stdout.write(self.style.WARNING('Removendo permissões existentes...'))
            Acesso.objects.all().delete()
            # Resetar auto-increment do SQLite
            with connection.cursor() as cursor:
                # Obtém o nome real da tabela do modelo
                table_name = Acesso._meta.db_table
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}';")
                self.stdout.write(self.style.SUCCESS(f'✓ Auto-increment resetado para tabela {table_name}'))
        
        # Definir estrutura de permissões baseada no menu lateral
        permissoes_base = {
            # GERAL - CT1
            'CT1': {
                'nome': 'GERAL',
                'descricao': 'Categoria Geral do sistema',
                'subcategorias': {
                    # Comunicados - SCT1
                    'SCT1': {
                        'nome': 'GERAL | COMUNICADOS',
                        'descricao': 'SubCategoria de Comunicados',
                        'sessoes': {
                            'SS1': {
                                'nome': 'GERAL | COMUNICADOS | MURAL',
                                'descricao': 'Acesso ao mural de comunicados'
                            },
                            'SS2': {
                                'nome': 'GERAL | COMUNICADOS | GERENCIADOR',
                                'descricao': 'Acesso ao gerenciador de comunicados'
                            }
                        }
                    }
                }
            },
            # RECURSOS HUMANOS - CT2
            'CT2': {
                'nome': 'RECURSOS HUMANOS',
                'descricao': 'Categoria de Recursos Humanos',
                'subcategorias': {
                    # Administrativo - SCT2
                    'SCT2': {
                        'nome': 'RECURSOS HUMANOS | ADMINISTRATIVO',
                        'descricao': 'SubCategoria Administrativa (Empresas, Lojas, etc)',
                        'sessoes': {
                            'SS3': {
                                'nome': 'RECURSOS HUMANOS | ADMINISTRATIVO | GERENCIAMENTO GERAL',
                                'descricao': 'Acesso ao gerenciamento administrativo geral'
                            }
                        }
                    },
                    # Funcionários - SCT3
                    'SCT3': {
                        'nome': 'RECURSOS HUMANOS | FUNCIONARIOS',
                        'descricao': 'SubCategoria de Funcionários',
                        'sessoes': {
                            'SS4': {
                                'nome': 'RECURSOS HUMANOS | FUNCIONARIOS | NOVO ACESSO',
                                'descricao': 'Acesso para criar novo funcionário'
                            },
                            'SS5': {
                                'nome': 'RECURSOS HUMANOS | FUNCIONARIOS | GERENCIADOR',
                                'descricao': 'Acesso ao gerenciador de funcionários'
                            }
                        }
                    },
                    # Usuários - SCT4
                    'SCT4': {
                        'nome': 'RECURSOS HUMANOS | USUARIOS',
                        'descricao': 'SubCategoria de Usuários',
                        'sessoes': {
                            'SS6': {
                                'nome': 'RECURSOS HUMANOS | USUARIOS | GERENCIADOR',
                                'descricao': 'Acesso ao gerenciador de usuários'
                            }
                        }
                    }
                }
            },
            # SEGURANÇA - CT3
            'CT3': {
                'nome': 'SEGURANCA',
                'descricao': 'Categoria de Segurança',
                'subcategorias': {
                    # Permissões - SCT5
                    'SCT5': {
                        'nome': 'SEGURANCA | PERMISSOES',
                        'descricao': 'SubCategoria de Permissões',
                        'sessoes': {
                            'SS7': {
                                'nome': 'SEGURANCA | PERMISSOES | GERENCIAMENTO DE PERMISSOES',
                                'descricao': 'Acesso ao gerenciamento de permissões'
                            }
                        }
                    }
                }
            },
            # TESOURARIA - CT4
            'CT4': {
                'nome': 'TESOURARIA',
                'descricao': 'Categoria de Tesouraria',
                'subcategorias': {
                    # Financeiro Geral - SCT6
                    'SCT6': {
                        'nome': 'TESOURARIA | FINANCEIRO GERAL',
                        'descricao': 'SubCategoria Financeiro Geral',
                        'sessoes': {
                            'SS8': {
                                'nome': 'TESOURARIA | FINANCEIRO GERAL | ADICIONAR A PAGAR',
                                'descricao': 'Acesso para adicionar contas a pagar'
                            },
                            'SS9': {
                                'nome': 'TESOURARIA | FINANCEIRO GERAL | ADICIONAR A RECEBER',
                                'descricao': 'Acesso para adicionar contas a receber'
                            },
                            'SS10': {
                                'nome': 'TESOURARIA | FINANCEIRO GERAL | GERENCIAMENTO GERAL',
                                'descricao': 'Acesso ao gerenciamento financeiro geral'
                            }
                        }
                    }
                }
            },
            # VENDAS - CT5
            'CT5': {
                'nome': 'VENDAS',
                'descricao': 'Categoria de Vendas',
                'subcategorias': {
                    # SIAPE - SCT7
                    'SCT7': {
                        'nome': 'VENDAS | SIAPE',
                        'descricao': 'SubCategoria SIAPE',
                        'sessoes': {
                            'SS11': {
                                'nome': 'VENDAS | SIAPE | RANKING',
                                'descricao': 'Acesso ao ranking SIAPE'
                            },
                            'SS12': {
                                'nome': 'VENDAS | SIAPE | CONSULTA CLIENTE',
                                'descricao': 'Acesso à consulta de cliente SIAPE'
                            },
                            'SS13': {
                                'nome': 'VENDAS | SIAPE | CRM',
                                'descricao': 'Acesso ao CRM SIAPE'
                            }
                        }
                    },
                    # Financeiro Vendas - SCT8
                    'SCT8': {
                        'nome': 'VENDAS | FINANCEIRO VENDAS',
                        'descricao': 'SubCategoria Financeiro Vendas',
                        'sessoes': {
                            'SS14': {
                                'nome': 'VENDAS | FINANCEIRO VENDAS | GERENCIAMENTO DE VENDAS',
                                'descricao': 'Acesso ao gerenciamento financeiro de vendas'
                            }
                        }
                    }
                }
            }
        }
        
        # Criar permissões em ordem: primeiro todas CT, depois todas SCT, depois todas SS
        acessos_criados = {}
        hierarquias_criadas = []
        
        # FASE 1: Criar TODAS as Categorias (CT) primeiro
        self.stdout.write(self.style.SUCCESS('\n--- Fase 1: Criando Categorias ---'))
        for ct_code, ct_data in permissoes_base.items():
            categoria, created = Acesso.objects.get_or_create(
                tipo=Acesso.CATEGORIA_APP,
                nome=ct_data['nome'],
                defaults={
                    'descricao': ct_data['descricao'],
                    'status': True
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Categoria criada: {categoria.nome} ({categoria.gerar_codigo()})'))
            else:
                categoria.descricao = ct_data['descricao']
                categoria.status = True
                categoria.save()
                self.stdout.write(self.style.WARNING(f'→ Categoria atualizada: {categoria.nome} ({categoria.gerar_codigo()})'))
            
            acessos_criados[ct_code] = categoria
        
        # FASE 2: Criar TODAS as SubCategorias (SCT) depois
        self.stdout.write(self.style.SUCCESS('\n--- Fase 2: Criando SubCategorias ---'))
        subcategorias_map = {}  # Mapeia SCT code -> (categoria, subcategoria_data)
        for ct_code, ct_data in permissoes_base.items():
            categoria = acessos_criados[ct_code]
            for sct_code, sct_data in ct_data['subcategorias'].items():
                subcategoria, created = Acesso.objects.get_or_create(
                    tipo=Acesso.SUBCATEGORIA_RENDER,
                    nome=sct_data['nome'],
                    defaults={
                        'descricao': sct_data['descricao'],
                        'status': True
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ SubCategoria criada: {subcategoria.nome} ({subcategoria.gerar_codigo()})'))
                else:
                    subcategoria.descricao = sct_data['descricao']
                    subcategoria.status = True
                    subcategoria.save()
                    self.stdout.write(self.style.WARNING(f'  → SubCategoria atualizada: {subcategoria.nome} ({subcategoria.gerar_codigo()})'))
                
                acessos_criados[sct_code] = subcategoria
                subcategorias_map[sct_code] = (categoria, sct_data)
        
        # FASE 3: Criar TODAS as Sessões (SS) por último
        self.stdout.write(self.style.SUCCESS('\n--- Fase 3: Criando Sessões ---'))
        sessoes_map = {}  # Mapeia SS code -> (subcategoria, sessao_data)
        for ct_code, ct_data in permissoes_base.items():
            for sct_code, sct_data in ct_data['subcategorias'].items():
                subcategoria = acessos_criados[sct_code]
                for ss_code, ss_data in sct_data['sessoes'].items():
                    sessao, created = Acesso.objects.get_or_create(
                        tipo=Acesso.SESSAO_SECTION,
                        nome=ss_data['nome'],
                        defaults={
                            'descricao': ss_data['descricao'],
                            'status': True
                        }
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Sessão criada: {sessao.nome} ({sessao.gerar_codigo()})'))
                    else:
                        sessao.descricao = ss_data['descricao']
                        sessao.status = True
                        sessao.save()
                        self.stdout.write(self.style.WARNING(f'    → Sessão atualizada: {sessao.nome} ({sessao.gerar_codigo()})'))
                    
                    acessos_criados[ss_code] = sessao
                    sessoes_map[ss_code] = (subcategoria, ss_data)
        
        # FASE 4: Criar hierarquias SCT -> SS
        self.stdout.write(self.style.SUCCESS('\n--- Fase 4: Criando Hierarquias SCT -> SS ---'))
        for ss_code, (subcategoria, ss_data) in sessoes_map.items():
            sessao = acessos_criados[ss_code]
            hierarquia_sct_ss, created = AcessoHierarquia.objects.get_or_create(
                pai=subcategoria,
                defaults={'status': True}
            )
            if created or sessao.id not in hierarquia_sct_ss.filhos.values_list('id', flat=True):
                hierarquia_sct_ss.filhos.add(sessao)
                if created:
                    hierarquias_criadas.append(f'SCT->SS: {subcategoria.nome}')
        
        # FASE 5: Criar hierarquias CT -> SCT
        self.stdout.write(self.style.SUCCESS('\n--- Fase 5: Criando Hierarquias CT -> SCT ---'))
        for ct_code, ct_data in permissoes_base.items():
            categoria = acessos_criados[ct_code]
            subcategorias_ids = []
            for sct_code in ct_data['subcategorias'].keys():
                subcategorias_ids.append(acessos_criados[sct_code].id)
            
            if subcategorias_ids:
                hierarquia_ct_sct, created = AcessoHierarquia.objects.get_or_create(
                    pai=categoria,
                    defaults={'status': True}
                )
                if created:
                    hierarquia_ct_sct.filhos.set(Acesso.objects.filter(id__in=subcategorias_ids))
                    hierarquias_criadas.append(f'CT->SCT: {categoria.nome}')
        
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
                
                # Adicionar todas as permissões criadas
                todas_permissoes = Acesso.objects.filter(status=True)
                controle.acessos.set(todas_permissoes)
                
                self.stdout.write(self.style.SUCCESS(f'✓ Permissões aplicadas ao superuser: {superuser.username}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Permissões base criadas com sucesso!'))
        
        # Mostrar mapeamento organizado por tipo
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('MAPEAMENTO DE CÓDIGOS (use estes códigos nos templates):'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        # Categorias
        self.stdout.write(self.style.SUCCESS('\n📁 CATEGORIAS (CT):'))
        for ct_code in sorted([k for k in acessos_criados.keys() if k.startswith('CT')]):
            acesso = acessos_criados[ct_code]
            codigo_gerado = acesso.gerar_codigo()
            status = '✓' if ct_code == codigo_gerado else '⚠'
            self.stdout.write(f'  {status} {ct_code:4} → {codigo_gerado:4} - {acesso.nome}')
        
        # SubCategorias
        self.stdout.write(self.style.SUCCESS('\n📂 SUBCATEGORIAS (SCT):'))
        for sct_code in sorted([k for k in acessos_criados.keys() if k.startswith('SCT')]):
            acesso = acessos_criados[sct_code]
            codigo_gerado = acesso.gerar_codigo()
            status = '✓' if sct_code == codigo_gerado else '⚠'
            self.stdout.write(f'  {status} {sct_code:5} → {codigo_gerado:5} - {acesso.nome}')
        
        # Sessões
        self.stdout.write(self.style.SUCCESS('\n📄 SESSÕES (SS):'))
        for ss_code in sorted([k for k in acessos_criados.keys() if k.startswith('SS')]):
            acesso = acessos_criados[ss_code]
            codigo_gerado = acesso.gerar_codigo()
            status = '✓' if ss_code == codigo_gerado else '⚠'
            self.stdout.write(f'  {status} {ss_code:4} → {codigo_gerado:4} - {acesso.nome}')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('\n⚠ IMPORTANTE: Se os códigos não corresponderem, atualize o menu lateral'))
        self.stdout.write(self.style.SUCCESS('   com os códigos gerados mostrados acima (coluna da direita).'))
        self.stdout.write(self.style.SUCCESS('\n✓ Superusers têm acesso total automaticamente!'))
        self.stdout.write(self.style.SUCCESS('  Não é necessário atribuir permissões a superusers.'))

