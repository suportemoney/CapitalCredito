"""
Roteiro de testes funcionais — Envio de Proposta (Consultor/Vendedor).

Este arquivo centraliza o checklist de cenários que validam o critério 10 da
validação [3] ENVIO DE PROPOSTA. Os casos abaixo devem ser executados
manualmente (UI) e/ou automatizados quando uma suíte de testes for montada.

======================================================================
A) Carregamento da Tabela CMS (critérios 2, 3 e 10)
======================================================================
A1. Selecionar Banco + Convênio + Produto que TENHAM TabelaCms ativa.
    Esperado: select "Tabela CMS" habilita e lista as tabelas com o
    sufixo "[M1 - 100%]" / "[M2 - 50%]" / "[M3 - 0%]".

A2. Selecionar combinação de Banco + Convênio + Produto que NÃO possui
    TabelaCms ativa (ou só possui inativas).
    Esperado: única opção no select é
        "---nenhuma tabela disponível---"
    (desabilitada, selecionada). Endpoint GET /contratos/api/v2/tabelas-cms-filtradas/
    retorna {"ok": true, "tabelas": []}.

A3. Selecionar parcialmente (apenas 1 ou 2 dos três selects).
    Esperado: select de Tabela CMS continua desabilitado com texto
    "Selecione Banco + Convênio + Produto...".

======================================================================
B) Cálculos automáticos em tempo real (critérios 4, 6, 7)
======================================================================
B1. Preencher Parcela=500,00 e Coeficiente=2,5 -> AF deve virar 200,00.
B2. Preencher Parcela=500,00 e AF=250,00 -> Coeficiente deve virar 2,000000.
B3. Após B1, editar AF manualmente -> Coeficiente é recalculado
    (fonte = "af"); não entra em loop.
B4. Após B2, editar Coeficiente manualmente -> AF é recalculado
    (fonte = "coeficiente"); não entra em loop.
B5. TC = 0 ou vazio: Liberado = AF.
B6. TC > 0: Liberado = AF - TC (com piso em 0 se TC > AF).
B7. Campo "Valor Liberado" deve estar readonly (não aceita digitação).

======================================================================
C) Validações de segurança (critério 5)
======================================================================
C1. Digitar valor negativo em Parcela/AF/TC/Coeficiente:
    - min="0" nos inputs bloqueia no browser.
    - Backend em api_post_solicitar_propostas troca negativos por None.
C2. Coeficiente = 0 e Parcela > 0:
    - Frontend valida ">0" no submit.
    - Cálculo protegido por `seguro(n)` (evita divisão por zero).
C3. Enviar sem selecionar Tabela CMS:
    - _validarLinhasPropostaProp bloqueia com mensagem clara.

======================================================================
D) Persistência e integração (critérios 7, 9 e 3.8 backend)
======================================================================
D1. POST /contratos/api/v2/solicitar-propostas/ com tabela_cms_id válido:
    PropostaDados é criado com tabela_cms e coeficiente preenchidos.

D2. POST com tabela_cms_id que NÃO pertence à tripla banco+convênio+produto:
    Backend ignora (salva sem tabela_cms), evitando dado inconsistente.

D3. POST com valor_liberado manipulado pelo cliente (ex.: 999999):
    Backend IGNORA e recalcula Liberado = AF - max(0, TC), persistindo o
    valor correto em PropostaDados.valor_liberado.

D4. Operacional chama api_post_gerar_contrato_digitacao SEM tabela_cms_id:
    - Se PropostaDados.tabela_cms existir, é usada como default.
    - Se não existir, retorna HTTP 400.

======================================================================
E) Testes de regressão da UI (critério 8)
======================================================================
E1. Adicionar múltiplas linhas (3+) de proposta: cada linha tem seu próprio
    ciclo de Tabela CMS / cálculos sem interferir nas outras.
E2. Remover linha (.prop-btn-rem-proposta) após cálculos: remanescentes
    mantêm consistência.
E3. Cliente com produto de portabilidade (contém "PORT"/"REFIN"): o bloco
    de contrato de origem aparece independentemente da Tabela CMS.

======================================================================
F) Endpoints envolvidos
======================================================================
- GET  /contratos/api/v2/tabelas-cms-filtradas/?banco_id=&convenio_id=&produto_id=
- POST /contratos/api/v2/solicitar-propostas/
- POST /contratos/api/v2/gerar-contrato-digitacao/  (operacional)


======================================================================
ROTEIRO VALIDAÇÃO [4] — CLASSIFICADOR DE TC (RegisterMoney)
======================================================================

G) Classificação automática (critérios 3, 4, 5, 11)
----------------------------------------------------
G1. CPF inédito + user V qualquer + 1º Pago TC:
    Esperado: `classificar_tc_automatico('11111111111', V)` -> ('M1', 'NOVO').
    RegisterMoney.classificador_auto = 'M1', tipo_classificacao = 'NOVO'.

G2. CPF inédito + user vazio (sem comercial identificado):
    Esperado: ('M1', 'NOVO') — regra de segurança (não penaliza).

G3. RegisterMoney existente mesmo CPF + user V + data_criacao < 90 dias:
    Esperado: ('M2', 'RETRABALHO').
    2º Pago TC vinculado ao mesmo user: classificador_auto = 'M2'.

G4. ContratoExecucao existente mesmo CPF + carteira.user_responsavel = V
    + data_criacao < 90 dias:
    Esperado: ('M2', 'RETRABALHO').

G5. ContratoExecucao existente mesmo CPF + proposta.solicitacao_origem.criado_por = V
    + data_criacao < 90 dias:
    Esperado: ('M2', 'RETRABALHO').

G6. Mesmo CPF com user W != V (OUTRO funcionário) dentro de 90 dias:
    Esperado: ('M1', 'NOVO') para V — não considera histórico de outros users.

G7. Mesmo CPF + user V com data_criacao > 90 dias:
    Esperado: ('M1', 'NOVO') — janela excedida.

G8. Payload Pago TC com `forcar_m3=True`:
    Esperado: `_disparar_registermoney_se_necessario` grava
    classificador_auto='M3', tipo_classificacao='MANUAL',
    independentemente da janela de 90 dias.


H) Persistência / Travamento (critérios 5, 6, 8)
----------------------------------------------------
H1. 1º ComprovanteTC parcial (valor < valor_tc):
    - RegisterMoney é criado com classificador_auto calculado.
    - ContratoExecucao.sub_status_operacional = PG_PAGO_TC_PARCIAL.

H2. 2º ComprovanteTC parcial posterior (soma ainda < valor_tc):
    - NÃO cria novo RegisterMoney (`RegisterMoney_has_for_ce` = True).
    - `_incrementar_acumulado_rm` soma o valor em valor_pago_acumulado.
    - classificador_auto PERMANECE o mesmo do 1º pagamento.

H3. ComprovanteTC que zera o saldo (soma == valor_tc):
    - sub_status_operacional vira PG_PAGO_TC_TOTAL.
    - classificador_auto permanece inalterado.

H4. POST /api/v2/contrato/editar-dados/ alterando valor_af / valor_tc /
    valor_liberado após H1 (contrato com ComprovanteTC ativo):
    - Resposta HTTP 409.
    - `erro` contém "travados após o primeiro pagamento de TC".
    - Campo `campo_bloqueado` presente no JSON de erro.

H5. POST /api/v2/contrato/editar-dados/ alterando campos NÃO financeiros
    (cliente.nome_completo etc.) após existir ComprovanteTC:
    - Resposta HTTP 200; alteração persiste normalmente.

H6. POST /api/v2/contrato/editar-dados/ alterando valor_af antes de existir
    qualquer ComprovanteTC ou RegisterMoney:
    - Resposta HTTP 200; alteração persiste (nenhum trava).


I) Integridade financeira e UI (critérios 7, 2)
----------------------------------------------------
I1. Modal "Evoluir → Pago TC" exibe input file + botão Enviar + lista
    de comprovantes + badge "Pago TC Parcial"/"Pago TC Total".

I2. Envio multipart POST /api/v2/comprovante-tc/:
    - valor obrigatório > 0 (frontend + backend).
    - arquivo obrigatório.
    - Response contém classificador_auto e tipo_classificacao
      (devolvidos via `obter_classificador_primeiro_rm`).

I3. Badge em tempo real:
    - Ao digitar valor no input, badge atualiza para Parcial/Total/Aguardando
      baseado em soma_acumulada + valor_novo vs valor_tc.


J) Performance (critério 10)
----------------------------------------------------
J1. RegisterMoney.Meta.indexes contém
    models.Index(fields=['cpf_cliente', 'user', 'data'],
                 name='rm_retrab_cpf_user_data_idx').
J2. Query EXPLAIN de `classificar_tc_automatico` deve usar esse índice na
    consulta de janela 90 dias.


K) Endpoints envolvidos na validação [4]
----------------------------------------------------
- POST /contratos/api/v2/comprovante-tc/   (multipart: contrato_id, valor, arquivo, forcar_m3?)
- GET  /contratos/api/v2/comprovantes-tc/?contrato_id=
- POST /contratos/api/v2/contrato/editar-dados/   (bloqueio 409 de AF/TC/Liberado)
- apps.siape.apis.classificador.classificar_tc_automatico(cpf, user, dias=90)
- apps.siape.apis.classificador.obter_classificador_primeiro_rm(ce)


======================================================================
Roteiro de testes funcionais — Validação [5] ESTEIRA OPERACIONAL
======================================================================

L) Progressão Digitação → Formalização (critérios 2, 3, 5, 6)
----------------------------------------------------
L1. Contrato novo iniciado pela solicitação de digitação:
    - Esperado: etapa_operacional='DIGITACAO', sub_status_operacional='DIG_AGUARDANDO'.

L2. Operacional executa ação 'operacional_digitado':
    - Transição DIG_AGUARDANDO -> DIG_DIGITADO dentro de DIGITACAO.
    - HistoricoTransicaoContrato registra etapa_anterior='DIGITACAO',
      sub_anterior='DIG_AGUARDANDO', etapa_nova='DIGITACAO',
      sub_nova='DIG_DIGITADO'.

L3. Operacional executa 'operacional_link_disponibilizado' em DIG_DIGITADO:
    - Etapa muda para FORMALIZACAO; sub vira FORM_LINK_DISPONIVEL.
    - Histórico registra a troca de etapa.

L4. Supervisor executa 'supervisor_checado' em FORM_LINK_DISPONIVEL:
    - Sub avança para FORM_CHECADO dentro de FORMALIZACAO.
    - Histórico aparece com sub_nova='FORM_CHECADO'.

L5. Supervisor executa 'supervisor_formalizado' em FORM_CHECADO:
    - Sub avança para FORM_FORMALIZADO.
    - Contrato está pronto para seguir para ANALISE/CIP conforme fluxo seguinte.

L6. Vendedor executa 'vendedor_formalizado' diretamente em FORM_LINK_DISPONIVEL:
    - Esperado: ação REJEITADA (exige FORM_CHECADO ou DIG_CHECADO).
    - Mensagem de erro de transição inválida é retornada.


M) UI — Checado oculto + mapeamento FORMALIZACAO (critérios 4, 7)
----------------------------------------------------
M1. CRM v2 operacional ([apps/contratos_v2/static/contratos/js/crm_operacional.js]):
    - ETAPA_SUBSTATUS['DIGITACAO'] contém APENAS [DIG_AGUARDANDO, DIG_DIGITADO].
    - ETAPA_SUBSTATUS['FORMALIZACAO'] contém [FORM_LINK_DISPONIVEL, FORM_FORMALIZADO]
      (FORM_CHECADO INTENCIONALMENTE AUSENTE como chip).
    - STATUS_MAP resolve 'FORM_LINK_DISPONIVEL' -> 'Link disponível',
      'FORM_CHECADO' -> 'Checado', 'FORM_FORMALIZADO' -> 'Formalizado'.
    - ETAPA_COLORS/NOMINAL/INITIAL_SUB populam a entrada 'FORMALIZACAO'.

M2. Ao filtrar pelo chip "Formalização":
    - Sub-chips exibem APENAS "Link disponível" e "Formalizado".
    - Contratos em FORM_CHECADO continuam visíveis no chip-pai "Formalização"
      com badge inline "Checado" na coluna de sub-status.

M3. Supervisão ([apps/siape/templates/siape/forms/crm_supervisao.html]):
    - Chip 'FORMALIZACAO' presente na barra de chips operacional.
    - crm_supervisao.js `_matchEtapaFiltro` cobre etapa='FORMALIZACAO'.
    - Sub-chips de Formalização idênticos ao CRM v2 (sem Checado).


N) Histórico / Timeline (critério 8)
----------------------------------------------------
N1. Listagem de histórico (api_get /contratos/api/v2/contrato/historico/)
    retorna registros com sub_nova_label correto:
    - 'FORM_LINK_DISPONIVEL' -> 'Link disponível'.
    - 'FORM_CHECADO'         -> 'Checado'.
    - 'FORM_FORMALIZADO'     -> 'Formalizado'.

N2. Mesmo com "Checado" oculto como chip na esteira, o registro FORM_CHECADO
    aparece corretamente no modal de linha do tempo do contrato.


O) Compatibilidade com dados antigos — migration 0046 (critério 11)
----------------------------------------------------
O1. Base com contratos em DIGITACAO + DIG_LINK_DISPONIBILIZADO antes do migrate:
    - Após aplicar 0046_promover_formalizacao_legado:
        etapa_operacional='FORMALIZACAO', sub_status_operacional='FORM_LINK_DISPONIVEL'.
    - Um HistoricoTransicaoContrato foi criado com observação
      "Migração automática legado -> FORMALIZACAO".

O2. Idem para DIG_CHECADO -> FORM_CHECADO e DIG_FORMALIZADO -> FORM_FORMALIZADO.

O3. Contratos que já estavam em DIG_AGUARDANDO/DIG_DIGITADO NÃO são alterados
    (migration só atua nos 3 sub-status legados listados em MAPA_LEGADO).

O4. Rodar a migration em base vazia deve ser idempotente e não criar
    históricos espúrios.


P) Permissões (critério 9)
----------------------------------------------------
P1. Operacional (SCT189) consegue executar 'operacional_digitado' e
    'operacional_link_disponibilizado'.
P2. Supervisor (SCT147) consegue executar 'supervisor_checado' e
    'supervisor_formalizado'.
P3. Papéis fora do mapeamento recebem erro 403 (controle_acess_multiplos).


Q) Regressão (critério 12)
----------------------------------------------------
Q1. Fluxo completo: Aguardando -> Digitado -> Link disponível ->
    Checado -> Formalizado, sem erros.
Q2. Grid da esteira exibe badge correto em cada etapa intermediária.
Q3. Contratos em etapas anteriores (SIMULACAO, ANALISE, etc.) não são
    afetados pelas mudanças de UI/migration.


======================================================================
Roteiro de testes funcionais — Validação [6] FICHA DO CLIENTE (Modal)
======================================================================

R) Estrutura do modal (critérios 1, 2, 3, 4)
----------------------------------------------------
R1. CRM v2 operacional — `modalFicha` em
    [apps/contratos_v2/templates/contratos/v2/crm_operacional.html]:
    - `#tabsFicha` contém EXATAMENTE 2 abas: "Dados & Proposta"
      (`#fichaTabPessoais`) e "Arquivos" (`#fichaTabArquivos`).
    - Não há mais o bloco oculto `#fichaTabHistorico`, o botão
      `#btnFichaLinhaTempo` no rodapé nem o `modalFichaLinhaTempo`.

R2. Supervisor SIAPE — `modalFichaOp` em
    [apps/siape/templates/siape/forms/crm_supervisao.html]:
    - `#tabsFichaOp` contém EXATAMENTE 2 abas: "Dados & Proposta"
      (`#fichaOpDados`) e "Arquivos" (`#fichaOpArquivos`).
    - Nenhuma aba "Linha do Tempo" aparece no modal principal.


S) Botão dedicado de Linha do Tempo (critérios 5, 6, 8)
----------------------------------------------------
S1. CRM v2 operacional — a coluna "Ações" da grid mantém o botão de
    auditoria (`.btn-auditoria`, ícone `bx-history`) que abre
    `modalAuditoriaCrm` consumindo
    `GET /contratos/api/v2/auditoria-fluxo/?tipo=<t>&id=<i>`.

S2. Supervisor SIAPE — a coluna "Ações" da grid operacional inclui o
    botão `.btn-timeline-op` (ícone `bx-history`) que chama
    `_abrirTimelineSup(tipo, id)`:
    - Abre `modalTimelineSup` com spinner.
    - Faz GET em `/contratos/api/v2/auditoria-fluxo/?tipo=<t>&id=<i>`.
    - Renderiza a timeline com o mesmo layout do modal de auditoria
      do CRM v2.

S3. Consistência: os dois modais (operacional e supervisor) partem da
    MESMA rota (`auditoria-fluxo/`) — sem divergência de payload ou
    formato de data entre as esteiras.


T) Performance (critério 10)
----------------------------------------------------
T1. `api_get_ficha` ([apps/contratos_v2/apis/fluxo.py]) suporta o query param
    `with_historico`:
    - `with_historico` ausente, `1`, `true`, `yes` → resposta mantém o
      campo `historico` (compat).
    - `with_historico` em `{0, false, no, nao, não}` (case-insensitive)
      → resposta OMITE o campo `historico` do payload.

T2. CRM v2 operacional (`abrirModalFicha` em
    [apps/contratos_v2/static/contratos/js/crm_operacional.js]) chama
    `ficha/?...&with_historico=0`. `renderFichaConteudo` não referencia
    mais `#fichaConteudoHistorico`.

T3. Supervisor SIAPE (`abrirFichaOp` em
    [apps/siape/static/siape/js/forms/crm_supervisao.js]) chama
    `ficha/?...&with_historico=0` em paralelo com o endpoint de
    `midia-arquivos`. `_renderFichaOpConteudo` não referencia mais
    `#fichaOpConteudoHistorico`.


U) Aba Arquivos (critério 3)
----------------------------------------------------
U1. `_urlArquivosPorTipo('contrato', id)` →
    `/contratos/api/v2/contrato/<id>/midia-arquivos/`.
U2. `_urlArquivosPorTipo('simulacao', id)` →
    `/contratos/api/v2/solicitacao-dig/<id>/midia-arquivos/`.
U3. Outros tipos → retorna null; aba fica com "Nenhum arquivo anexado.".

U4. `_renderFichaOpArquivos(payload)` gera uma linha para cada item
    válido (pdf_proposta, vídeo, e `arquivos[]`). Quando total = 0,
    exibe `#fichaOpSemArquivos` e mantém `#fichaOpListaArquivos` vazio.

U5. Itens da lista renderizados têm link "Abrir" (target _blank) quando
    `url` existe; caso contrário, texto "sem URL".


V) Permissões e compatibilidade (critérios 9, 11)
----------------------------------------------------
V1. `api_get_ficha`, `api_get_auditoria_fluxo`,
    `api_get_contrato_midia_arquivos` e
    `api_get_solicitacao_dig_midia_arquivos` seguem protegidos por
    `@login_required + @controle_acess('SCT189')`.
V2. Consumidores antigos que NÃO passam `with_historico` continuam
    recebendo o campo `historico` (retrocompat do endpoint de ficha).


W) Regressão visual (critério 12)
----------------------------------------------------
W1. Abrir modal Ficha em diferentes tipos (simulação, proposta, contrato)
    sem erro de JS no console.
W2. Alternar abas "Dados & Proposta" ↔ "Arquivos" sem quebra visual.
W3. Clicar no botão de linha do tempo na grid do supervisor abre o
    `modalTimelineSup` e renderiza o histórico.
W4. Fechar os modais não deixa backdrop ou foco preso.
"""

