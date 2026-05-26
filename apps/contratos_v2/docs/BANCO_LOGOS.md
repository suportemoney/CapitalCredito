# Logos de bancos (catálogo `contratos.Banco`)

Os bancos já existem em `apps/contratos_v2/models.py` — foram adicionados campos `dominio`, `logo`, `logo_url`, `nome_curto` e `ispb`.

## Variáveis de ambiente

```env
BANCO_LOGO_PROVIDER=logo_dev
LOGO_DEV_TOKEN=sua_chave
BRANDFETCH_API_KEY=sua_chave
```

Com `BANCO_LOGO_PROVIDER=brandfetch`, a API tenta Brandfetch primeiro e Logo.dev como fallback (e vice-versa).

## Comandos (executar no servidor / VPS)

```bash
python manage.py migrate contratos
python manage.py sincronizar_logos_bancos --apenas-dominios
python manage.py sincronizar_logos_bancos
```

## Ícones via CDN (fallback gratuito)

Pacote [icones-bancos-brasileiros](https://github.com/matheuscuba/icones-bancos-brasileiros) — classes `ibb-*` por COMPE/título, sem API key:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/matheuscuba/icones-bancos-brasileiros@1.1/dist/all.css">
```

Ordem na tela CRM Supervisão: **logo em /media** → **ícone ibb-*** → ícone genérico.

## API

- `GET /contratos/api/v2/bancos-logos/` — mapa de logos + `icon_class` para o front
- CRM Supervisão: `GET /siape/api/get/crm-sup-resumo-operacional/?dias=30`
