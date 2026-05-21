# Sistema de Permissões - CapitalCredito

## Comando de Criação de Permissões Base

### Uso

Para criar todas as permissões base do sistema (Categorias, SubCategorias e Sessões):

```bash
python manage.py criar_permissoes_base
```

### Opções

#### `--reset`
Remove todas as permissões existentes antes de criar novas:

```bash
python manage.py criar_permissoes_base --reset
```

#### `--aplicar-superuser`
Aplica todas as permissões criadas aos superusers:

```bash
python manage.py criar_permissoes_base --aplicar-superuser
```

#### Combinando opções

```bash
python manage.py criar_permissoes_base --reset --aplicar-superuser
```

### Permissões Criadas

O comando cria automaticamente:

#### Categorias (CT)
- **CT1**: GERAL
- **CT2**: RECURSOS HUMANOS
- **CT3**: SEGURANCA
- **CT4**: VENDAS
- **CT5**: TESOURARIA

#### SubCategorias (SCT)
- **SCT1**: COMUNICADOS (CT1)
- **SCT2**: ADMINISTRATIVO (CT2)
- **SCT3**: GERENCIAMENTO DE FUNCIONARIOS (CT2)
- **SCT4**: USUARIOS (CT2)
- **SCT5**: PERMISSOES (CT3)
- **SCT6**: SIAPE (CT4)
- **SCT7**: FINANCEIRO VENDAS (CT4)
- **SCT8**: FINANCEIRO GERAL (CT5)

#### Sessões (SS)
- **SS1**: MURAL DE AVISOS (SCT1)
- **SS2**: GERENCIAMENTO ADMINISTRATIVO (SCT2)
- **SS3**: LISTA DE FUNCIONARIOS (SCT3)
- **SS4**: GERENCIAMENTO DE USUARIOS (SCT4)
- **SS5**: GERENCIAMENTO DE PERMISSOES (SCT5)
- **SS6**: CONSULTA SIAPE (SCT6)
- **SS7**: RANKING SIAPE (SCT6)
- **SS8**: GERENCIAMENTO FINANCEIRO VENDAS (SCT7)
- **SS9**: GERENCIAMENTO FINANCEIRO GERAL (SCT8)

### Hierarquias

O comando também cria automaticamente as hierarquias:
- CT → SCT (Categoria → SubCategoria)
- SCT → SS (SubCategoria → Sessão)

### Superusers

**IMPORTANTE**: Superusers têm acesso total a tudo automaticamente. Não é necessário atribuir permissões manualmente a superusers, pois o sistema verifica `user.is_superuser` antes de verificar permissões específicas.

### Após Executar o Comando

1. As permissões estarão disponíveis no Django Admin
2. Você pode atribuir permissões aos usuários através da interface de gerenciamento
3. Superusers já terão acesso total automaticamente