"""
═══════════════════════════════════════════════════════════════════════════════
Validação [7] — EDIÇÃO (Operacional/Supervisor)
═══════════════════════════════════════════════════════════════════════════════

Escopo: novo fluxo de edição do contrato via `modalEditarDados` (CRM v2) e
`modalEditarDadosSup` (Supervisor), ambos com 2 abas (Dados&Proposta/Arquivos),
endpoints `api_post_editar_dados_contrato` (expandido) e
`api_post_excluir_cliente_arquivo` (novo), além do signal `post_delete` de
`ClienteArquivo` (defesa em profundidade contra órfãos).

Pré-requisitos compartilhados:
    F1. Três usuários:
          - U_OP    — Funcionario com Cargo "OPERACIONAL".
          - U_SUP   — Funcionario com Cargo "SUPERVISOR".
          - U_VEND  — Funcionario com Cargo "VENDEDOR" (sem SCT189).
    F2. Contrato em execução CE com proposta P e cliente C (DP).
          - C.nome_completo preenchido; nenhum ClienteContato ainda.
          - P com valor_af/valor_tc/valor_liberado e prazo preenchidos.
    F3. Sem ComprovanteTC ativo nem RegisterMoney com classificador (trava
        financeira DESATIVADA).

A. api_post_editar_dados_contrato — EXPANSÃO
    A1. OPERACIONAL edita email/telefone (não existia ClienteContato):
        - POST com cliente={email,telefone,rg,nome_mae}; retorna 200 ok;
          cria ClienteContato linkado a DP.
        - Assert: campos persistidos; `numero_rg` atualizado (alias `rg`).
        - Assert: 1 HistoricoTransicaoContrato novo com observação contendo
          "Edição de dados (operacional)" e lista de campos alterados.
    A2. SUPERVISOR edita numero_contrato e link_formalizacao:
        - POST com contrato={numero_contrato,link_formalizacao}; 200 ok.
        - Assert: CE.codigo/CE.link_formalizacao atualizados; um novo
          `HistoricoTransicaoContrato` com "Edição de dados (supervisor)".
    A3. OPERACIONAL edita coeficiente e valor_parcela da proposta:
        - POST proposta={coeficiente,valor_parcela}; 200 ok; persistência ok.
    A4. VENDEDOR fora da etapa PENDENCIAS (sem vínculo de correção): 403.
        Com contrato em PENDENCIAS + pendência aberta correspondente à seção
        editada, edição permitida (Validação [9] — ver roteiro [9]).
    A5. Trava financeira (ComprovanteTC ativo previamente criado):
        - POST proposta.valor_af=NOVO: 409 com `campo_bloqueado=proposta.valor_af`.
        - POST proposta.valor_af=ATUAL (noop): 200 ok (sem diff, sem bloqueio).
    A6. Validação de obrigatoriedade:
        - POST cliente.nome_completo=""  → 400, `campos_invalidos` inclui
          "cliente.nome_completo não pode ficar vazio."; DP inalterado.
    A7. Validação de não-negatividade:
        - POST proposta.valor_af=-1.00 → 400, `campos_invalidos` inclui
          "proposta.valor_af não pode ser negativo."; PD inalterado.
    A8. Validação de prazo:
        - POST proposta.prazo=0 → 400, `campos_invalidos` inclui
          "proposta.prazo deve ser >= 1.".
    A9. Alias `cliente.rg` → `numero_rg` é respeitado tanto no GET (ficha)
        quanto no POST (editar) mantendo retrocompatibilidade.

B. api_post_excluir_cliente_arquivo — NOVO
    B1. OPERACIONAL exclui arquivo do próprio contrato:
        - Cria ClienteArquivo CA ligado a DP de CE. `CA.arquivo.storage.exists`.
        - POST {contrato_id: CE.id, arquivo_id: CA.id} → 200 ok.
        - Assert: ClienteArquivo inexistente; arquivo físico removido do
          storage (`default_storage.exists(CA.arquivo.name)` == False).
        - Assert: HistoricoTransicaoContrato com observação "Arquivo
          excluído (operacional): <titulo>".
    B2. SUPERVISOR exclui arquivo de outro cliente (cross-tenant):
        - Cria DP2/CE2 e CA2 ligado a DP2. POST {contrato_id=CE.id,
          arquivo_id=CA2.id} → 403 "Arquivo não pertence a este contrato.".
        - CA2 permanece íntegro; nenhum histórico adicional.
    B3. VENDEDOR tenta excluir: 403.
    B4. Payload faltante: POST sem `arquivo_id` → 400.
    B5. Arquivo físico já removido do disco mas row presente:
        - `CA.arquivo.delete()` manual antes da chamada; endpoint ainda
          retorna 200 e apaga a row (log warning, sem 500).

C. Signal `post_delete` em ClienteArquivo (defesa em profundidade)
    C1. Deleção via ORM direto (`CA.delete()`) também remove arquivo físico.
    C2. Cascata via DP.delete() remove CAs e seus arquivos físicos.
    C3. Quando o arquivo físico não existe mais, o signal loga warning e
        NÃO reescala a exceção — `CA.delete()` completa.

D. Permissões (gate backend + UI)
    D1. Endpoint `api/v2/cliente-arquivo/excluir/` exige SCT189 (403 para
        usuário sem permissão mesmo logado).
    D2. Endpoint `api/v2/contrato/editar-dados/`: operacional/supervisor com
        SCT189; vendedor autenticado sem SCT189 pode corrigir apenas em
        PENDENCIAS conforme roteiro [9].
    D3. O botão `#btnFichaEditar` do modal Ficha (CRM v2) e `.btn-editar-op`
        do grid supervisor usam `data-acess="SCT189"` — UI esconde para
        papéis sem permissão (checagem via template filter ou custom script).

E. Frontend (integração manual / smoke)
    E1. CRM v2: clicar em "Editar" na ficha abre modalEditarDados com a
        aba "Dados & Proposta" ativa e os inputs pré-populados via
        `data-edit-field` (nome, email, telefone, RG, numero_contrato,
        link_formalizacao, coeficiente, etc.).
    E2. CRM v2: alternar para a aba "Arquivos" exibe a lista vinda de
        `midia-arquivos`; upload adiciona item sem recarregar a página;
        excluir remove o item imediatamente.
    E3. Supervisor: clicar no botão Editar (ícone de lápis) na coluna Ações
        abre `modalEditarDadosSup` com mesma experiência do CRM v2.
    E4. Após salvar com sucesso, a grid é recarregada e aparece toast
        "Alterações registradas.".
    E5. 409 de campo bloqueado é apresentado no alerta amarelo dentro da
        aba "Dados & Proposta" (não silencia a resposta).
    E6. 400 com `campos_invalidos` é concatenado ao texto do alerta.
    E7. Visual regression: ambos os modais compartilham a mesma estrutura
        visual (header/tabs/footer); responsivo em viewports 375px/768px.

F. Auditoria / timeline
    F1. Toda edição (cliente/proposta/contrato/arquivos) gera exatamente um
        registro em `HistoricoTransicaoContrato` por chamada de API.
    F2. Observação contém o papel do usuário (operacional/supervisor) e a
        lista resumida de campos alterados OU "Arquivo excluído: <titulo>".
    F3. O modal de linha do tempo (`modalTimelineSup` / `modalAuditoriaCrm`)
        exibe os novos registros após F5 reload.

G. Regressão (garantia de que nada mais quebrou)
    G1. Editar apenas `dados_operacionais` (fluxo legado) continua funcionando.
    G2. `api_get_ficha` sem `with_historico=0` ainda retorna `historico`.
    G3. Upload de ClienteArquivo em outro contrato do mesmo cliente continua
        listando o arquivo em ambos os contratos.
"""

