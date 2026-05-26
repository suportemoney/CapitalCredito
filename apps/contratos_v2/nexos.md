# Nexos — Sistema operacional de contratos (visão e regras)

Este arquivo descreve **o que** o sistema deve controlar e **por quê**, alinhado ao plano técnico em [`plan.md`](plan.md). Referência visual externa: mapas Lucidspark *Tabulações Contratos Operacional* (legenda, status, fluxo), 30/03/2026.

---

## Ideia principal

Centralizar dentro da Money toda a **esteira operacional de contratos**: propostas, digitação, formalização, análise bancária, CIP/Refin (quando for portabilidade), anuência, pagamentos, pendências e encerramentos — com **histórico**, **responsável por etapa** e **impedimento de saltos indevidos** de status.

O objetivo final: saber exatamente onde cada contrato está, quem alterou, integrar formalização e pendências, controlar pagamento e comissão (**RegisterMoney** no momento certo), e escalar a operação com processo rastreável.

---

## Duas esteiras conectadas

### Esteira comercial (carteira — `siape`)

Onde o vendedor conduz o relacionamento com o cliente:

- Não é o cliente, Agendar, Sem interesse  
- **Em negociação** (ex.: em atendimento)  
- **Simulação** — o **operacional** produz propostas *simuladas*; o retorno volta para o time comercial aguardando decisão  
- **Proposta** — duas origens:
  1. Vendedor informa propostas **diretamente** quando **não** passou por simulação; ou  
  2. Após simulação, quando o vendedor **fixa/aceita** propostas: o sistema **cria um contrato operacional por proposta aceita**, cada um com **token único**, já posicionado na esteira operacional como **proposta** (objeto de digitação)

### Esteira operacional (contratos — `contratos`)

Onde o operacional (e em partes supervisor/financeiro) executa o contrato no banco:

- **Digitação** → **Análise** → (opcional **CIP** → **Refin** se portabilidade) → **Anuência** → **Pagamento**  
- **Pendências** (com retorno à etapa anterior após correção)  
- **Cancelado**, **Inelegível**

Separação proposital: comercial negocia; operacional executa contrato; financeiro confirma CMS; o sistema liga tudo pelo CPF/carteira/contrato.

---

## Regra de negócio: Anuência e portabilidade

**Anuência não depende de portabilidade.**

| Tipo de operação | Caminho operacional |
|------------------|---------------------|
| Normal | Digitação → Análise → **Anuência** → Pagamento |
| Portabilidade | Digitação → Análise → **CIP** → **Refin** → **Anuência** → Pagamento |

Quem decide se entra em CIP/Refin é o **operacional** (marcação explícita), não uma inferência automática do sistema.

---

## Sub-status por etapa (controle fino)

Cada macro-etapa possui sub-status para auditoria e telas:

| Etapa | Sub-status |
|-------|------------|
| Em negociação (comercial) | Em atendimento |
| Simulação | Aguardando retorno |
| Propostas (comercial) | Aceite, Verificando, Verificado |
| Digitação | Link disponibilizado, Checado, Formalizado |
| Análise | Aguardando, Sucesso |
| CIP | Aguardando, Sucesso |
| Refin | Aguardando, Sucesso |
| Anuência | Aguardando, Averbado |
| Pagamento | Pago Cliente, Pago TC, Pago CMS |
| Pendências | Aguardando correção, Corrigido |

---

## Edição do contrato após Digitação

Quando o contrato entra na **Digitação** (e nas fases seguintes):

- **Operacional** pode alterar: dados bancários, valores, prazo, banco, convênio, tipo de operação, link de formalização, status bancário, pendências.  
- **Vendedor** **não** edita o contrato após essa entrada (comercial permanece na carteira; o contrato é controle operacional).

---

## Fluxo resumido: Proposta → Digitação → Formalização → Análise

1. Na esteira comercial em **Proposta**, o **operacional** tabula para **Digitação** (início da execução no banco).  
2. Operacional digita no banco, obtém **link de formalização** e atualiza digitação (ex.: **link disponibilizado**).  
3. **Vendedor ou supervisor** envia o link ao cliente.  
4. No **`crm_supervisao`**, o **supervisor** abre o **card do contrato/proposta**, pode **ligar/checagem** e registrar desfecho: **Cancelado**, **Checado** ou **Formalizado**.  
5. Se **Formalizado**: vendedor e supervisor **não alteram** mais; o **operacional** move para **Análise** (**Aguardando**).  
6. Após análise (**Sucesso**), operacional escolhe: seguir para **CIP/Refin** (portabilidade) ou ir direto para **Anuência** (**Aguardando** → **Averbado** quando aplicável).  
7. Quando o banco paga o cliente, operacional registra **Pagamento — Pago Cliente**.  
8. Quando a TC for paga (cliente → empresa), o **supervisor** atualiza **Pago TC**.  
9. Quando o banco pagar a empresa (CMS da proposta), o **financeiro** atualiza **Pago CMS**.

---

## Pendências

A etapa **Pendências** cobre retrabalho documental ou operacional, por exemplo:

- Documento errado ou faltando; vídeo de formalização incorreto; dados bancários ou valores divergentes; erro de digitação; reprovação bancária ainda corrigível.

Sub-status **Corrigido** deve **restaurar a etapa anterior** (guardar “de onde veio” no histórico).

---

## Controle financeiro e tags

Alinhar tags ao que o banco e a empresa efetivamente pagaram:

| Situação | Tag (referência) |
|----------|------------------|
| Banco pagou cliente | PAGO CLIENTE |
| Banco/cliente pagou TC | PAGO TC |
| Sem TC | AGUARDANDO PAGAMENTO EMPRESA (até CMS) |
| Empresa recebeu CMS | PAGO EMPRESA / PAGO CMS |

---

## RegisterMoney

Lançar **RegisterMoney** somente quando:

1. Houve **pagamento de TC**; **ou**  
2. **Não existe TC** e ocorreu **pagamento da empresa (CMS)**.

Assim a comissão só entra no financeiro quando o contrato está **fechado** no sentido financeiro acordado.

---

## Diagrama macro (comercial × operacional)

```mermaid
flowchart TB
  subgraph comercial [Esteira comercial carteira]
    N1[Em negociação]
    N2[Simulação]
    N3[Proposta]
    N1 --> N2
    N1 --> N3
    N2 --> N3
  end
  subgraph operacional [Esteira operacional contrato]
    O1[Digitação]
    O2[Análise]
    O3[CIP]
    O4[Refin]
    O5[Anuência]
    O6[Pagamento]
    PEND[Pendências]
    N3 -->|operacional tabula| O1
    O1 --> O2
    O2 -->|portabilidade manual| O3
    O3 --> O4
    O4 --> O5
    O2 -->|demais casos| O5
    O5 --> O6
    O1 --> PEND
    O2 --> PEND
    PEND -->|Corrigido| O1
```

---

## Legado vs novo fluxo (contexto)

No fluxo antigo, muitas vezes o supervisor ia de “checado” direto para “pago”, **pulando** anuência e controles de pagamento. O novo desenho **obriga** passagem explícita por **Anuência** antes de **Pagamento** e separa **Pago Cliente**, **Pago TC** e **Pago CMS** com responsáveis distintos.

---

## Próximos passos de implementação

Ver fases e tabela de impacto em [`plan.md`](plan.md) (modelos, `fluxo_constants`, APIs, templates `consulta_cliente`, `crm_supervisao`, `crm_operacional`, migrações, RegisterMoney).
