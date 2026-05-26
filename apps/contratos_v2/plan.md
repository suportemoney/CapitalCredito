# Plano de atualização — Sistema operacional de contratos (MoneyConsig)

Documento de planejamento para evolução coordenada dos apps **`contratos`** e **`siape`**. Referência visual complementar: exportações Lucidspark *Tabulações Contratos Operacional* (legenda / status / fluxo), 30/03/2026.

---

## 1. Objetivo

Centralizar, organizar e automatizar a esteira operacional de contratos — do primeiro atendimento comercial ao pagamento final — com:

- Duas esteiras conectadas (comercial na carteira × operacional no contrato);
- Registro de etapa, sub-status e responsável;
- Histórico e rastreabilidade;
- Regras de transição que impeçam “pular” fases críticas;
- Integração financeira (tags de pagamento, **RegisterMoney** com gatilhos corretos).

---

## 2. Esteira comercial (Carteira — `siape`)

Tabulações de contexto do vendedor com o cliente (não confundir com fase operacional do contrato):

| Etapa comercial (macro) | Observação |
|-------------------------|------------|
| Não é o cliente | Mantida |
| Agendar | Mantida |
| Sem interesse | Mantida |
| Em negociação | Inclui atendimento ativo |
| **Simulação** | Operacional cadastra propostas *simuladas*; retorno ao vendedor |
| **Proposta** | Vendedor informa propostas **se não** houver passagem por simulação; ou contratos já criados após aceite pós-simulação |

### 2.1 Regra: Simulação × Proposta

1. O vendedor pode tabular a carteira como **Simulação** ou **Proposta** (conforme política de acesso no sistema).
2. **Simulação**: quem cria e mantém as propostas simuladas é o **operacional**; o fluxo “volta” para análise/retorno comercial.
3. **Proposta** (sem simulação): quem informa as propostas é o **vendedor** (equivalente ao envio atual de solicitação + linhas de proposta).
4. **Pós-simulação**: quando o vendedor **fixa/aceita** uma ou mais propostas simuladas, o sistema deve **gerar registros de contrato** (`ContratoExecucao` ou entidade alinhada) com **tokens únicos** e posicionar cada um na esteira operacional como **Proposta** (um contrato por proposta aceita), prontos para evolução para **Digitação**.

---

## 3. Esteira operacional (Contratos — `contratos`)

Etapas operacionais do contrato (macro):

| Etapa | Quando |
|-------|--------|
| Digitação | Após operacional tabular a partir de Proposta; digitação no banco; link de formalização |
| Análise | Pós-formalização (vídeo/cliente); banco analisando |
| CIP | Só portabilidade — decisão **manual** do operacional |
| Refin | Só portabilidade — decisão **manual** do operacional |
| Anuência | Sempre antes de pagamento (ver §4) |
| Pagamento | Controle dos três eventos financeiros |
| Pendências | Retorno temporário; após corrigido, volta à etapa anterior |
| Cancelado | Encerramento sem conclusão |
| Inelegível | Sem continuidade operacional |

### 3.1 Sub-status por etapa

| Etapa | Sub-status |
|-------|------------|
| Em negociação (comercial) | Em atendimento |
| Simulação (comercial) | Aguardando retorno |
| Propostas (comercial) | Aceite, Verificando, Verificado |
| Digitação | Link disponibilizado, Checado, Formalizado |
| Análise | Aguardando, Sucesso |
| CIP | Aguardando, Sucesso |
| Refin | Aguardando, Sucesso |
| Anuência | Aguardando, Averbado |
| Pagamento | Pago Cliente, Pago TC, Pago CMS |
| Pendências | Aguardando correção, Corrigido |

*(Implementação: `CharField` com choices, ou tabela de domínio, espelhando `fluxo_constants` estendido.)*

### 3.2 Regra de negócio: Anuência e portabilidade

| Situação | Sequência operacional |
|----------|------------------------|
| Contrato normal | Digitação → Análise → **Anuência** → Pagamento |
| Portabilidade | Digitação → Análise → **CIP** → **Refin** → **Anuência** → Pagamento |

- **Anuência não depende** de portabilidade: em operações sem CIP/Refin, o fluxo vai de **Análise** direto para **Anuência**.
- A decisão “é portabilidade e entra CIP/Refin” é do **operacional**, não inferida automaticamente pelo sistema (flag ou tabulação explícita).

### 3.3 Edição após Digitação

Após o contrato existir na etapa **Digitação** (ou fases posteriores operacionais):

- **Operacional** pode editar: dados bancários, valores, prazo, banco, convênio, tipo de operação, link de formalização, status bancário, pendências.
- **Vendedor** não edita o contrato após entrada em Digitação (somente leitura / ações permitidas por perfil, ex.: envio de documento se o produto permitir).