"""
═══════════════════════════════════════════════════════════════════════════════
Validação [9] — PENDÊNCIAS (operacional cria / vendedor corrige)
═══════════════════════════════════════════════════════════════════════════════

P1. Criação (operacional, SCT189):
    - POST /contratos/api/v2/pendencia/ com tipos=[DADOS_CLIENTE,DADOS_PROPOSTA]
      e observacao obrigatória → 200; N registros Pendencia; supervisor não
      cria (403 se papel != operacional).
    - POST sem tipos nem tipo → 400.
    - POST sem observacao → 400.

P2. CRM v2: botão amarelo de pendências na coluna Ações (contrato) abre
    modalPendencias; GET pendencias preenche lista; checkboxes + salvar
    disparam POST com array tipos.

P3. Consulta cliente: card Operacional com tem_pendencia exibe botão amarelo
    "Pendências" (contrato em PENDENCIAS ou solicitação em PENDENTE_CORRECAO
    sem CE); abre modalCorrecaoPendencia com abas só dos tipos em aberto;
    GET ficha tipo=solicitacao_dig permitido ao vendedor dono da carteira
    (ApiGetFichaSolicitacaoDigVendedorPendenciaTest); sem exclusão de arquivos na lista.

P4. Vendedor: GET ficha e GET midia-arquivos e GET pendencias com contrato na
    própria carteira em PENDENCIAS → 200; fora disso → 403.

P5. Vendedor: POST editar-dados só envia cliente se existir pendência
    DADOS_CLIENTE aberta; idem proposta; contrato/dados_operacionais → 400.

P6. Vendedor: POST cliente-arquivo só com pendência FALTA_ARQUIVO aberta.

P7. Resolver: POST pendencia/resolver com vendedor dono da carteira → 200;
    ao zerar pendências abertas, transição pendencia_corrigido retorna etapa
    de origem.

P8. loja.html (INSS): fluxo de pendência operacional INSS permanece separado
    do modelo Pendencia de contratos v2 — não misturar cenários no mesmo teste.

P9. Timeline: criação via pendencia_entrar e edições via editar-dados geram
    HistoricoTransicaoContrato com papel na observação.
"""

"""
═══════════════════════════════════════════════════════════════════════════════
Validação [11] — Relatório CMS (Financeiro – Jaci)
═══════════════════════════════════════════════════════════════════════════════

R11. GET /contratos/api/v2/relatorio-cms/meta/ (autenticado + SCT203):
     resposta com ok/success; chaves bancos, convenios, produtos, classificadores,
     funcionarios, status_cms_financeiro.

R12. GET /contratos/api/v2/relatorio-cms/?banco_id=&status=&status_cms_financeiro=pendente
     &classificador=M1&funcionario_id=&busca=&data_ini=&data_fim= → 200; itens coerentes.

R13. Proposta em PG_PAGO_TC_PARCIAL e PG_PAGO_TC_TOTAL aparecem; ao evoluir TC
     parcial→total, novo GET reflete sub_status e valor_pago_tc.

R14. POST /contratos/api/v2/relatorio-cms/pago-cms-empresa/ com JSON
     {contrato_id, contrato_execucao_id} em sub permitido → ok; já EMPRESA ou
     sub inválido → 4xx conforme API.

R15. POST /contratos/api/v2/relatorio-cms/ajustar-af/ com percentual (ou percentual_af)
     → percentual_af_manual persistido; HistoricoTransicaoContrato com observação
     contendo percentual anterior e novo.

R16. Usuário sem SCT203 → GET/POST relatório-cms retornam negação de acesso.

R17. Menu lateral: entrada «Contratos — Financeiro» / «Relatório CMS» visível só com
     permissão SCT203 (COD_SCT203).

R18. UI: links de comprovantes TC abrem arquivo; colunas AF, % manual, CMS rec/rep,
     status financeiro CMS (Pendente / Pago Empresa).
"""

from decimal import Decimal
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase


class RelatorioCmsHelpersTest(SimpleTestCase):
    """Testes leves sem banco — helpers do módulo relatorio_cms."""

    def test_taxa_snapshot_prefere_campo_snapshot(self):
        from types import SimpleNamespace

        from apps.contratos_v2.apis import relatorio_cms as rc

        d = SimpleNamespace(
            taxa_recebido_snapshot=Decimal('1.25'),
            tabela_cms_id=1,
            tabela_cms=SimpleNamespace(taxa_recebido=Decimal('9.99')),
        )
        self.assertEqual(
            rc._taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido'),
            Decimal('1.25'),
        )

    def test_taxa_snapshot_cai_na_tabela_se_snapshot_nulo(self):
        from types import SimpleNamespace

        from apps.contratos_v2.apis import relatorio_cms as rc

        d = SimpleNamespace(
            taxa_recebido_snapshot=None,
            tabela_cms_id=1,
            tabela_cms=SimpleNamespace(taxa_recebido=Decimal('3')),
        )
        self.assertEqual(
            rc._taxa_snapshot_ou_tabela(d, 'taxa_recebido_snapshot', 'taxa_recebido'),
            Decimal('3'),
        )


class RelatorioCmsBaseAfFluxoTest(SimpleTestCase):
    """Base AF e classificador efetivo (fluxo) — sem banco."""

    def test_base_af_para_cms_prioriza_valor_af_base_cms(self):
        from types import SimpleNamespace

        from apps.contratos_v2.cms_financeiro_base import base_af_para_cms

        d = SimpleNamespace(
            valor_af_base_cms=Decimal('1500'),
            valor_af=Decimal('2000'),
            percentual_af_manual=Decimal('100'),
        )
        self.assertEqual(base_af_para_cms(d), Decimal('1500.00'))

    def test_base_af_para_cms_usa_percentual_manual_sem_base_explicita(self):
        from types import SimpleNamespace

        from apps.contratos_v2.cms_financeiro_base import base_af_para_cms

        d = SimpleNamespace(
            valor_af_base_cms=None,
            valor_af=Decimal('2000'),
            percentual_af_manual=Decimal('50'),
        )
        self.assertEqual(base_af_para_cms(d), Decimal('1000.00'))

    def test_classificador_banco_efetivo_override(self):
        from types import SimpleNamespace

        from apps.contratos_v2.cms_financeiro_base import classificador_banco_efetivo

        d = SimpleNamespace(
            classificador_banco_operacional='M3',
            tabela_cms_id=1,
            tabela_cms=SimpleNamespace(classificador_banco='M1'),
        )
        self.assertEqual(classificador_banco_efetivo(d), 'M3')


