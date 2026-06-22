# Services MoneyPlus V2

## cliente_resolver.py

Ponto único: `resolver_dados_cliente(cpf, tipo, dados_json)`.

## Schemas fixos

### INSS (`cliente_inss.py`)

- pessoal: cpf, nome_completo, numero, flg_whatsapp, status_ativo
- ultimo_agendamento, ultima_presenca

### SIAPE (`cliente_siape.py`)

- pessoal, margens, debitos[], telefones[]

### OUTROS (`cliente_outros.py`)

- campos dinâmicos do `dados_json` (CSV importado)

## Outros módulos

| Arquivo | Função |
|---------|--------|
| `csv_import.py` | Parse CSV, preview, bulk create |
| `distribuicao.py` | Próximo cliente na esteira |
| `esteira_kpis.py` | KPIs básicos (máx. 6) |
| `dashboard.py` | Snapshot BI completo |
| `gerenciador.py` | CRUD campanhas/equipes |
| `gerador_siape.py` / `gerador_inss.py` | Criar campanha com lista de CPFs |