---

## 4. Fluxo Digitação → Formalização → Análise (detalhe)

1. Da etapa comercial **Proposta**, o **operacional** tabula para **Digitação** (no contrato/carteira conforme modelo atual).
2. Operacional digita no banco e obtém o **link de formalização**; atualiza sub-status de digitação para **link disponibilizado** (ou equivalente).
3. **Vendedor ou supervisor** envia o link ao cliente.
4. Em **`crm_supervisao.html`**: o **supervisor** pode abrir o **card da proposta/contrato**, contatar o cliente e registrar **checagem** (sub-status **Checado**) ou encaminhar a **Formalizado**, ou ainda **Cancelado** conforme regra.
5. Em **Formalizado**: **vendedor e supervisor não alteram** mais esse contrato; retorna ao **operacional**, que evolui a tabulação para **Análise** com sub-status **Aguardando**.
6. Após análise bancária (sub-status **Sucesso**), o operacional define o caminho:
   - Portabilidade: **CIP** → **Refin** → **Anuência**;
   - Demais: **Anuência** direto (**Aguardando** → **Averbado** quando aplicável).

---

## 5. Pagamento, tags e RegisterMoney

### 5.1 Eventos em Pagamento

| Evento | Quem atualiza (referência) | Tag sugerida |
|--------|----------------------------|--------------|
| Banco pagou o cliente | Operacional | PAGO CLIENTE |
| Cliente/fluxo pagou TC | Supervisor | PAGO TC |
| Banco pagou comissão empresa (CMS) | Financeiro | PAGO CMS / PAGO EMPRESA |

Tags auxiliares (conforme negócio):

- Sem TC: **AGUARDANDO PAGAMENTO EMPRESA** até CMS;
- **PAGO EMPRESA** quando a empresa recebeu.

### 5.2 RegisterMoney

Gerar **RegisterMoney** apenas quando:

1. Houve **pagamento de TC**; **ou**
2. **Não houver TC**, após **pagamento da empresa (CMS)**.

Isso evita lançamento prematuro de comissão.

---

## 6. Pendências

Usar etapa/tabulação **Pendências** quando houver, entre outros:

- Documento incorreto ou faltando;
- Vídeo de formalização incorreto;
- Dados bancários ou valores divergentes;
- Erro de digitação;
- Reprovação bancária com possibilidade de correção.

Após **Corrigido**, o contrato **retorna à etapa anterior** (estado armazenado em histórico).

---

## 7. Implicações técnicas (resumo)

| Área | Ação planejada |
|------|----------------|
| [`apps/contratos_v2/models.py`](models.py) | Estender `ContratoExecucao` (e relacionados) com **etapa macro** + **sub_status**; opcional `origem_portabilidade`; histórico de transições e `alterado_por`. |
| [`apps/contratos_v2/fluxo_constants.py`](fluxo_constants.py) | Novos enums: etapas operacionais completas, sub-status por etapa, tags financeiras. |
| [`apps/contratos_v2/apis/fluxo.py`](apis/fluxo.py) | Endpoints de transição validada; edição operacional pós-digitação; bloqueio de edição vendedor. |
| [`apps/siape/models.py`](../siape/models.py) | Alinhar `CarteiraClientes` / `TabulacaoVendedor` com novas tabulações comerciais (Simulação, sub-status de Proposta). |
| [`consulta_cliente.html`](../siape/templates/siape/forms/consulta_cliente.html) | UI para caminhos simulação vs proposta; cards por contrato/token. |
| [`crm_supervisao.html`](../siape/templates/siape/forms/crm_supervisao.html) | Card contrato/proposta: checagem, formalizado, cancelado; integração API. |
| [`crm_operacional.html`](templates/contratos/v2/crm_operacional.html) | Filas por etapa/sub-status; CIP/Refin; anuência; pagamento. |
| Migrações | Campos novos + dados default para contratos existentes. |

---

## 8. Próximas entregas sugeridas (fases)

1. **Modelagem**: etapas, sub-status, histórico, flags portabilidade; migração.
2. **Máquina de estados**: matriz de transições permitidas (incl. Pendências e retorno).
3. **Permissões**: matriz papel × ação (vendedor, supervisor, operacional, financeiro).
4. **APIs e telas**: consulta cliente, supervisão, CRM operacional, financeiro (CMS).
5. **RegisterMoney**: serviço/gatilho nos eventos TC ou CMS sem TC.
6. **Testes HML**: fluxos com e sem portabilidade; com e sem TC.

---

## 9. Documentação irmã

Descrição narrativa alinhada a este plano: [`nexos.md`](nexos.md).