class ValorTcEfetivoParaFluxoTest(SimpleTestCase):
    """TC efetivo: snapshot (DO) com fallback na proposta — sem banco."""

    def test_prioriza_valor_tc_do_snapshot_quando_positivo(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_transicoes import valor_tc_efetivo_para_fluxo

        ce = SimpleNamespace(
            dados_operacionais=SimpleNamespace(valor_tc=Decimal('200')),
            proposta_dados=SimpleNamespace(valor_tc=Decimal('50')),
        )
        self.assertEqual(valor_tc_efetivo_para_fluxo(ce), Decimal('200'))

    def test_usa_proposta_quando_snapshot_zero_ou_nulo(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_transicoes import valor_tc_efetivo_para_fluxo

        ce = SimpleNamespace(
            dados_operacionais=SimpleNamespace(valor_tc=Decimal('0')),
            proposta_dados=SimpleNamespace(valor_tc=Decimal('350')),
        )
        self.assertEqual(valor_tc_efetivo_para_fluxo(ce), Decimal('350'))

    def test_usa_proposta_quando_snapshot_tc_nulo(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_transicoes import valor_tc_efetivo_para_fluxo

        ce = SimpleNamespace(
            dados_operacionais=SimpleNamespace(valor_tc=None),
            proposta_dados=SimpleNamespace(valor_tc=Decimal('99.50')),
        )
        self.assertEqual(valor_tc_efetivo_para_fluxo(ce), Decimal('99.50'))

    def test_retorna_zero_sem_fontes(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_transicoes import valor_tc_efetivo_para_fluxo

        ce = SimpleNamespace(
            dados_operacionais=SimpleNamespace(valor_tc=None),
            proposta_dados=SimpleNamespace(valor_tc=None),
        )
        self.assertEqual(valor_tc_efetivo_para_fluxo(ce), Decimal('0'))


class EspelharPropostaFinanceirosDoTest(SimpleTestCase):
    """Espelhamento PD → DO após editar-dados (helpers) — sem banco."""

    def test_espelhar_atualiza_tc_e_liberado_no_snapshot(self):
        from apps.contratos_v2.apis.acoes_crm import _espelhar_proposta_financeiros_em_do

        class Snap:
            def __init__(self):
                self.valor_parcela = Decimal('100')
                self.prazo = 96
                self.valor_af = Decimal('11341.86')
                self.valor_tc = Decimal('0')
                self.valor_liberado = Decimal('11341.86')
                self.saved_fields = None

            def save(self, update_fields=None):
                self.saved_fields = update_fields

        d = Snap()
        pd = type(
            'Pd',
            (),
            {
                'valor_parcela': Decimal('100'),
                'prazo': 96,
                'valor_af': Decimal('11341.86'),
                'valor_tc': Decimal('250'),
                'valor_liberado': Decimal('11091.86'),
            },
        )()
        pp_payload = {'valor_tc': '250,00'}
        campos = []
        _espelhar_proposta_financeiros_em_do(d, pd, pp_payload, campos)
        self.assertEqual(d.valor_tc, Decimal('250'))
        self.assertEqual(d.valor_liberado, Decimal('11091.86'))
        self.assertTrue(any('dados_operacionais.valor_tc' in c for c in campos))
        self.assertIsNotNone(d.saved_fields)
        self.assertIn('valor_tc', d.saved_fields)


class PapelUsuarioCargoOperacoesTest(SimpleTestCase):
    """Cargo «Assistente de Operações» deve mapear para papel operacional (CRM/pendências)."""

    def test_assistente_operacoes_retorna_operacional(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from apps.contratos_v2.apis.acoes_crm import _papel_usuario

        stub_fun = SimpleNamespace(
            cargo_id=1,
            cargo=SimpleNamespace(nome='Assistente de Operações (PADRAO)'),
        )
        with patch('apps.funcionarios.models.Funcionario.objects') as om:
            om.select_related.return_value.filter.return_value.first.return_value = stub_fun
            self.assertEqual(_papel_usuario(SimpleNamespace()), 'operacional')

    def test_operacoes_sem_acento_no_cargo_retorna_operacional(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from apps.contratos_v2.apis.acoes_crm import _papel_usuario

        stub_fun = SimpleNamespace(cargo_id=1, cargo=SimpleNamespace(nome='ANALISTA DE OPERACOES'))
        with patch('apps.funcionarios.models.Funcionario.objects') as om:
            om.select_related.return_value.filter.return_value.first.return_value = stub_fun
            self.assertEqual(_papel_usuario(SimpleNamespace()), 'operacional')


class SolicitacaoDigitacaoPreContratoTest(SimpleTestCase):
    """Pré-contrato: estados pendência/cancelar e transições do Evoluir (sem DB)."""

    def test_permite_gerar_contrato_somente_fila_ativa(self):
        from apps.contratos_v2.apis.fluxo import _solicitacao_digitacao_permite_gerar_contrato
        from apps.contratos_v2.fluxo_constants import EstadoSolicitacaoDigitacao as E

        self.assertTrue(_solicitacao_digitacao_permite_gerar_contrato(E.PENDENTE_OPERACIONAL))
        self.assertTrue(_solicitacao_digitacao_permite_gerar_contrato(E.EM_DIGITACAO))
        self.assertFalse(_solicitacao_digitacao_permite_gerar_contrato(E.PENDENTE_CORRECAO))
        self.assertFalse(_solicitacao_digitacao_permite_gerar_contrato(E.CANCELADA))
        self.assertFalse(_solicitacao_digitacao_permite_gerar_contrato(E.CONTRATO_GERADO))

    def test_transicoes_disponiveis_por_estado(self):
        from types import SimpleNamespace

        from apps.contratos_v2.apis.fluxo import _transicoes_disponiveis_solicitacao_digitacao
        from apps.contratos_v2.fluxo_constants import EstadoSolicitacaoDigitacao as E

        def acoes(est):
            sol = SimpleNamespace(estado=est)
            return {t['acao'] for t in _transicoes_disponiveis_solicitacao_digitacao(sol)}

        esperado_ativo = {
            'gerar_contrato',
            'operacional_solicitacao_marcar_pendencia',
            'operacional_solicitacao_cancelar',
        }
        self.assertEqual(acoes(E.PENDENTE_OPERACIONAL), esperado_ativo)
        self.assertEqual(acoes(E.EM_DIGITACAO), esperado_ativo)
        self.assertEqual(acoes(E.PENDENTE_CORRECAO), {'operacional_solicitacao_reabrir'})
        self.assertEqual(acoes(E.CANCELADA), set())
        self.assertEqual(acoes(E.CONTRATO_GERADO), set())


class ApiGetFichaSolicitacaoDigVendedorPendenciaTest(SimpleTestCase):
    """P3 ext.: GET ficha solicitacao_dig sem SCT189 — vendedor dono em PENDENTE_CORRECAO."""

    def test_vendedor_responsavel_carteira_retorna_200(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis import fluxo

        rf = RequestFactory()
        user = MagicMock()
        user.id = 42
        user.is_authenticated = True
        request = rf.get('/contratos/api/v2/ficha/', {'tipo': 'solicitacao_dig', 'id': '7', 'with_historico': '0'})
        request.user = user

        sol = MagicMock()
        sol.estado = 'PENDENTE_CORRECAO'
        cart = MagicMock()
        cart.user_responsavel_id = 42
        sol.carteira_clientes = cart

        qs_seguro = MagicMock()
        qs_seguro.filter.return_value.select_related.return_value.first.return_value = sol

        with patch.object(fluxo, 'user_has_access', return_value=False):
            with patch.object(fluxo, '_solicitacao_digitacao_queryset_schema_seguro', return_value=qs_seguro):
                with patch.object(
                    fluxo,
                    '_ficha_montar_payload',
                    return_value={'dados_pessoais': {'id': 1}, 'propostas': [], 'contrato': None},
                ) as mfp:
                    resp = fluxo.api_get_ficha(request)

        self.assertEqual(resp.status_code, 200)
        mfp.assert_called_once_with('solicitacao_dig', 7)

    def test_usuario_nao_responsavel_retorna_403(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis import fluxo

        rf = RequestFactory()
        user = MagicMock()
        user.id = 1
        user.is_authenticated = True
        request = rf.get('/contratos/api/v2/ficha/', {'tipo': 'solicitacao_dig', 'id': '3'})
        request.user = user

        sol = MagicMock()
        sol.estado = 'PENDENTE_CORRECAO'
        sol.proposta_dados_id = None
        cart = MagicMock()
        cart.user_responsavel_id = 999
        cart.user_repasse_id = 888
        sol.carteira_clientes = cart

        qs_seguro = MagicMock()
        qs_seguro.filter.return_value.select_related.return_value.first.return_value = sol

        with patch.object(fluxo, 'user_has_access', return_value=False):
            with patch.object(fluxo, '_solicitacao_digitacao_queryset_schema_seguro', return_value=qs_seguro):
                resp = fluxo.api_get_ficha(request)

        self.assertEqual(resp.status_code, 403)


class ApiGetFichaSolicitacaoDigRepasseCarteiraTest(SimpleTestCase):
    """GET ficha solicitacao_dig sem SCT189 — usuário de repasse da carteira em PENDENTE_CORRECAO."""

    def test_repasse_carteira_retorna_200(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis import fluxo

        rf = RequestFactory()
        user = MagicMock()
        user.id = 55
        user.is_authenticated = True
        request = rf.get('/contratos/api/v2/ficha/', {'tipo': 'solicitacao_dig', 'id': '21', 'with_historico': '0'})
        request.user = user

        sol = MagicMock()
        sol.estado = 'PENDENTE_CORRECAO'
        cart = MagicMock()
        cart.user_responsavel_id = 999
        cart.user_repasse_id = 55
        sol.carteira_clientes = cart

        qs_seguro = MagicMock()
        qs_seguro.filter.return_value.select_related.return_value.first.return_value = sol

        with patch.object(fluxo, 'user_has_access', return_value=False):
            with patch.object(fluxo, '_solicitacao_digitacao_queryset_schema_seguro', return_value=qs_seguro):
                with patch.object(
                    fluxo,
                    '_ficha_montar_payload',
                    return_value={'dados_pessoais': {'id': 1}, 'propostas': [], 'contrato': None},
                ) as mfp:
                    resp = fluxo.api_get_ficha(request)

        self.assertEqual(resp.status_code, 200)
        mfp.assert_called_once_with('solicitacao_dig', 21)


class ObservacaoPendenciaCorrecaoDigitacaoTest(SimpleTestCase):
    """Observação do operacional na ficha pré-contrato (histórico de marcar pendência)."""

    def test_retorna_texto_do_ultimo_evento_pendente_correcao(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.apis.fluxo import _observacao_pendencia_correcao_digitacao
        from apps.contratos_v2.fluxo_constants import EstadoSolicitacaoDigitacao as E

        h = MagicMock()
        h.observacao = '  Ajustar RG e margem  '
        qs = MagicMock()
        qs.filter.return_value.exclude.return_value.order_by.return_value.only.return_value.first.return_value = h
        sol = MagicMock()
        sol.pk = 1
        sol.historico_eventos = qs

        self.assertEqual(_observacao_pendencia_correcao_digitacao(sol), 'Ajustar RG e margem')
        qs.filter.assert_called_once()
        args, kwargs = qs.filter.call_args
        self.assertEqual(kwargs.get('estado_novo'), E.PENDENTE_CORRECAO)
        qs.filter.return_value.exclude.assert_called_once()
        ex_args, ex_kwargs = qs.filter.return_value.exclude.call_args
        self.assertEqual(ex_kwargs.get('estado_anterior'), E.PENDENTE_CORRECAO)

    def test_sem_pk_retorna_vazio(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.apis.fluxo import _observacao_pendencia_correcao_digitacao

        sol = MagicMock()
        sol.pk = None
        self.assertEqual(_observacao_pendencia_correcao_digitacao(sol), '')


class ApiPostSolicitacaoDigCorrecaoConcluidaTest(SimpleTestCase):
    """POST correcao-concluida: permissão e validações básicas."""

    def test_409_quando_ja_existe_contrato_execucao(self):
        from unittest.mock import MagicMock, patch

        from django.test import RequestFactory

        from apps.contratos_v2.apis import fluxo

        rf = RequestFactory()
        req = rf.post(
            '/contratos/api/v2/solicitacao-dig/9/correcao-concluida/',
            data=b'{}',
            content_type='application/json',
        )
        user = MagicMock()
        user.id = 1
        user.is_authenticated = True
        req.user = user

        chain = MagicMock()
        chain.exists.return_value = True
        with patch.object(fluxo.ContratoExecucao.objects, 'filter', return_value=chain):
            resp = fluxo.api_post_solicitacao_dig_correcao_concluida(req, 9)

        self.assertEqual(resp.status_code, 409)

    def test_403_vendedor_sem_vinculo_carteira(self):
        from unittest.mock import MagicMock, patch

        from django.test import RequestFactory

        from apps.contratos_v2.apis import fluxo

        rf = RequestFactory()
        req = rf.post(
            '/contratos/api/v2/solicitacao-dig/5/correcao-concluida/',
            data=b'{}',
            content_type='application/json',
        )
        user = MagicMock()
        user.id = 1
        user.is_authenticated = True
        req.user = user

        sol = MagicMock()
        sol.estado = 'PENDENTE_CORRECAO'
        sol.carteira_clientes = MagicMock()
        sol.carteira_clientes.user_responsavel_id = 999
        sol.carteira_clientes.user_repasse_id = 888

        qs = MagicMock()
        qs.select_related.return_value.filter.return_value.first.return_value = sol

        chain_ce = MagicMock()
        chain_ce.exists.return_value = False

        with patch.object(fluxo.ContratoExecucao.objects, 'filter', return_value=chain_ce):
            with patch.object(fluxo, '_solicitacao_digitacao_queryset_schema_seguro', return_value=qs):
                with patch.object(fluxo, 'user_has_access', return_value=False):
                    resp = fluxo.api_post_solicitacao_dig_correcao_concluida(req, 5)

        self.assertEqual(resp.status_code, 403)

    def test_400_estado_diferente_de_pendente_correcao(self):
        from unittest.mock import MagicMock, patch

        from django.test import RequestFactory

        from apps.contratos_v2.apis import fluxo

        rf = RequestFactory()
        req = rf.post(
            '/contratos/api/v2/solicitacao-dig/3/correcao-concluida/',
            data=b'{}',
            content_type='application/json',
        )
        user = MagicMock()
        user.id = 1
        user.is_authenticated = True
        req.user = user

        sol = MagicMock()
        sol.estado = 'PENDENTE_OPERACIONAL'
        sol.carteira_clientes = MagicMock()

        qs = MagicMock()
        qs.select_related.return_value.filter.return_value.first.return_value = sol

        chain_ce = MagicMock()
        chain_ce.exists.return_value = False

        with patch.object(fluxo.ContratoExecucao.objects, 'filter', return_value=chain_ce):
            with patch.object(fluxo, '_solicitacao_digitacao_queryset_schema_seguro', return_value=qs):
                resp = fluxo.api_post_solicitacao_dig_correcao_concluida(req, 3)

        self.assertEqual(resp.status_code, 400)


class ResolveLojaRegisterMoneyRmPayloadTest(SimpleTestCase):
    """Pago TC: rm_payload com venda_associada_loja / loja_id (M2M funcionário)."""

    def test_sem_chave_venda_associada_usa_loja_do_contrato(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import resolve_loja_register_money_de_rm_payload

        ce = MagicMock()
        fake_loja = object()
        with patch('apps.contratos_v2.fluxo_transicoes._loja_from_contrato', return_value=fake_loja):
            r = resolve_loja_register_money_de_rm_payload(ce, {'valor_est': '100'})
        self.assertIs(r, fake_loja)

    def test_venda_false_retorna_sem_loja(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import resolve_loja_register_money_de_rm_payload

        ce = MagicMock()
        with patch('apps.contratos_v2.fluxo_transicoes._loja_from_contrato') as m_loja:
            r = resolve_loja_register_money_de_rm_payload(ce, {'venda_associada_loja': False})
        m_loja.assert_not_called()
        self.assertIsNone(r)

    def test_venda_true_com_loja_id_elegivel(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import resolve_loja_register_money_de_rm_payload

        ce = MagicMock()
        mock_loja = MagicMock()
        with patch(
            'apps.contratos_v2.fluxo_transicoes.lojas_elegiveis_m2m_destinatarios_register_money_ce',
            return_value=[{'id': 5, 'nome': 'LOJA TESTE'}],
        ):
            with patch('apps.funcionarios.models.Loja.objects.filter') as qf:
                qf.return_value.first.return_value = mock_loja
                r = resolve_loja_register_money_de_rm_payload(
                    ce, {'venda_associada_loja': True, 'loja_id': 5}
                )
        self.assertIs(r, mock_loja)

    def test_venda_true_loja_id_fora_da_lista_raises(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import resolve_loja_register_money_de_rm_payload

        ce = MagicMock()
        with patch(
            'apps.contratos_v2.fluxo_transicoes.lojas_elegiveis_m2m_destinatarios_register_money_ce',
            return_value=[{'id': 5, 'nome': 'LOJA A'}],
        ):
            with self.assertRaises(ValueError) as ctx:
                resolve_loja_register_money_de_rm_payload(
                    ce, {'venda_associada_loja': True, 'loja_id': 999}
                )
        self.assertIn('elegível', str(ctx.exception).lower())

    def test_venda_true_sem_loja_id_raises(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import resolve_loja_register_money_de_rm_payload

        ce = MagicMock()
        with patch(
            'apps.contratos_v2.fluxo_transicoes.lojas_elegiveis_m2m_destinatarios_register_money_ce',
            return_value=[{'id': 5, 'nome': 'LOJA A'}],
        ):
            with self.assertRaises(ValueError):
                resolve_loja_register_money_de_rm_payload(
                    ce, {'venda_associada_loja': True, 'loja_id': None}
                )


class PersistirTcModalContratoRmTest(SimpleTestCase):
    """persistir_tc_modal_em_contrato_e_rm e extrator JSON do comprovante (sem banco)."""

    def test_rejeita_tc_zero(self):
        from decimal import Decimal
        from unittest.mock import MagicMock

        from apps.contratos_v2.fluxo_transicoes import persistir_tc_modal_em_contrato_e_rm

        ce = MagicMock()
        ce.dados_operacionais = MagicMock()
        ok, msg = persistir_tc_modal_em_contrato_e_rm(ce, Decimal('0'), Decimal('0'))
        self.assertFalse(ok)
        self.assertIsNotNone(msg)

    def test_rejeita_tc_menor_que_soma_comprovantes(self):
        from decimal import Decimal
        from unittest.mock import MagicMock

        from apps.contratos_v2.fluxo_transicoes import persistir_tc_modal_em_contrato_e_rm

        ce = MagicMock()
        ce.dados_operacionais = MagicMock()
        ok, msg = persistir_tc_modal_em_contrato_e_rm(ce, Decimal('100'), Decimal('150'))
        self.assertFalse(ok)
        self.assertIn('comprovantes', msg.lower())

    def test_sem_dados_operacionais(self):
        from decimal import Decimal
        from unittest.mock import MagicMock

        from apps.contratos_v2.fluxo_transicoes import persistir_tc_modal_em_contrato_e_rm

        ce = MagicMock()
        ce.dados_operacionais = None
        ok, msg = persistir_tc_modal_em_contrato_e_rm(ce, Decimal('200'), Decimal('0'))
        self.assertFalse(ok)

    def test_um_rm_atualiza_valor_est_e_snapshot(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import persistir_tc_modal_em_contrato_e_rm

        d = MagicMock()
        pd = MagicMock()
        ce = MagicMock()
        ce.dados_operacionais = d
        ce.proposta_dados = pd
        rm = MagicMock()
        rm.flag_repasse = False
        chain = MagicMock()
        chain.filter.return_value.order_by.return_value = [rm]
        with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain):
            ok, msg = persistir_tc_modal_em_contrato_e_rm(ce, Decimal('300'), Decimal('50'))
        self.assertTrue(ok)
        self.assertIsNone(msg)
        self.assertEqual(rm.valor_est, Decimal('300'))
        d.save.assert_called_once()
        pd.save.assert_called_once()

    def test_dois_rm_repasse_metade(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import persistir_tc_modal_em_contrato_e_rm

        d = MagicMock()
        ce = MagicMock()
        ce.dados_operacionais = d
        ce.proposta_dados = None
        r1 = MagicMock(flag_repasse=True)
        r2 = MagicMock(flag_repasse=True)
        chain = MagicMock()
        chain.filter.return_value.order_by.return_value = [r1, r2]
        with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain):
            ok, msg = persistir_tc_modal_em_contrato_e_rm(ce, Decimal('100'), Decimal('20'))
        self.assertTrue(ok)
        self.assertEqual(r1.valor_est, Decimal('50.00'))
        self.assertEqual(r2.valor_est, Decimal('50.00'))


class ZerarTcModalEmContratoTest(SimpleTestCase):
    """zerar_tc_modal_em_contrato (sem banco)."""

    def test_sucesso_zerar_do_pd_e_rm(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import zerar_tc_modal_em_contrato

        d = MagicMock()
        pd = MagicMock()
        ce = MagicMock()
        ce.pk = 1
        ce.dados_operacionais = d
        ce.proposta_dados = pd
        rm = MagicMock(flag_repasse=False)
        chain = MagicMock()
        chain.filter.return_value.order_by.return_value = [rm]
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('500')):
            with patch('apps.contratos_v2.fluxo_transicoes.ComprovanteTC.objects.filter') as mcomp:
                mcomp.return_value.exists.return_value = False
                with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain):
                    ok, msg = zerar_tc_modal_em_contrato(ce)
        self.assertTrue(ok)
        self.assertIsNone(msg)
        self.assertEqual(d.valor_tc, Decimal('0'))
        self.assertEqual(pd.valor_tc, Decimal('0'))
        self.assertEqual(rm.valor_est, Decimal('0'))

    def test_bloqueia_com_comprovante_ativo(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import zerar_tc_modal_em_contrato

        ce = MagicMock()
        ce.dados_operacionais = MagicMock()
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('100')):
            with patch('apps.contratos_v2.fluxo_transicoes.ComprovanteTC.objects.filter') as mcomp:
                mcomp.return_value.exists.return_value = True
                ok, msg = zerar_tc_modal_em_contrato(ce)
        self.assertFalse(ok)
        self.assertIn('comprovantes', msg.lower())

    def test_bloqueia_ja_sem_tc(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_transicoes import zerar_tc_modal_em_contrato

        ce = MagicMock()
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('0')):
            ok, msg = zerar_tc_modal_em_contrato(ce)
        self.assertFalse(ok)
        self.assertIn('sem', msg.lower())

    def test_montar_rm_aceita_zerar_tc_no_modal(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis.fluxo import _montar_registermoney_extra_supervisor_pago_tc

        d = MagicMock()
        d.valor_af = Decimal('1000')
        d.tabela_cms_id = None
        ce = MagicMock()
        ce.dados_operacionais = d
        with patch('apps.contratos_v2.apis.fluxo._valor_tc_contrato', return_value=Decimal('200')):
            with patch('apps.contratos_v2.apis.fluxo.ClassificacaoValor') as mcv:
                cv = MagicMock()
                cv.id = 7
                mcv.objects.get.return_value = cv
                rm_dict, err = _montar_registermoney_extra_supervisor_pago_tc(
                    {'valor_est_tc': '0', 'classificacao_valor_id': 7, 'af': '1000'},
                    ce,
                )
        self.assertIsNone(err)
        self.assertEqual(rm_dict['valor_est'], Decimal('0'))

    def test_decrementar_acumulado_rm(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis.acoes_crm import _decrementar_acumulado_rm

        ce = MagicMock()
        rm = MagicMock()
        rm.flag_repasse = False
        rm.valor_pago_acumulado = Decimal('100')
        with patch('apps.siape.models.RegisterMoney.objects.filter') as mf:
            mf.return_value = [rm]
            _decrementar_acumulado_rm(ce, Decimal('40'))
        self.assertEqual(rm.valor_pago_acumulado, Decimal('60'))

    def test_valor_est_json_registermoney_post(self):
        from decimal import Decimal

        from apps.contratos_v2.apis.acoes_crm import _valor_est_json_registermoney_post

        self.assertIsNone(_valor_est_json_registermoney_post(''))
        self.assertIsNone(_valor_est_json_registermoney_post('{"outro": 1}'))
        self.assertEqual(_valor_est_json_registermoney_post('{"valor_est": "150.50"}'), Decimal('150.50'))

    def test_rm_payload_de_registermoney_post_vazio(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.apis.acoes_crm import _rm_payload_de_registermoney_post

        ce = MagicMock()
        payload, err = _rm_payload_de_registermoney_post('', ce)
        self.assertIsNone(payload)
        self.assertIn('registro financeiro', err.lower())

    def test_rm_payload_de_registermoney_post_json_invalido(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.apis.acoes_crm import _rm_payload_de_registermoney_post

        ce = MagicMock()
        payload, err = _rm_payload_de_registermoney_post('{invalid', ce)
        self.assertIsNone(payload)
        self.assertIn('json', err.lower())

    def test_rm_payload_de_registermoney_post_monta_dict(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis.acoes_crm import _rm_payload_de_registermoney_post

        ce = MagicMock()
        rm_esperado = {'valor_est': Decimal('100'), 'af': Decimal('1000')}
        with patch(
            'apps.contratos_v2.apis.acoes_crm._montar_registermoney_extra_supervisor_pago_tc',
            return_value=(rm_esperado, None),
        ):
            payload, err = _rm_payload_de_registermoney_post(
                '{"valor_est": "100", "af": "1000", "classificacao_valor_id": 1}',
                ce,
            )
        self.assertIsNone(err)
        self.assertEqual(payload, rm_esperado)


class RepasseCarteiraContratoTest(SimpleTestCase):
    """Repasse SIAPE: snapshot no contrato, resolver e dois RegisterMoney no Pago TC."""

    def test_kwargs_snapshot_com_repasse(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.services.repasse_carteira import kwargs_snapshot_repasse_contrato

        cart = MagicMock()
        cart.id = 10
        cart.user_repasse_id = 55
        kw = kwargs_snapshot_repasse_contrato(cart)
        self.assertEqual(kw['carteira_clientes_snapshot_id'], 10)
        self.assertEqual(kw['user_repasse_snapshot_id'], 55)

    def test_kwargs_snapshot_sem_repasse(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.services.repasse_carteira import kwargs_snapshot_repasse_contrato

        cart = MagicMock()
        cart.user_repasse_id = None
        self.assertEqual(kwargs_snapshot_repasse_contrato(cart), {})

    def test_resolver_contexto_via_snapshot(self):
        from unittest.mock import MagicMock

        from apps.contratos_v2.services.repasse_carteira import resolver_contexto_repasse_contrato

        ur = MagicMock()
        ur.id = 99
        ur.get_full_name.return_value = 'Responsavel Teste'
        ux = MagicMock()
        ux.id = 88
        ux.get_full_name.return_value = 'Repasse Teste'
        cart = MagicMock()
        cart.id = 10
        cart.user_responsavel_id = 99
        cart.user_responsavel = ur
        cart.user_repasse_id = 88
        cart.user_repasse = ux
        ce = MagicMock()
        ce.user_repasse_snapshot_id = 88
        ce.carteira_clientes_snapshot_id = 10
        ce.carteira_clientes_snapshot = cart
        ce.solicitacao_digitacao_id = None
        ce.proposta_dados_id = None
        ctx = resolver_contexto_repasse_contrato(ce)
        self.assertTrue(ctx['tem_repasse'])
        self.assertEqual(ctx['user_repasse_id'], 88)
        self.assertEqual(ctx['user_responsavel_id'], 99)
        self.assertEqual(len(ctx['destinatarios']), 2)

    def test_montar_pago_tc_modal_tem_repasse_via_snapshot(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis.fluxo import _montar_pago_tc_modal_defaults

        d = MagicMock()
        d.valor_af = Decimal('1000')
        d.tabela_cms_id = None
        d.tabela_cms_titulo_snapshot = ''
        ce = MagicMock()
        ce.id = 1
        ce.dados_operacionais = d
        ce.flag_video_enviado = False
        ce.solicitacao_digitacao_id = None
        ce.proposta_dados_id = None
        ce.user_repasse_snapshot_id = 88
        ce.carteira_clientes_snapshot_id = 10
        ur = MagicMock()
        ur.id = 99
        ur.get_full_name.return_value = 'Resp'
        ux = MagicMock()
        ux.id = 88
        ux.get_full_name.return_value = 'Rep'
        cart = MagicMock()
        cart.id = 10
        cart.user_responsavel_id = 99
        cart.user_responsavel = ur
        cart.user_repasse_id = 88
        cart.user_repasse = ux
        ce.carteira_clientes_snapshot = cart
        with patch('apps.contratos_v2.apis.fluxo.valor_tc_efetivo_para_fluxo', return_value=Decimal('200')):
            with patch('apps.contratos_v2.apis.fluxo.lojas_elegiveis_m2m_destinatarios_register_money_ce', return_value=[]):
                with patch('apps.contratos_v2.apis.fluxo.contrato_exige_video_conscientizacao_para_pagamento', return_value=False):
                    with patch('apps.contratos_v2.apis.fluxo.ClassificacaoValor') as mcv:
                        mcv.objects.filter.return_value.order_by.return_value.exists.return_value = False
                        mcv.objects.filter.return_value.order_by.return_value.first.return_value = MagicMock(id=1)
                        mcv.objects.all.return_value.order_by.return_value = []
                        out = _montar_pago_tc_modal_defaults(ce)
        self.assertIsNotNone(out)
        self.assertTrue(out['tem_repasse'])

    def test_disparar_rm_repasse_cria_dois_registros(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import _disparar_registermoney_se_necessario

        ur = MagicMock()
        ur.id = 99
        ux = MagicMock()
        ux.id = 88
        cart = MagicMock()
        cart.id = 10
        cart.user_responsavel_id = 99
        cart.user_responsavel = ur
        cart.user_repasse_id = 88
        cart.user_repasse = ux
        sol = MagicMock()
        sol.carteira_clientes = cart
        sol.carteira_clientes_id = 10
        sol.criado_por_id = 99
        dp = MagicMock()
        dp.cpf = '12345678901'
        ce = MagicMock()
        ce.sub_status_operacional = SubStatusOperacional.PG_PAGO_TC_PARCIAL
        ce.solicitacao_digitacao = sol
        ce.solicitacao_digitacao_id = 1
        ce.cliente_dados_pessoais = dp
        ce.proposta_dados_id = None
        ce.user_repasse_snapshot_id = None
        ce.carteira_clientes_snapshot_id = None
        d = MagicMock()
        d.valor_af = Decimal('500')
        d.produto = None
        ce.dados_operacionais = d
        creates = []

        def _track_create(**kwargs):
            creates.append(kwargs)
            return MagicMock()

        rm_payload = {
            'valor_est': '1000',
            'af': '500',
            'flag_cms_pago': False,
        }
        chain_exists = MagicMock()
        chain_exists.exists.return_value = False
        with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain_exists):
            with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.create', side_effect=_track_create):
                with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('1000')):
                    with patch('apps.contratos_v2.fluxo_transicoes.resolve_loja_register_money_de_rm_payload', return_value=None):
                        with patch('apps.contratos_v2.fluxo_transicoes._proposta_siape_id_para_contrato_execucao', return_value=None):
                            with patch('apps.contratos_v2.fluxo_transicoes._siape_produto_id_por_contratos_produto', return_value=None):
                                with patch('apps.contratos_v2.fluxo_transicoes._org_funcionario_por_user', return_value={}):
                                    with patch('apps.contratos_v2.fluxo_transicoes._sincronizar_valor_pago_tc_acumulado_rm'):
                                        with patch(
                                            'apps.siape.apis.classificador.classificar_tc_automatico',
                                            return_value=('M1', 'NOVO'),
                                        ):
                                            _disparar_registermoney_se_necessario(ce, rm_payload)
        self.assertEqual(len(creates), 2)
        self.assertEqual(creates[0]['user_id'], 99)
        self.assertEqual(creates[0]['valor_est'], Decimal('500.00'))
        self.assertEqual(creates[0]['af'], Decimal('500'))
        self.assertTrue(creates[0]['flag_repasse'])
        self.assertEqual(creates[1]['user_id'], 88)
        self.assertEqual(creates[1]['valor_est'], Decimal('500.00'))
        self.assertIsNone(creates[1]['af'])
        self.assertIsNone(creates[1]['valor_cms_recebido'])


class FluxoPagamentoTcParcialTransicoesTest(SimpleTestCase):
    """Transições Pago TC parcial/total e validação de POST evoluir (sem banco)."""

    def test_parcial_lista_inclui_operacional_pago_tc(self):
        from decimal import Decimal
        from types import SimpleNamespace
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import transicoes_disponiveis_contrato_execucao

        ce = SimpleNamespace(
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional=SubStatusOperacional.PG_PAGO_TC_PARCIAL,
        )
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('100')):
            trans = transicoes_disponiveis_contrato_execucao(ce)
        acoes = {t['acao'] for t in trans}
        self.assertIn('operacional_pago_tc', acoes)

    def test_total_lista_inclui_operacional_aguardando_cms(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import transicoes_disponiveis_contrato_execucao

        ce = SimpleNamespace(
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional=SubStatusOperacional.PG_PAGO_TC_TOTAL,
        )
        trans = transicoes_disponiveis_contrato_execucao(ce)
        acoes = {t['acao'] for t in trans}
        self.assertIn('operacional_aguardando_cms', acoes)

    def test_legado_pago_tc_lista_inclui_aguardando_cms(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import transicoes_disponiveis_contrato_execucao

        ce = SimpleNamespace(
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional=SubStatusOperacional.PG_PAGO_TC,
        )
        trans = transicoes_disponiveis_contrato_execucao(ce)
        acoes = {t['acao'] for t in trans}
        self.assertIn('operacional_aguardando_cms', acoes)

    def test_operacional_aguardando_cms_aceita_pago_tc_total(self):
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import PAPEL_OPERACIONAL, transicao_por_acao

        ce = MagicMock()
        ce.etapa_operacional = EtapaOperacional.PAGAMENTO
        ce.sub_status_operacional = SubStatusOperacional.PG_PAGO_TC_TOTAL
        user = MagicMock()
        with patch('apps.contratos_v2.fluxo_transicoes.aplicar_etapa_sub', return_value=(True, '')):
            ok, msg = transicao_por_acao(
                ce, user, PAPEL_OPERACIONAL, 'operacional_aguardando_cms', observacao='x'
            )
        self.assertTrue(ok)
        self.assertEqual(msg, '')

    def test_operacional_pago_tc_bloqueado_em_parcial_quando_ja_tem_rm(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import PAPEL_OPERACIONAL, transicao_por_acao

        ce = MagicMock()
        ce.etapa_operacional = EtapaOperacional.PAGAMENTO
        ce.sub_status_operacional = SubStatusOperacional.PG_PAGO_TC_PARCIAL
        user = MagicMock()
        extras = {'registermoney': {'valor_est': '100', 'af': '1000'}}
        chain_rm = MagicMock()
        chain_rm.exists.return_value = True
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('50')):
            with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain_rm):
                ok, msg = transicao_por_acao(
                    ce, user, PAPEL_OPERACIONAL, 'operacional_pago_tc', extras=extras
                )
        self.assertFalse(ok)
        self.assertIn('comprovante', msg.lower())

    def test_operacional_pago_tc_parcial_sem_rm_exige_comprovantes(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import PAPEL_OPERACIONAL, transicao_por_acao

        ce = MagicMock()
        ce.etapa_operacional = EtapaOperacional.PAGAMENTO
        ce.sub_status_operacional = SubStatusOperacional.PG_PAGO_TC_PARCIAL
        user = MagicMock()
        extras = {'registermoney': {'valor_est': '100', 'af': '1000'}}
        chain_rm = MagicMock()
        chain_rm.exists.return_value = False
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('100')):
            with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain_rm):
                with patch('apps.contratos_v2.fluxo_transicoes._soma_comprovantes_tc_ativos', return_value=Decimal('0')):
                    ok, msg = transicao_por_acao(
                        ce, user, PAPEL_OPERACIONAL, 'operacional_pago_tc', extras=extras
                    )
        self.assertFalse(ok)
        self.assertIn('comprovante', msg.lower())

    def test_operacional_pago_tc_parcial_sem_rm_cria_registermoney(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import PAPEL_OPERACIONAL, transicao_por_acao

        ce = MagicMock()
        ce.etapa_operacional = EtapaOperacional.PAGAMENTO
        ce.sub_status_operacional = SubStatusOperacional.PG_PAGO_TC_PARCIAL
        user = MagicMock()
        extras = {'registermoney': {'valor_est': '100', 'af': '1000'}}
        chain_rm = MagicMock()
        chain_rm.exists.return_value = False
        with patch('apps.contratos_v2.fluxo_transicoes._valor_tc_contrato', return_value=Decimal('100')):
            with patch('apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter', return_value=chain_rm):
                with patch('apps.contratos_v2.fluxo_transicoes._soma_comprovantes_tc_ativos', return_value=Decimal('40')):
                    with patch('apps.contratos_v2.fluxo_transicoes.aplicar_etapa_sub', return_value=(True, '')) as mock_ap:
                        ok, msg = transicao_por_acao(
                            ce, user, PAPEL_OPERACIONAL, 'operacional_pago_tc', extras=extras
                        )
        self.assertTrue(ok)
        mock_ap.assert_called_once()
        args, kwargs = mock_ap.call_args
        self.assertEqual(args[2], SubStatusOperacional.PG_PAGO_TC_PARCIAL)
        self.assertEqual(kwargs.get('rm_payload'), extras['registermoney'])

    def test_registrar_comprovante_tc_repassa_rm_payload_no_primeiro_comprovante(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis.acoes_crm import _registrar_comprovante_tc_sem_rm

        ce = MagicMock()
        ce.pk = 1
        user = MagicMock()
        arquivo = MagicMock()
        comp_mock = MagicMock()
        comp_mock.id = 99
        rm_extra = {'valor_est': Decimal('100'), 'af': Decimal('1000')}
        atomic_cm = MagicMock()
        atomic_cm.__enter__ = MagicMock(return_value=None)
        atomic_cm.__exit__ = MagicMock(return_value=False)
        with patch('apps.contratos_v2.apis.acoes_crm.transaction.atomic', return_value=atomic_cm):
            with patch('apps.contratos_v2.apis.acoes_crm.ComprovanteTC.objects.create', return_value=comp_mock):
                with patch('apps.contratos_v2.apis.acoes_crm._soma_comprovantes', return_value=Decimal('50')):
                    with patch('apps.contratos_v2.apis.acoes_crm._valor_tc_do_contrato', return_value=Decimal('100')):
                        with patch('apps.contratos_v2.apis.acoes_crm.RegisterMoney_has_for_ce', return_value=False):
                            with patch('apps.contratos_v2.apis.acoes_crm.aplicar_etapa_sub', return_value=(True, '')) as mock_ap:
                                _registrar_comprovante_tc_sem_rm(
                                    ce, Decimal('50'), arquivo, user, rm_payload=rm_extra
                                )
        self.assertEqual(mock_ap.call_args.kwargs.get('rm_payload'), rm_extra)

    def test_registrar_comprovante_tc_sem_rm_payload_com_tc_levanta_erro(self):
        from decimal import Decimal
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.apis.acoes_crm import _registrar_comprovante_tc_sem_rm

        ce = MagicMock()
        ce.pk = 1
        user = MagicMock()
        arquivo = MagicMock()
        comp_mock = MagicMock()
        comp_mock.id = 99
        atomic_cm = MagicMock()
        atomic_cm.__enter__ = MagicMock(return_value=None)
        atomic_cm.__exit__ = MagicMock(return_value=False)
        with patch('apps.contratos_v2.apis.acoes_crm.transaction.atomic', return_value=atomic_cm):
            with patch('apps.contratos_v2.apis.acoes_crm.ComprovanteTC.objects.create', return_value=comp_mock):
                with patch('apps.contratos_v2.apis.acoes_crm._soma_comprovantes', return_value=Decimal('50')):
                    with patch('apps.contratos_v2.apis.acoes_crm._valor_tc_do_contrato', return_value=Decimal('100')):
                        with patch('apps.contratos_v2.apis.acoes_crm.RegisterMoney_has_for_ce', return_value=False):
                            with self.assertRaises(RuntimeError) as ctx:
                                _registrar_comprovante_tc_sem_rm(ce, Decimal('50'), arquivo, user)
        self.assertIn('registro financeiro', str(ctx.exception).lower())


class ContratoExibeBotaoEnviarVideoVendedorTest(SimpleTestCase):
    """Botão Enviar vídeo: link preenchido + vídeo pendente, sem travar por sub-status."""

    def _ce(self, **kwargs):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional

        defaults = dict(
            etapa_operacional=EtapaOperacional.FORMALIZACAO,
            sub_status_operacional=SubStatusOperacional.FORM_LINK_DISPONIVEL,
            link_formalizacao='https://exemplo.com/f',
            flag_video_enviado=False,
            video_cliente=None,
        )
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_link_sem_video_retorna_true(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor

        with patch('apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento', return_value=True):
            self.assertTrue(contrato_exibe_botao_enviar_video_vendedor(self._ce()))

    def test_flag_video_enviado_retorna_false(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor

        with patch('apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento', return_value=True):
            self.assertFalse(contrato_exibe_botao_enviar_video_vendedor(self._ce(flag_video_enviado=True)))

    def test_sem_link_retorna_false(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor

        with patch('apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento', return_value=True):
            self.assertFalse(contrato_exibe_botao_enviar_video_vendedor(self._ce(link_formalizacao='')))

    def test_cancelado_retorna_false(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional
        from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor

        with patch('apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento', return_value=True):
            self.assertFalse(
                contrato_exibe_botao_enviar_video_vendedor(
                    self._ce(etapa_operacional=EtapaOperacional.CANCELADO)
                )
            )

    def test_pagamento_com_link_sem_video_retorna_true(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor

        with patch('apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento', return_value=True):
            self.assertTrue(
                contrato_exibe_botao_enviar_video_vendedor(
                    self._ce(
                        etapa_operacional=EtapaOperacional.PAGAMENTO,
                        sub_status_operacional=SubStatusOperacional.PG_PAGO_CLIENTE,
                    )
                )
            )

    def test_limpa_nome_retorna_false(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_transicoes import contrato_exibe_botao_enviar_video_vendedor

        with patch('apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento', return_value=False):
            self.assertFalse(contrato_exibe_botao_enviar_video_vendedor(self._ce()))


class EnvioComprovantePagamentoVendedorRegrasTest(SimpleTestCase):
    """Regras de etapa e validação de arquivo para comprovante do vendedor."""

    def test_permite_envio_em_sub_status_pagamento(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import (
            EtapaOperacional,
            SubStatusOperacional,
            contrato_permite_envio_comprovante_pagamento_vendedor,
        )

        for sub in (
            SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
            SubStatusOperacional.PG_PAGO_CLIENTE,
            SubStatusOperacional.PG_PAGO_TC_PARCIAL,
        ):
            ce = SimpleNamespace(
                etapa_operacional=EtapaOperacional.PAGAMENTO,
                sub_status_operacional=sub,
            )
            self.assertTrue(contrato_permite_envio_comprovante_pagamento_vendedor(ce))

    def test_nao_permite_fora_de_pagamento(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import (
            EtapaOperacional,
            SubStatusOperacional,
            contrato_permite_envio_comprovante_pagamento_vendedor,
        )

        ce = SimpleNamespace(
            etapa_operacional=EtapaOperacional.ANUENCIA,
            sub_status_operacional=SubStatusOperacional.ANU_AGUARDANDO,
        )
        self.assertFalse(contrato_permite_envio_comprovante_pagamento_vendedor(ce))

    def test_validar_arquivo_rejeita_extensao(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import validar_arquivo_comprovante_vendedor

        f = SimpleNamespace(name='virus.exe', size=100)
        ok, msg = validar_arquivo_comprovante_vendedor(f)
        self.assertFalse(ok)
        self.assertIn('Formato', msg)

    def test_validar_arquivo_aceita_pdf(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import validar_arquivo_comprovante_vendedor

        f = SimpleNamespace(name='comp.pdf', size=1024)
        ok, msg = validar_arquivo_comprovante_vendedor(f)
        self.assertTrue(ok)
        self.assertEqual(msg, '')


class PortRefinCatalogoFlagsTest(SimpleTestCase):
    """Flags Port+Refin no catálogo de produtos."""

    def test_flags_mutuamente_exclusivas(self):
        from apps.contratos_v2.apis.config_catalogos import _validar_flags_produto_mutuas

        self.assertIsNotNone(_validar_flags_produto_mutuas(True, True))
        self.assertIsNone(_validar_flags_produto_mutuas(True, False))
        self.assertIsNone(_validar_flags_produto_mutuas(False, True))


class PortRefinTransicaoPagoClienteTest(SimpleTestCase):
    """Regras de operacional_pago_cliente com Port + Refin."""

    def _ce_pagamento_aguardando(self):
        from types import SimpleNamespace

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional

        prod = SimpleNamespace(flag_port_mais_refin=True, titulo='PORT TEST')
        d_op = SimpleNamespace(produto=prod)
        return SimpleNamespace(
            pk=1,
            status=True,
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional=SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
            flag_video_enviado=True,
            dados_operacionais=d_op,
            proposta_dados=None,
        )

    def test_exige_payload_refin_port(self):
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_transicoes import transicao_por_acao

        ce = self._ce_pagamento_aguardando()
        user = SimpleNamespace(is_authenticated=True, pk=1)
        with patch(
            'apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento',
            return_value=False,
        ):
            with patch(
                'apps.contratos_v2.services.port_refin.produto_exige_refin_no_pago_cliente',
                return_value=True,
            ):
                with patch(
                    'apps.contratos_v2.services.port_refin.contrato_port_ja_tem_refin',
                    return_value=False,
                ):
                    with patch(
                        'apps.contratos_v2.services.port_refin.contrato_exige_valor_saldo_pago_cliente',
                        return_value=False,
                    ):
                        ok, msg = transicao_por_acao(
                            ce, user, 'operacional', 'operacional_pago_cliente', extras=None
                        )
        self.assertFalse(ok)
        self.assertIn('REFIN', msg)

    def test_pago_tc_refin_nao_altera_port(self):
        """Pago TC no REFIN não deve sincronizar sub-status do PORT (decisão de produto)."""
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import transicao_por_acao

        port_sub_antes = SubStatusOperacional.PG_PAGO_CLIENTE
        ce_port = self._ce_pagamento_aguardando()
        ce_port.sub_status_operacional = port_sub_antes
        ce_refin = self._ce_pagamento_aguardando()
        ce_refin.pk = 2
        ce_refin.sub_status_operacional = SubStatusOperacional.PG_PAGO_CLIENTE
        ce_refin.contrato_vinculo_port_id = 1

        rm_qs = MagicMock()
        rm_qs.exists.return_value = False

        with patch(
            'apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento',
            return_value=False,
        ):
            with patch(
                'apps.contratos_v2.fluxo_transicoes._valor_tc_contrato',
                return_value=0,
            ):
                with patch(
                    'apps.contratos_v2.fluxo_transicoes.RegisterMoney.objects.filter',
                    return_value=rm_qs,
                ):
                    with patch(
                        'apps.contratos_v2.fluxo_transicoes.aplicar_etapa_sub',
                        return_value=(True, ''),
                    ) as mock_aplicar:
                        ok, _ = transicao_por_acao(
                            ce_refin,
                            SimpleNamespace(pk=1),
                            'operacional',
                            'operacional_pago_tc',
                        )
        self.assertTrue(ok)
        mock_aplicar.assert_called_once()
        self.assertEqual(ce_port.sub_status_operacional, port_sub_antes)


class ValorSaldoPortTest(SimpleTestCase):
    """Valor Saldo obrigatório no Pago Cliente (produto PORT)."""

    def test_titulo_produto_indica_port(self):
        from apps.contratos_v2.services.port_refin import titulo_produto_indica_port

        self.assertTrue(titulo_produto_indica_port('PORTABILIDADE'))
        self.assertFalse(titulo_produto_indica_port('NOVO EMPRESTIMO'))

    def test_contrato_exige_valor_saldo(self):
        from types import SimpleNamespace

        from apps.contratos_v2.services.port_refin import contrato_exige_valor_saldo_pago_cliente

        prod_port = SimpleNamespace(titulo='PORT TEST', flag_refin_da_port=False)
        ce_port = SimpleNamespace(
            dados_operacionais=SimpleNamespace(produto=prod_port),
            proposta_dados=None,
        )
        self.assertTrue(contrato_exige_valor_saldo_pago_cliente(ce_port))

        prod_refin = SimpleNamespace(titulo='REFIN PORT', flag_refin_da_port=True)
        ce_refin = SimpleNamespace(
            dados_operacionais=SimpleNamespace(produto=prod_refin),
            proposta_dados=None,
        )
        self.assertFalse(contrato_exige_valor_saldo_pago_cliente(ce_refin))

    def test_pago_cliente_sem_valor_saldo_bloqueia(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.fluxo_transicoes import transicao_por_acao

        prod = SimpleNamespace(flag_port_mais_refin=False, titulo='PORT TEST', flag_refin_da_port=False)
        ce = SimpleNamespace(
            pk=10,
            status=True,
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional=SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
            flag_video_enviado=True,
            dados_operacionais=SimpleNamespace(produto=prod),
            proposta_dados=None,
        )
        user = SimpleNamespace(is_authenticated=True, pk=1)
        with patch(
            'apps.contratos_v2.fluxo_transicoes.contrato_exige_video_conscientizacao_para_pagamento',
            return_value=False,
        ):
            with patch(
                'apps.contratos_v2.services.port_refin.produto_exige_refin_no_pago_cliente',
                return_value=False,
            ):
                ok, msg = transicao_por_acao(
                    ce, user, 'operacional', 'operacional_pago_cliente', extras=None
                )
        self.assertFalse(ok)
        self.assertIn('Valor Saldo', msg)

    def test_validar_valor_saldo_parse_pt_br(self):
        from decimal import Decimal
        from types import SimpleNamespace
        from unittest.mock import patch

        from apps.contratos_v2.services.port_refin import validar_valor_saldo_obrigatorio

        ce = SimpleNamespace(dados_operacionais=None, proposta_dados=None)
        with patch(
            'apps.contratos_v2.services.port_refin.contrato_exige_valor_saldo_pago_cliente',
            return_value=True,
        ):
            v = validar_valor_saldo_obrigatorio({'valor_saldo': '1.500,75'}, ce)
        self.assertEqual(v, Decimal('1500.75'))

    def test_criar_refin_recebe_valor_saldo(self):
        from decimal import Decimal
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch

        from apps.contratos_v2.fluxo_constants import EtapaOperacional, SubStatusOperacional
        from apps.contratos_v2.services.port_refin import criar_refin_apos_pago_cliente

        # SimpleTestCase não permite DB; bypass do @transaction.atomic
        criar_refin_fn = getattr(criar_refin_apos_pago_cliente, '__wrapped__', criar_refin_apos_pago_cliente)

        ce_port = SimpleNamespace(
            pk=1,
            id=1,
            status=True,
            codigo='P1',
            etapa_operacional=EtapaOperacional.PAGAMENTO,
            sub_status_operacional=SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
            flag_video_enviado=True,
            cliente_dados_pessoais_id=1,
            proposta_dados_id=5,
            proposta_dados=SimpleNamespace(id=5),
            solicitacao_digitacao=SimpleNamespace(carteira_clientes_id=1, carteira_clientes=SimpleNamespace(id=1)),
        )
        refin_port = {
            'numero_contrato': 'REFIN001',
            'tabela_cms_id': 2,
            'proposta': {},
        }
        saldo = Decimal('2500.00')
        with patch('apps.contratos_v2.services.port_refin.produto_exige_refin_no_pago_cliente', return_value=True):
            with patch('apps.contratos_v2.services.port_refin.contrato_port_ja_tem_refin', return_value=False):
                with patch('apps.contratos_v2.services.port_refin._validar_refin_port_payload', return_value=('REFIN001', MagicMock(), MagicMock(), {})):
                    with patch('apps.contratos_v2.services.port_refin.aplicar_etapa_sub', return_value=(True, '')):
                        with patch('apps.contratos_v2.services.port_refin.persistir_valor_saldo_contrato') as mock_persist:
                            with patch('apps.contratos_v2.services.port_refin.PropostaDados.objects.create') as mock_pd_create:
                                with patch('apps.contratos_v2.services.port_refin.adicionar_proposta_operacional_na_carteira'):
                                    with patch('apps.contratos_v2.services.port_refin.SolicitacaoDigitacao.objects.create', return_value=SimpleNamespace(id=9)):
                                        with patch('apps.contratos_v2.services.port_refin.HistoricoEventoDigitacao.objects.create'):
                                            with patch('apps.contratos_v2.services.port_refin.ContratoExecucao.objects.create', return_value=SimpleNamespace(id=2, codigo='REFIN001')):
                                                with patch('apps.contratos_v2.services.port_refin.ContratoDadosOperacionais.objects.create'):
                                                    with patch('apps.contratos_v2.services.port_refin.sincronizar_fase_legada'):
                                                        with patch('apps.contratos_v2.services.port_refin.HistoricoTransicaoContrato.objects.create'):
                                                            with patch('apps.contratos_v2.services.port_refin._clonar_contratos_portados'):
                                                                criar_refin_fn(
                                                                    ce_port,
                                                                    refin_port,
                                                                    SimpleNamespace(pk=1),
                                                                    valor_saldo=saldo,
                                                                )
        mock_persist.assert_called_once_with(ce_port, saldo)
        self.assertEqual(mock_pd_create.call_args.kwargs.get('valor_saldo'), saldo)


class PortRefinValidacaoPayloadTest(SimpleTestCase):
    """Validação do payload do modal REFIN."""

    def test_numero_contrato_invalido(self):
        from types import SimpleNamespace

        from apps.contratos_v2.services.port_refin import _validar_refin_port_payload

        ce = SimpleNamespace(proposta_dados=SimpleNamespace(banco_id=1, convenio_id=1))
        with self.assertRaises(ValueError) as ctx:
            _validar_refin_port_payload(
                ce,
                {'numero_contrato': 'inválido espaço', 'tabela_cms_id': 1, 'proposta': {}},
            )
        self.assertIn('inválido', str(ctx.exception).lower())
