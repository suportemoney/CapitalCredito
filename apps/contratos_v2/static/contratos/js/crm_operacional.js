/* ==============================================
   CRM OPERACIONAL — JS (tabela unificada)
   Template: contratos/v2/crm_operacional.html
   ============================================== */
(function () {
    'use strict';

    const base = '/contratos/api/v2/';
    /** Limite de tamanho do vídeo (igual a apps/contratos_v2/video_audit.py) */
    const VIDEO_UPLOAD_MAX_BYTES = 35 * 1024 * 1024;
    const MSG_VIDEO_TAMANHO = 'O vídeo excede o tamanho máximo permitido (35 MB). Envie um arquivo menor.';
    const isSuperuser = (document.getElementById('crm-container') || {}).dataset &&
        document.getElementById('crm-container').dataset.superuser === 'true';

    // Cache dos itens carregados (para filtro/busca no frontend)
    let _todosItens = [];
    let _crmPage = 1;
    let _catalogosCarregados = false;

    // Transições disponíveis em cache por registro aberto
    let _transicoes = [];
    let _modoLivreEvoluir = false;
    // Defaults do modal Pago TC (API transicoes-disponiveis → pago_tc_modal)
    let _pagoTcModal = null;
    // Snapshot percentuais CMS para Pago CMS (API → pago_cms_modal)
    let _pagoCmsModal = null;
    let _refinPortDefaults = null;
    let _evoluirPendenteRefinPort = null;
    let _evoluirPendenteSaldoPort = null;
    let _valorSaldoPendente = null;

    /** True quando falta vídeo e o produto exige envio antes de Pago Cliente / Pago TC (Limpa Nome dispensa). */
    function _pagoTcModalBloqueiaPorVideo(modal) {
        const m = modal || {};
        if (m.exige_video_conscientizacao === false) {
            return false;
        }
        return m.flag_video_enviado === false;
    }

    /** Soma de comprovantes TC já registrados e valor TC (API); preview do badge não re-lê texto formatado. */
    let _tcCompSomaServidor = 0;
    let _tcCompValorTc = 0;

    /* ── CSRF + sessão (Django: sem Bearer; cookie sessionid + header CSRF) ── */
    function csrf() {
        const inp = document.querySelector('[name=csrfmiddlewaretoken]');
        if (inp && inp.value) return inp.value;
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    /** Parse JSON da resposta; se vier HTML (403 CSRF, login, 500), devolve { ok: false, erro }. */
    function _jsonFromFetchResponse(r, text) {
        let j = null;
        try {
            j = text ? JSON.parse(text) : null;
        } catch (e) {
            j = {
                ok: false,
                erro:
                    r.status === 403
                        ? 'Sessão ou CSRF inválido. Recarregue a página e tente de novo.'
                        : 'Resposta inválida do servidor (HTTP ' + r.status + ').',
            };
        }
        if (!r.ok) {
            if (!j || typeof j !== 'object') {
                j = { ok: false, erro: 'HTTP ' + r.status };
            } else if (j.ok !== false) {
                j = { ok: false, erro: j.erro || j.detail || ('HTTP ' + r.status) };
            }
        }
        return j;
    }

    /* ── Fetch helpers (sempre same-origin = envia cookies de sessão + CSRF) ── */
    function getJson(url) {
        return fetch(url, { credentials: 'same-origin', headers: { 'X-CSRFToken': csrf() } }).then(function (r) {
            return r.text().then(function (text) { return _jsonFromFetchResponse(r, text); });
        });
    }
    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
            body: JSON.stringify(body || {}),
        }).then(function (r) {
            return r.text().then(function (text) { return _jsonFromFetchResponse(r, text); });
        });
    }

    function postMultipart(url, formData) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': csrf() },
            body: formData,
        }).then(function (r) {
            return r.text().then(function (text) { return _jsonFromFetchResponse(r, text); });
        });
    }

    /* Evita aviso aria-hidden: foco preso em botão ao fechar modal empilhado */
    function blurFocoAtivo() {
        try {
            const a = document.activeElement;
            if (a && a !== document.body && typeof a.blur === 'function') {
                a.blur();
            }
        } catch (e) { /* noop */ }
    }

    let _crmArquivosContratoId = null;
    let _crmArquivosTipo = null;
    let _crmArquivosPendente = null;
    /** Callback pendente após gerar contrato no modal obrigatório */
    let _crmAcaoPendentePosContrato = null;

    function crmBuscarItem(tipo, id) {
        return (_todosItens || []).find(function (it) {
            return String(it.tipo) === String(tipo) && String(it.id) === String(id);
        }) || null;
    }

    function crmDeveForcarGeracaoContrato(it) {
        if (!it || it.tipo !== 'solicitacao_dig') return false;
        if (it.requer_geracao_contrato === true) return true;
        if (it.requer_geracao_contrato === false) return false;
        if (it.etapa === 'CANCELADO') return false;
        if (it.tem_pendencia || it.etapa === 'PENDENCIAS' || it.sub_status === 'PENDENTE_CORRECAO') return false;
        if (it.etapa === 'DIGITACAO' && it.sub_status === 'PENDENTE_OPERACIONAL') return false;
        return true;
    }

    function crmExecutarAcaoProposta(tipo, id, callback) {
        const it = crmBuscarItem(tipo, id);
        if (crmDeveForcarGeracaoContrato(it)) {
            _crmAcaoPendentePosContrato = { fn: callback, tipoOriginal: tipo, idOriginal: id };
            abrirModalGerarContratoObrigatorio(it);
            return;
        }
        if (typeof callback === 'function') callback();
    }

    function _carregarTabelasCmsSolicitacao(solId, selEl) {
        if (!selEl) return;
        selEl.innerHTML = '<option value="">Carregando...</option>';
        selEl.disabled = true;
        getJson(base + 'tabelas-cms/?solicitacao_digitacao_id=' + encodeURIComponent(solId)).then(function (d) {
            selEl.disabled = false;
            if (!d.ok || !d.tabelas || !d.tabelas.length) {
                selEl.innerHTML = '<option value="">Nenhuma tabela disponível para este banco/produto</option>';
                return;
            }
            selEl.innerHTML = '<option value="">Selecione a tabela CMS...</option>';
            const _labelClassif = { M1: 'M1 - 100%', M2: 'M2 - 50%', M3: 'M3 - 0%' };
            d.tabelas.forEach(function (t) {
                const opt = document.createElement('option');
                opt.value = t.id;
                const cls = (t.classificador_banco || '').toString().toUpperCase();
                const sufixo = _labelClassif[cls] ? ' [' + _labelClassif[cls] + ']' : '';
                opt.textContent = t.titulo + sufixo;
                selEl.appendChild(opt);
            });
            const idProposta = d.tabela_cms_id_proposta != null ? String(d.tabela_cms_id_proposta) : '';
            if (idProposta) {
                const jaExiste = Array.from(selEl.options).some(function (o) {
                    return String(o.value) === idProposta;
                });
                if (!jaExiste) {
                    const extra = document.createElement('option');
                    extra.value = idProposta;
                    extra.textContent = d.tabela_cms_titulo_proposta || 'Tabela da proposta';
                    selEl.appendChild(extra);
                }
                selEl.value = idProposta;
            }
        }).catch(function () {
            selEl.disabled = false;
            selEl.innerHTML = '<option value="">Erro ao carregar tabelas</option>';
        });
    }

    function abrirModalGerarContratoObrigatorio(item) {
        if (!item) return;
        document.getElementById('gerarContratoSolId').value = String(item.id);
        document.getElementById('gerarContratoProposta').textContent = item.proposta_codigo || '—';
        document.getElementById('gerarContratoCliente').textContent = item.nome_cliente || '—';
        document.getElementById('gerarContratoBanco').textContent = item.banco || '—';
        document.getElementById('gerarContratoConvenio').textContent = item.convenio || '—';
        document.getElementById('gerarContratoProduto').textContent = item.produto || '—';
        const inpNum = document.getElementById('gerarContratoNum');
        if (inpNum) inpNum.value = item.numero_contrato_banco_pre || '';
        const sel = document.getElementById('gerarContratoTabelaCms');
        _carregarTabelasCmsSolicitacao(item.id, sel);
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalGerarContratoObrigatorio')).show();
    }

    function confirmarGerarContratoObrigatorio() {
        const solId = parseInt(document.getElementById('gerarContratoSolId').value, 10);
        const numContrato = String((document.getElementById('gerarContratoNum') || {}).value || '').trim().toUpperCase();
        const tabelaCmsId = (document.getElementById('gerarContratoTabelaCms') || {}).value;
        const btn = document.getElementById('btnConfirmarGerarContrato');
        if (!solId) {
            showToast('Solicitação inválida.', 'warning');
            return;
        }
        if (!numContrato) {
            showToast('Informe o Nº Contrato.', 'warning');
            return;
        }
        if (!/^[A-Z0-9\-\.\/]{1,30}$/.test(numContrato)) {
            showToast('Nº Contrato inválido. Use apenas letras, números e -./ (até 30 caracteres).', 'warning');
            return;
        }
        if (!tabelaCmsId) {
            showToast('Selecione uma tabela CMS.', 'warning');
            return;
        }
        if (btn) btn.disabled = true;
        postJson(base + 'evoluir/', {
            tipo: 'solicitacao_dig',
            id: solId,
            acao: 'gerar_contrato',
            contrato_codigo: numContrato,
            tabela_cms_id: parseInt(tabelaCmsId, 10),
        }).then(function (r) {
            if (btn) btn.disabled = false;
            if (!r || !r.ok) {
                showToast((r && r.erro) || 'Erro ao gerar contrato.', 'danger');
                return;
            }
            showToast('Contrato ' + (r.codigo || '') + ' gerado com sucesso.', 'success');
            blurFocoAtivo();
            bootstrap.Modal.getInstance(document.getElementById('modalGerarContratoObrigatorio')).hide();
            const contratoId = r.contrato_id;
            const pendente = _crmAcaoPendentePosContrato;
            _crmAcaoPendentePosContrato = null;
            loadTabelaUnificada().finally(function () {
                if (pendente && typeof pendente.fn === 'function' && contratoId) {
                    pendente.fn('contrato', contratoId);
                }
            });
        }).catch(function () {
            if (btn) btn.disabled = false;
            showToast('Erro de comunicação.', 'danger');
        });
    }

    function crmMostrarBotaoArquivos(it) {
        // Mostra para contratos (exceto DIG_AGUARDANDO antes do upload do vídeo)
        // e tambem para SolicitacaoDigitacao, p/ que o operacional veja o PDF da
        // proposta e os arquivos do cliente enviados pelo vendedor.
        if (it.tipo === 'solicitacao_dig') return true;
        return it.tipo === 'contrato' && !(it.etapa === 'DIGITACAO' && it.sub_status === 'DIG_AGUARDANDO');
    }

    function crmPreencherModalArquivos(d) {
        const ehSol = d.tipo === 'solicitacao_dig';
        const tituloBase = ehSol
            ? 'Solicitação ' + esc(String(d.solicitacao_id || ''))
            : 'Contrato ' + esc(d.contrato_codigo || String(d.contrato_id || ''));
        document.getElementById('crmArqTitulo').innerHTML =
            '<i class="bx bx-folder me-2"></i>' + tituloBase;
        document.getElementById('crmArqSubtitulo').textContent = d.nome_cliente || '';

        // PDF da proposta (enviado pelo vendedor) — bloco opcional renderizado no
        // mesmo container do vídeo. Para solicitacao_dig ocultamos o vídeo.
        const vb = document.getElementById('crmArqVideoBloco');
        const partes = [];
        if (d.pdf_proposta && d.pdf_proposta.url) {
            const meta = [];
            if (d.pdf_proposta.enviado_por) meta.push('por ' + esc(d.pdf_proposta.enviado_por));
            if (d.pdf_proposta.data_criacao) meta.push(esc(d.pdf_proposta.data_criacao));
            partes.push(
                '<div class="mb-2">' +
                '<strong class="d-block small text-muted mb-1">PDF da proposta (vendedor)</strong>' +
                '<a href="' + String(d.pdf_proposta.url).replace(/"/g, '&quot;') +
                '" target="_blank" rel="noopener">' +
                esc(d.pdf_proposta.name || 'proposta.pdf') + '</a>' +
                (meta.length ? ' <span class="text-muted small">(' + meta.join(' — ') + ')</span>' : '') +
                '</div>'
            );
        }
        if (!ehSol) {
            if (d.video && d.video.url) {
                partes.push(
                    '<div><strong class="d-block small text-muted mb-1">Vídeo de conscientização</strong>' +
                    '<a href="' + String(d.video.url).replace(/"/g, '&quot;') +
                    '" target="_blank" rel="noopener">' + esc(d.video.name) + '</a>' +
                    (d.video.size ? ' <span class="text-muted">(' + esc(String(d.video.size)) + ' bytes)</span>' : '') +
                    (d.video.flag_video_enviado ? ' <span class="badge bg-success">Enviado</span>' : '') +
                    '</div>'
                );
            } else {
                partes.push('<div><span class="text-warning">Nenhum vídeo enviado.</span></div>');
            }
        }
        if (!partes.length) {
            partes.push('<div><span class="text-muted">Sem PDF da proposta.</span></div>');
        }
        vb.innerHTML = partes.join('');
        const ul = document.getElementById('crmArqListaArquivos');
        const sem = document.getElementById('crmArqSemArquivos');
        ul.innerHTML = '';
        const lista = d.arquivos || [];
        if (!lista.length) {
            sem.classList.remove('d-none');
        } else {
            sem.classList.add('d-none');
            lista.forEach(function (a) {
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center px-0';
                const href = String(a.url || '').replace(/"/g, '&quot;');
                li.innerHTML =
                    '<span>' +
                    esc(a.titulo) +
                    ' <span class="text-muted">' +
                    esc(a.data_criacao || '') +
                    '</span></span>' +
                    '<a class="btn btn-sm btn-outline-primary" href="' +
                    href +
                    '" target="_blank" rel="noopener">Abrir</a>';
                ul.appendChild(li);
            });
        }
        const ro = !!d.somente_leitura;
        const btnVid = document.getElementById('crmArqBtnVideo');
        const btnArq = document.getElementById('crmArqBtnArquivo');
        if (btnVid) btnVid.classList.toggle('d-none', ro || ehSol);
        if (btnArq) btnArq.classList.toggle('d-none', ro);
        const al = document.getElementById('crmArqAlertaLeitura');
        if (al) al.classList.toggle('d-none', !ro);
        const bannerPre = document.getElementById('crmArqBannerPreContrato');
        if (bannerPre) {
            const itArq = _crmArquivosTipo === 'solicitacao_dig'
                ? crmBuscarItem('solicitacao_dig', _crmArquivosContratoId)
                : null;
            const mostrarBanner = !!(
                itArq
                && itArq.etapa === 'DIGITACAO'
                && itArq.sub_status === 'PENDENTE_OPERACIONAL'
            );
            bannerPre.classList.toggle('d-none', !mostrarBanner);
        }
    }

    function abrirModalArquivosContrato(tipo, id) {
        // Compatibilidade retroativa: chamadas antigas passavam apenas o ID
        // (para contrato). Se o 1º arg não for string de tipo, assume 'contrato'.
        if (id === undefined && (tipo !== undefined && tipo !== null)) {
            id = tipo;
            tipo = 'contrato';
        }
        tipo = tipo === 'solicitacao_dig' ? 'solicitacao_dig' : 'contrato';
        _crmArquivosContratoId = id;
        _crmArquivosTipo = tipo;
        document.getElementById('crmArqVideoBloco').innerHTML =
            '<span class="spinner-border spinner-border-sm" role="status"></span> Carregando...';
        document.getElementById('crmArqListaArquivos').innerHTML = '';
        document.getElementById('crmArqSemArquivos').classList.add('d-none');
        const al0 = document.getElementById('crmArqAlertaLeitura');
        if (al0) al0.classList.add('d-none');
        const bannerPre0 = document.getElementById('crmArqBannerPreContrato');
        if (bannerPre0) bannerPre0.classList.add('d-none');
        ['crmArqBtnVideo', 'crmArqBtnArquivo'].forEach(function (bid) {
            const b = document.getElementById(bid);
            if (b) b.classList.remove('d-none');
        });
        const btnVidInit = document.getElementById('crmArqBtnVideo');
        if (btnVidInit && tipo === 'solicitacao_dig') btnVidInit.classList.add('d-none');
        const url = tipo === 'solicitacao_dig'
            ? base + 'solicitacao-dig/' + encodeURIComponent(id) + '/midia-arquivos/'
            : base + 'contrato/' + encodeURIComponent(id) + '/midia-arquivos/';
        getJson(url).then(function (d) {
            if (!d.ok) {
                showToast(d.erro || 'Erro ao carregar.', 'danger');
                return;
            }
            crmPreencherModalArquivos(d);
            bootstrap.Modal.getOrCreateInstance(document.getElementById('modalArquivosContrato')).show();
        }).catch(function () {
            showToast('Erro ao carregar arquivos.', 'danger');
        });
    }

    /* ── Toast ── */
    function showToast(msg, type) {
        const el = document.getElementById('toastMsg');
        const colors = { success: '#198754', danger: '#dc3545', warning: '#856404', info: '#0a9dc7' };
        el.style.background = colors[type] || colors.info;
        document.getElementById('toastBody').textContent = msg;
        bootstrap.Toast.getOrCreateInstance(el, { delay: 3500 }).show();
    }

    /* ── escapeHtml ── */
    function esc(s) {
        if (!s && s !== 0) return '—';
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    }

    function on(el, ev, fn) {
        if (el && typeof el.addEventListener === 'function') {
            el.addEventListener(ev, fn);
        }
    }

    /* ── Badge de sub-status ── */
    /* Labels alinhados com SubStatusOperacional.CHOICES em fluxo_constants.py */
    const STATUS_MAP = {
        'ENVIADA':                  ['sb-aguardando',  'Aguardando'],
        'EM_ANALISE_OPERACIONAL':   ['sb-aguardando',  'Em análise'],
        'RESULTADO_PROPOSTAS':      ['sb-retornado',   'Propostas retornadas'],
        'RESULTADO_INELEGIVEL':     ['sb-inelegivel',  'Inelegível'],
        'DIG_AGUARDANDO':           ['sb-aguardando',  'Aguardando operacional'],
        'DIG_DIGITADO':             ['sb-digitado',    'Digitado'],
        // Sub-status legados da Digitação — mantidos APENAS para renderizar
        // contratos antigos na grid/timeline (não entram nos chips novos).
        'DIG_LINK_DISPONIBILIZADO': ['sb-link',        'Link disponibilizado (legado)'],
        'DIG_CHECADO':              ['sb-digitado',    'Checado (legado)'],
        'DIG_FORMALIZADO':          ['sb-formalizado', 'Formalizado (legado)'],
        // Formalização (nova etapa): FORM_CHECADO aparece no badge/timeline,
        // mas intencionalmente NÃO é chip filtrável na esteira.
        'FORM_LINK_DISPONIVEL':     ['sb-link',        'Link disponível'],
        'FORM_CHECADO':             ['sb-digitado',    'Checado'],
        'FORM_FORMALIZADO':         ['sb-formalizado', 'Formalizado'],
        'ANL_AGUARDANDO':           ['sb-aguardando',  'Aguardando análise'],
        'ANL_SUCESSO':              ['sb-sucesso',     'Análise aprovada'],
        'CIP_AGUARDANDO':           ['sb-aguardando',  'Aguardando CIP'],
        'CIP_SUCESSO':              ['sb-retornado',   'CIP aprovado'],
        'REFIN_AGUARDANDO':         ['sb-aguardando',  'Aguardando REFIN'],
        'REFIN_SUCESSO':            ['sb-sucesso',     'REFIN aprovado'],
        'ANU_AGUARDANDO':           ['sb-aguardando',  'Aguardando anuência'],
        'ANU_AVERBADO':             ['sb-averbado',    'Averbado'],
        'PG_AGUARDANDO_CLIENTE':    ['sb-aguardando',  'Aguardando Pagamento Cliente'],
        'PG_PAGO_CLIENTE':          ['sb-pago',        'Pago Cliente'],
        'PG_AGUARDANDO_TC':         ['sb-aguardando',  'Aguardando Verificação de Valores'],
        'PG_PAGO_TC':               ['sb-pago',        'Pago TC'],
        'PG_PAGO_TC_PARCIAL':       ['sb-pago',        'Pago TC Parcial'],
        'PG_PAGO_TC_TOTAL':         ['sb-pago',        'Pago TC Total'],
        'PG_AGUARDANDO_CMS':        ['sb-aguardando',  'Aguardando pagamento CMS'],
        'PG_PAGO_CMS':              ['sb-pago',        'Pago CMS'],
        'PG_PAGO_CMS_EMPRESA':      ['sb-pago',        'Pago CMS Empresa'],
        'PEND_AGUARDANDO':          ['sb-pendente',    'Pendência em aberto'],
        'PEND_CORRIGIDO':           ['sb-sucesso',     'Pendência corrigida'],
        'CAN_ENCERRADO':            ['sb-cancelado',   'Encerrado'],
        'CAN_CLIENTE':              ['sb-cancelado',   'Cancelado pelo cliente'],
        'CAN_CORRETOR':             ['sb-cancelado',   'Cancelado pelo corretor'],
        'CAN_BANCO':                ['sb-cancelado',   'Cancelado pelo banco'],
        'CAN_REEMBOLSO':            ['sb-cancelado',   'Estorno'],
        'DIG_AGUARDANDO_GERACAO':   ['sb-aguardando',  'Aguardando geração'],
        /* Estados da solicitação de digitação (pré-contrato) — fluxo_constants.EstadoSolicitacaoDigitacao */
        'PENDENTE_OPERACIONAL':     ['sb-aguardando',  'Pendente operacional'],
        'EM_DIGITACAO':             ['sb-digitado',    'Em digitação'],
        'PENDENTE_CORRECAO':        ['sb-pendente',    'Pendente correção (vendedor)'],
        'CANCELADA':                ['sb-cancelado',   'Cancelada (sem contrato)'],
        'CONTRATO_GERADO':          ['sb-sucesso',     'Contrato gerado'],
    };
    function sbadge(sub) {
        const m = STATUS_MAP[sub];
        if (!m) return '<span class="crm-pill-status sbadge sb-default">' + esc(sub) + '</span>';
        return '<span class="crm-pill-status sbadge ' + m[0] + '">' + m[1] + '</span>';
    }

    /* ── Badge de etapa ── */
    const ETAPA_COLORS = {
        'SIMULACAO':    'var(--sim)',
        'DIGITACAO':    'var(--dig)',
        // Formalização reutiliza a cor da Digitação para manter a continuidade visual.
        'FORMALIZACAO': 'var(--dig)',
        'ANALISE':      'var(--anal)',
        'CIP':          'var(--cip)',
        'REFIN':        'var(--refin)',
        'ANUENCIA':     'var(--anu)',
        'PAGAMENTO':    'var(--pag)',
        'PENDENCIAS':   'var(--pend)',
        'CANCELADO':    '#842029',
        /* Pré-contrato (solicitacao_dig) — códigos sintéticos da API */
        'PRE_SOL_GERAR':     'var(--dig)',
        'PRE_SOL_PENDENCIA': 'var(--pend)',
        'PRE_SOL_CANCELAR':  '#842029',
        'PRE_SOL_REABRIR':   'var(--dig)',
    };

    /* Nome nominal da fase (usado quando o sub-status já avançou além do estado inicial) */
    const ETAPA_NOMINAL = {
        'SIMULACAO':    'Simulação',
        'DIGITACAO':    'Digitação',
        'FORMALIZACAO': 'Formalização',
        'ANALISE':      'Análise',
        'CIP':          'CIP',
        'REFIN':        'REFIN',
        'ANUENCIA':     'Anuência',
        'PAGAMENTO':    'Pagamento',
        'PENDENCIAS':   'Pendências',
        'CANCELADO':    'Cancelado',
        'PRE_SOL_GERAR':     'Pré-contrato',
        'PRE_SOL_PENDENCIA': 'Pré-contrato',
        'PRE_SOL_CANCELAR':  'Pré-contrato',
        'PRE_SOL_REABRIR':   'Pré-contrato',
    };

    /*
     * Sub-statuses que representam o estado INICIAL de cada etapa.
     * Apenas nesses casos o label de presente contínuo ("Digitando", "Analisando" …)
     * é exibido — nos demais, o badge mostra o nome nominal da fase.
     */
    const ETAPA_INITIAL_SUB = {
        'SIMULACAO':    ['ENVIADA', 'EM_ANALISE_OPERACIONAL'],
        'DIGITACAO':    ['DIG_AGUARDANDO', 'PENDENTE_OPERACIONAL', 'EM_DIGITACAO'],
        'FORMALIZACAO': ['FORM_LINK_DISPONIVEL'],
        'ANALISE':      ['ANL_AGUARDANDO'],
        'CIP':          ['CIP_AGUARDANDO'],
        'REFIN':        ['REFIN_AGUARDANDO'],
        'ANUENCIA':     ['ANU_AGUARDANDO'],
        'PAGAMENTO':    ['PG_AGUARDANDO_CLIENTE'],
        'PENDENCIAS':   ['PEND_AGUARDANDO', 'PENDENTE_CORRECAO'],
        'CANCELADO':    [],
    };

    function etapaBadge(etapa, label, sub) {
        const color = ETAPA_COLORS[etapa] || '#6c757d';
        const initials = ETAPA_INITIAL_SUB[etapa] || [];
        /* usa presente contínuo (label da API) só no estado inicial; fora disso, nome nominal */
        const isInitial = !sub || initials.includes(sub);
        const displayLabel = isInitial ? (label || etapa) : (ETAPA_NOMINAL[etapa] || label || etapa);
        return '<span class="crm-pill-etapa" style="background:' + color + ';color:#fff;">' + esc(displayLabel) + '</span>';
    }

    /* ── Mapa de sub-statuses por etapa (para os sub-chips de filtro) ── */
    const ETAPA_SUBSTATUS = {
        'SIMULACAO':  [
            { code: 'ENVIADA',                label: 'Aguardando' },
            { code: 'EM_ANALISE_OPERACIONAL', label: 'Em análise' },
            { code: 'RESULTADO_PROPOSTAS',    label: 'Propostas retornadas' },
            { code: 'RESULTADO_INELEGIVEL',   label: 'Inelegível' },
        ],
        // Digitação (fluxo novo): apenas Aguardando e Digitado.
        // Os sub-status legados (DIG_LINK_DISPONIBILIZADO/CHECADO/FORMALIZADO)
        // continuam válidos em banco e aparecem na grid/timeline via STATUS_MAP,
        // mas NÃO são chips filtráveis.
        'DIGITACAO':    [
            { code: 'DIG_AGUARDANDO', label: 'Aguardando' },
            { code: 'DIG_DIGITADO',   label: 'Digitado' },
            { code: 'PENDENTE_OPERACIONAL', label: 'Pendente operacional' },
            { code: 'EM_DIGITACAO',   label: 'Em digitação' },
        ],
        // Formalização: chip "Checado" intencionalmente OMITIDO da esteira
        // (critério 4 da validação [5] — continua registrado no histórico
        // e renderizado como badge inline via STATUS_MAP).
        'FORMALIZACAO': [
            { code: 'FORM_LINK_DISPONIVEL', label: 'Link disponível' },
            { code: 'FORM_FORMALIZADO',     label: 'Formalizado' },
        ],
        'ANALISE':    [
            { code: 'ANL_AGUARDANDO', label: 'Aguardando análise' },
            { code: 'ANL_SUCESSO',    label: 'Análise aprovada' },
        ],
        'CIP':        [
            { code: 'CIP_AGUARDANDO', label: 'Aguardando CIP' },
            { code: 'CIP_SUCESSO',    label: 'CIP aprovado' },
        ],
        'REFIN':      [
            { code: 'REFIN_AGUARDANDO', label: 'Aguardando REFIN' },
            { code: 'REFIN_SUCESSO',    label: 'REFIN aprovado' },
        ],
        'ANUENCIA':   [
            { code: 'ANU_AGUARDANDO', label: 'Aguardando anuência' },
            { code: 'ANU_AVERBADO',   label: 'Averbado' },
        ],
        'PAGAMENTO':  [
            { code: 'PG_AGUARDANDO_CLIENTE', label: 'Aguardando Pagamento Cliente' },
            { code: 'PG_PAGO_CLIENTE',       label: 'Pago Cliente' },
            { code: 'PG_AGUARDANDO_TC',      label: 'Aguardando Verificação de Valores' },
            { code: 'PG_PAGO_TC',            label: 'Pago TC' },
            { code: 'PG_PAGO_TC_PARCIAL',    label: 'Pago TC Parcial' },
            { code: 'PG_PAGO_TC_TOTAL',      label: 'Pago TC Total' },
            { code: 'PG_AGUARDANDO_CMS',     label: 'Aguardando pagamento CMS' },
            { code: 'PG_PAGO_CMS',           label: 'Pago CMS' },
            { code: 'PG_PAGO_CMS_EMPRESA',   label: 'Pago CMS Empresa' },
        ],
        'PENDENCIAS': [
            { code: 'PEND_AGUARDANDO', label: 'Pendência em aberto' },
            { code: 'PEND_CORRIGIDO',  label: 'Pendência corrigida' },
            { code: 'PENDENTE_CORRECAO', label: 'Pendente correção (vendedor)' },
        ],
        'CANCELADO':  [
            { code: 'CAN_ENCERRADO', label: 'Encerrado' },
            { code: 'CAN_CLIENTE', label: 'Cancelado pelo cliente' },
            { code: 'CAN_CORRETOR', label: 'Cancelado pelo corretor' },
            { code: 'CAN_BANCO', label: 'Cancelado pelo banco' },
            { code: 'CAN_REEMBOLSO', label: 'Estorno' },
            /* EstadoSolicitacaoDigitacao.CANCELADA na fila unificada (pré-contrato) */
            { code: 'CANCELADA', label: 'Cancelada (sem contrato)' },
        ],
    };

    /* Cor da etapa para a borda do sub-chip bar */
    const ETAPA_HEX = {
        'SIMULACAO':    '#2563EB',
        'DIGITACAO':    '#0EA5E9',
        'FORMALIZACAO': '#7C3AED',
        'ANALISE':      '#D97706',
        'CIP':          '#6366F1',
        'REFIN':        '#EA580C',
        'ANUENCIA':     '#0D9488',
        'PAGAMENTO':    '#16A34A',
        'PENDENCIAS':   '#DC2626',
        'CANCELADO':    '#6B7280',
    };

    const COL_SPAN_TABELA = 14;

    function crmQueryFiltros() {
        const p = new URLSearchParams();
        const periodo = (document.getElementById('filtroPeriodo') || {}).value || '';
        const banco = (document.getElementById('filtroBanco') || {}).value || '';
        const convenio = (document.getElementById('filtroConvenio') || {}).value || '';
        const produto = (document.getElementById('filtroProduto') || {}).value || '';
        const solicitante = (document.getElementById('filtroSolicitante') || {}).value || '';
        if (periodo) p.set('periodo', periodo);
        if (banco) p.set('banco_id', banco);
        if (convenio) p.set('convenio_id', convenio);
        if (produto) p.set('produto_id', produto);
        if (solicitante) p.set('solicitante_id', solicitante);
        const qs = p.toString();
        return qs ? '?' + qs : '';
    }

    function crmFormatNum(n) {
        const v = Number(n) || 0;
        return v.toLocaleString('pt-BR');
    }

    function renderKpis(data) {
        const kpis = (data && data.kpis) || {};
        const map = [
            ['em_andamento', 'kpiEmAndamento', 'kpiDeltaEmAndamento'],
            ['pendencias', 'kpiPendencias', 'kpiDeltaPendencias'],
            ['formalizacao', 'kpiFormalizacao', 'kpiDeltaFormalizacao'],
            ['pagamentos', 'kpiPagamentos', 'kpiDeltaPagamentos'],
            ['cancelados', 'kpiCancelados', 'kpiDeltaCancelados'],
        ];
        map.forEach(function (row) {
            const k = kpis[row[0]] || {};
            const valEl = document.getElementById(row[1]);
            const deltaEl = document.getElementById(row[2]);
            if (valEl) valEl.textContent = crmFormatNum(k.total);
            if (!deltaEl) return;
            deltaEl.classList.remove('up', 'down', 'neutral');
            const pct = k.variacao_pct;
            if (pct == null || pct === undefined) {
                deltaEl.classList.add('neutral');
                deltaEl.innerHTML = '<span>— vs mês anterior</span>';
                return;
            }
            const tend = k.tendencia || 'neutral';
            deltaEl.classList.add(tend);
            const seta = tend === 'up' ? '↑' : tend === 'down' ? '↓' : '•';
            const sinal = pct > 0 ? '+' : '';
            deltaEl.innerHTML = '<span>' + seta + ' ' + sinal + pct + '% vs mês anterior</span>';
        });
        crmPopularSolicitantes((data && data.solicitantes) || []);
    }

    function crmPopularSolicitantes(lista) {
        const sel = document.getElementById('filtroSolicitante');
        if (!sel) return;
        const atual = sel.value;
        sel.innerHTML = '<option value="">Solicitante</option>';
        (lista || []).forEach(function (s) {
            const o = document.createElement('option');
            o.value = String(s.id);
            o.textContent = s.nome;
            sel.appendChild(o);
        });
        if (atual) sel.value = atual;
    }

    function loadCatalogosEsteira() {
        if (_catalogosCarregados) return Promise.resolve();
        return getJson(base + 'catalogos/').then(function (d) {
            if (!d || !d.ok) return;
            _catalogosCarregados = true;
            const bancoSel = document.getElementById('filtroBanco');
            const convSel = document.getElementById('filtroConvenio');
            const prodSel = document.getElementById('filtroProduto');
            (d.bancos || []).forEach(function (b) {
                const o = document.createElement('option');
                o.value = String(b.id);
                o.textContent = b.titulo;
                if (bancoSel) bancoSel.appendChild(o);
            });
            (d.convenios || []).forEach(function (c) {
                const o = document.createElement('option');
                o.value = String(c.id);
                o.textContent = c.titulo;
                if (convSel) convSel.appendChild(o);
            });
            (d.produtos || []).forEach(function (p) {
                const o = document.createElement('option');
                o.value = String(p.id);
                o.textContent = p.titulo;
                if (prodSel) prodSel.appendChild(o);
            });
        }).catch(function () { /* noop */ });
    }

    function getItensFiltradosTabela() {
        const filtro = etapaFiltroAtivo();
        const subAtivo = document.querySelector('#chipsSubStatus .chip-sub.active');
        const subFiltro = subAtivo ? subAtivo.getAttribute('data-sub') : 'ALL';
        const q = ((document.getElementById('searchUnif') || {}).value || '').toLowerCase();
        return _todosItens.filter(function (it) {
            const matchEtapa = filtro === 'ALL' || it.etapa === filtro;
            const matchSub = subFiltro === 'ALL' || it.sub_status === subFiltro;
            const txt = (it.nome_cliente + ' ' + it.cpf_cliente + ' ' + it.contrato_codigo + ' ' + it.proposta_codigo).toLowerCase();
            const matchQ = !q || txt.includes(q);
            return matchEtapa && matchSub && matchQ;
        });
    }

    function renderPaginationFooter(total, startIdx, pageLen, totalPages) {
        const info = document.getElementById('crmPaginationInfo');
        const nav = document.getElementById('crmPagination');
        if (!info || !nav) return;
        if (!total) {
            info.textContent = 'Nenhum registro encontrado';
            nav.innerHTML = '';
            return;
        }
        const de = startIdx + 1;
        const ate = startIdx + pageLen;
        info.textContent = 'Mostrando ' + de + ' a ' + ate + ' de ' + crmFormatNum(total) + ' registros';
        let html = '';
        html += '<button type="button" class="crm-page-btn" data-page="prev" ' + (_crmPage <= 1 ? 'disabled' : '') + ' aria-label="Anterior"><i class="bx bx-chevron-left"></i></button>';
        const maxBtns = 5;
        let startP = Math.max(1, _crmPage - 2);
        let endP = Math.min(totalPages, startP + maxBtns - 1);
        startP = Math.max(1, endP - maxBtns + 1);
        for (let p = startP; p <= endP; p++) {
            html += '<button type="button" class="crm-page-btn' + (p === _crmPage ? ' active' : '') + '" data-page="' + p + '">' + p + '</button>';
        }
        html += '<button type="button" class="crm-page-btn" data-page="next" ' + (_crmPage >= totalPages ? 'disabled' : '') + ' aria-label="Próximo"><i class="bx bx-chevron-right"></i></button>';
        nav.innerHTML = html;
    }

    function crmLimparFiltros() {
        ['filtroPeriodo', 'filtroBanco', 'filtroConvenio', 'filtroProduto', 'filtroSolicitante'].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const search = document.getElementById('searchUnif');
        if (search) search.value = '';
        document.querySelectorAll('#chipsEtapa .chip').forEach(function (c) {
            c.classList.toggle('active', c.getAttribute('data-filter') === 'ALL');
        });
        renderSubChips('ALL');
        _crmPage = 1;
    }

    function renderSubChips(etapa) {
        const bar = document.getElementById('chipsSubStatus');
        const subs = ETAPA_SUBSTATUS[etapa];
        if (!subs || etapa === 'ALL') {
            bar.classList.add('d-none');
            bar.innerHTML = '';
            bar.style.setProperty('--chip-color-bar', '#6c757d');
            return;
        }

        /* Conta itens por sub-status dentro da etapa selecionada */
        const itensEtapa = _todosItens.filter(it => it.etapa === etapa);
        const cor = ETAPA_HEX[etapa] || '#6c757d';
        bar.style.setProperty('--chip-color-bar', cor);

        let html = '<span class="chip-sub active" data-sub="ALL" style="--chip-color:' + cor + '">'
            + 'Todos <span class="chip-count">' + itensEtapa.length + '</span></span>';

        subs.forEach(function (s) {
            const count = itensEtapa.filter(it => it.sub_status === s.code).length;
            html += '<span class="chip-sub" data-sub="' + s.code + '" style="--chip-color:' + cor + '">'
                + esc(s.label) + ' <span class="chip-count">' + count + '</span></span>';
        });

        bar.innerHTML = html;
        bar.classList.remove('d-none');
    }

    function etapaFiltroAtivo() {
        const chipAtivo = document.querySelector('#chipsEtapa .chip.active');
        return chipAtivo ? chipAtivo.getAttribute('data-filter') : 'ALL';
    }

    function colSpanTabela() {
        return COL_SPAN_TABELA;
    }

    function syncTableHeader() {
        const row = document.getElementById('theadUnifRow');
        if (!row) return;
        row.innerHTML =
            '<th class="crm-col-dot"></th>' +
            '<th style="width:95px">Nº Proposta</th>' +
            '<th style="width:95px">Nº Contrato</th>' +
            '<th style="width:175px">Nome Cliente</th>' +
            '<th style="width:115px">CPF</th>' +
            '<th style="width:95px">Banco</th>' +
            '<th style="width:90px">Convênio</th>' +
            '<th style="width:90px">Produto</th>' +
            '<th style="width:110px">Solicitante</th>' +
            '<th style="width:72px" class="text-center">Pendência</th>' +
            '<th style="width:60px" class="text-center">Link</th>' +
            '<th style="width:100px">Tabulação</th>' +
            '<th style="width:110px">Status</th>' +
            '<th style="width:185px" class="text-end">Ações</th>';
    }

    /* ══════════════════════════════
       CARGA DA TABELA UNIFICADA
    ══════════════════════════════ */
    function loadTabelaUnificada() {
        syncTableHeader();
        const tb = document.getElementById('tbodyUnif');
        const cs = colSpanTabela();
        const qs = crmQueryFiltros();
        tb.innerHTML = '<tr class="loading-row"><td colspan="' + cs + '"><span class="spinner-border spinner-border-sm me-2" role="status"></span>Carregando...</td></tr>';
        return Promise.all([
            getJson(base + 'fila-unificada/' + qs),
            getJson(base + 'esteira-resumo/' + qs),
            loadCatalogosEsteira(),
        ]).then(function (results) {
            const dFila = results[0];
            const dResumo = results[1];
            _todosItens = (dFila && dFila.itens) || [];
            renderKpis(dResumo);
            const chipAtivo = document.querySelector('#chipsEtapa .chip.active');
            const etapaAtiva = chipAtivo ? chipAtivo.getAttribute('data-filter') : 'ALL';
            renderSubChips(etapaAtiva);
            renderTabela();
        }).catch(function () {
            tb.innerHTML = '<tr><td colspan="' + colSpanTabela() + '" class="empty-state text-danger">Erro ao carregar dados.</td></tr>';
        });
    }

    /** Linha da esteira tem código de proposta preenchido (exibe botão de imprimir ficha). */
    function crmItemTemProposta(it) {
        return !!(it && it.proposta_codigo && String(it.proposta_codigo).trim());
    }

    /** Tipos com PDF de ficha de proposta disponível na API. */
    function crmTipoSuportaFichaPdf(tipo) {
        return tipo === 'solicitacao_dig' || tipo === 'contrato' || tipo === 'simulacao';
    }

    function baixarFichaPdfGrid(tipo, id) {
        if (!tipo || id == null || id === '') return;
        window.location.href =
            base + 'ficha/pdf/?tipo=' + encodeURIComponent(tipo) + '&id=' + encodeURIComponent(String(id));
    }

    function renderTabela() {
        const tb = document.getElementById('tbodyUnif');
        syncTableHeader();
        const cs = colSpanTabela();
        const itens = getItensFiltradosTabela();
        const total = itens.length;
        const pageSize = parseInt((document.getElementById('crmPageSize') || {}).value, 10) || 10;
        const totalPages = Math.max(1, Math.ceil(total / pageSize));
        if (_crmPage > totalPages) _crmPage = totalPages;
        if (_crmPage < 1) _crmPage = 1;
        const startIdx = (_crmPage - 1) * pageSize;
        const pageItens = itens.slice(startIdx, startIdx + pageSize);

        tb.innerHTML = '';
        if (!total) {
            tb.innerHTML = '<tr><td colspan="' + cs + '" class="empty-state"><i class="bx bx-inbox d-block mb-1"></i>Nenhum registro encontrado</td></tr>';
            renderPaginationFooter(0, 0, 0, 1);
            return;
        }

        pageItens.forEach(function (it) {
            const tr = document.createElement('tr');
            tr.setAttribute('data-etapa', it.etapa);
            tr.setAttribute('data-tipo', it.tipo);
            tr.setAttribute('data-id', it.id);

            // Coluna Link
            let linkCell = '<span class="text-muted small">Não</span>';
            if (it.link_formalizacao) {
                linkCell = '<button type="button" class="btn btn-link p-0 btn-copy-link small fw-semibold" data-link="' + esc(it.link_formalizacao) + '" title="Clique para copiar o link">Sim</button>';
            }

            // Indicador de pendência
            const pendCell = it.tem_pendencia
                ? '<span class="crm-pill-status sbadge sb-pendente"><i class="bx bx-error-circle me-1"></i>Sim</span>'
                : '<span class="text-muted small">—</span>';

            const dotColor = ETAPA_HEX[it.etapa] || '#9CA3AF';
            const dotCell = '<td class="crm-col-dot"><span class="crm-row-dot" style="--dot-color:' + dotColor + '"></span></td>';

            // Botões de ação (cores no CSS #crm-container .crm-acao-*)
            let acoes =
                '<button type="button" class="btn crm-acao-btn crm-acao-ficha me-1 btn-ficha" data-tipo="' +
                it.tipo +
                '" data-id="' +
                it.id +
                '" title="Ficha completa: cliente, proposta ou contrato e histórico">' +
                '<i class="bx bx-id-card" aria-hidden="true"></i></button>';
            if (crmItemTemProposta(it) && crmTipoSuportaFichaPdf(it.tipo)) {
                acoes +=
                    '<button type="button" class="btn crm-acao-btn crm-acao-print me-1 btn-ficha-pdf-grid" data-tipo="' +
                    it.tipo +
                    '" data-id="' +
                    it.id +
                    '" title="Baixar ficha da proposta (PDF)">' +
                    '<i class="bx bx-printer" aria-hidden="true"></i></button>';
            }
            acoes +=
                '<button type="button" class="btn crm-acao-btn crm-acao-audit me-1 btn-auditoria" data-tipo="' +
                it.tipo +
                '" data-id="' +
                it.id +
                '" title="Auditoria: linha do tempo (alterações, status, quem executou, data)">' +
                '<i class="bx bx-history" aria-hidden="true"></i></button>';
            if (crmMostrarBotaoArquivos(it)) {
                const tituloArq = it.tipo === 'solicitacao_dig'
                    ? 'PDF da proposta e arquivos do cliente (enviados pelo vendedor)'
                    : 'Vídeo de conscientização, PDF da proposta e arquivos do cliente';
                acoes +=
                    '<button type="button" class="btn crm-acao-btn crm-acao-arquivos me-1 btn-arquivos-contrato" data-tipo="' +
                    it.tipo +
                    '" data-id="' +
                    it.id +
                    '" title="' + tituloArq + '">' +
                    '<i class="bx bx-folder" aria-hidden="true"></i></button>';
            }
            const podeEvoluir = !(
                (it.tipo === 'contrato' && it.etapa === 'CANCELADO')
                || (it.tipo === 'solicitacao_dig' && it.etapa === 'CANCELADO')
            );
            if (podeEvoluir) {
                acoes +=
                    '<button type="button" class="btn crm-acao-btn crm-acao-evoluir btn-evoluir" data-tipo="' +
                    it.tipo +
                    '" data-id="' +
                    it.id +
                    '" title="Evoluir: avançar etapa ou status no fluxo operacional">' +
                    '<i class="bx bx-right-arrow-alt" aria-hidden="true"></i></button>';
            }
            if (it.tipo === 'contrato') {
                acoes +=
                    '<button type="button" class="btn crm-acao-btn crm-acao-pendencias me-1 btn-crm-pendencias" data-acess="SS35" data-tipo="' +
                    it.tipo +
                    '" data-id="' +
                    it.id +
                    '" title="Pendências: listar, resolver ou registrar">' +
                    '<i class="bx bx-error-circle" aria-hidden="true"></i></button>';
            }

            tr.innerHTML =
                dotCell +
                '<td class="font-monospace small" title="' + esc(it.proposta_codigo || '—') + '">' + esc(it.proposta_codigo || '—') + '</td>' +
                '<td class="font-monospace small" title="' + esc(it.contrato_codigo || '—') + '">' + esc(it.contrato_codigo || '—') + '</td>' +
                '<td class="fw-semibold" title="' + esc(it.nome_cliente) + '">' + esc(it.nome_cliente) + '</td>' +
                '<td class="font-monospace small" title="' + esc(it.cpf_cliente) + '">' + esc(it.cpf_cliente) + '</td>' +
                '<td class="small" title="' + esc(it.banco) + '">' + esc(it.banco) + '</td>' +
                '<td class="small" title="' + esc(it.convenio) + '">' + esc(it.convenio) + '</td>' +
                '<td class="small" title="' + esc(it.produto) + '">' + esc(it.produto) + '</td>' +
                '<td class="small" title="' + esc(it.solicitante_label || it.solicitante) + '">' +
                esc(it.solicitante_label || it.solicitante) +
                (it.tem_repasse
                    ? ' <span class="badge rounded-pill bg-warning text-dark ms-1" title="Repasse: ' +
                      esc(it.nome_repasse || '') +
                      '">Repasse</span>'
                    : '') +
                '</td>' +
                '<td class="text-center">' + pendCell + '</td>' +
                '<td class="text-center">' + linkCell + '</td>' +
                '<td>' + etapaBadge(it.etapa, it.etapa_label, it.sub_status) + '</td>' +
                '<td>' + sbadge(it.sub_status) + '</td>' +
                '<td class="text-end crm-col-acoes"><span class="crm-acoes-wrap">' + acoes + '</span></td>';
            tb.appendChild(tr);
        });
        renderPaginationFooter(total, startIdx, pageItens.length, totalPages);
    }

    /* ── Filtro por etapa ── */
    document.getElementById('chipsEtapa').addEventListener('click', function (e) {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        document.querySelectorAll('#chipsEtapa .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const filtro = chip.getAttribute('data-filter');
        _crmPage = 1;
        renderSubChips(filtro);
        const panelSub = document.getElementById('crmMaisFiltrosPanel');
        if (filtro !== 'ALL' && panelSub) {
            bootstrap.Collapse.getOrCreateInstance(panelSub, { toggle: false }).show();
        }
        renderTabela();
    });

    /* ── Filtro por sub-status ── */
    document.getElementById('chipsSubStatus').addEventListener('click', function (e) {
        const chip = e.target.closest('.chip-sub');
        if (!chip) return;
        document.querySelectorAll('#chipsSubStatus .chip-sub').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        _crmPage = 1;
        renderTabela();
    });

    document.getElementById('searchUnif').addEventListener('input', function () {
        _crmPage = 1;
        renderTabela();
    });

    ['filtroPeriodo', 'filtroBanco', 'filtroConvenio', 'filtroProduto', 'filtroSolicitante'].forEach(function (id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('change', function () {
            _crmPage = 1;
            safeReloadFilaUnificada();
        });
    });

    const btnLimpar = document.getElementById('btnCrmLimparFiltros');
    if (btnLimpar) {
        btnLimpar.addEventListener('click', function () {
            crmLimparFiltros();
            safeReloadFilaUnificada();
        });
    }

    const btnMaisFiltros = document.getElementById('btnCrmMaisFiltros');
    const panelMaisFiltros = document.getElementById('crmMaisFiltrosPanel');
    if (btnMaisFiltros && panelMaisFiltros) {
        btnMaisFiltros.addEventListener('click', function () {
            const inst = bootstrap.Collapse.getOrCreateInstance(panelMaisFiltros, { toggle: false });
            inst.toggle();
        });
        panelMaisFiltros.addEventListener('shown.bs.collapse', function () {
            btnMaisFiltros.setAttribute('aria-expanded', 'true');
        });
        panelMaisFiltros.addEventListener('hidden.bs.collapse', function () {
            btnMaisFiltros.setAttribute('aria-expanded', 'false');
        });
    }

    const crmPageSizeEl = document.getElementById('crmPageSize');
    if (crmPageSizeEl) {
        crmPageSizeEl.addEventListener('change', function () {
            _crmPage = 1;
            renderTabela();
        });
    }

    const crmPagination = document.getElementById('crmPagination');
    if (crmPagination) {
        crmPagination.addEventListener('click', function (e) {
            const btn = e.target.closest('.crm-page-btn');
            if (!btn || btn.disabled) return;
            const p = btn.getAttribute('data-page');
            const itens = getItensFiltradosTabela();
            const pageSize = parseInt((document.getElementById('crmPageSize') || {}).value, 10) || 10;
            const totalPages = Math.max(1, Math.ceil(itens.length / pageSize));
            if (p === 'prev') _crmPage = Math.max(1, _crmPage - 1);
            else if (p === 'next') _crmPage = Math.min(totalPages, _crmPage + 1);
            else _crmPage = parseInt(p, 10) || 1;
            renderTabela();
        });
    }

    /* ── Copiar link ── */
    document.getElementById('tbodyUnif').addEventListener('click', function (e) {
        const btn = e.target.closest('.btn-copy-link');
        if (!btn) return;
        const link = btn.getAttribute('data-link');
        navigator.clipboard.writeText(link).then(function () {
            showToast('Link copiado!', 'success');
        }).catch(function () {
            showToast('Não foi possível copiar o link.', 'warning');
        });
    });

    /* ══════════════════════════════
       MODAL VISUALIZAR FICHA
    ══════════════════════════════ */
    document.getElementById('tbodyUnif').addEventListener('click', function (e) {
        const btn = e.target.closest('.btn-ficha');
        if (btn) {
            const t = btn.getAttribute('data-tipo');
            const i = btn.getAttribute('data-id');
            crmExecutarAcaoProposta(t, i, function (rt, ri) {
                abrirModalFicha(rt || t, ri || i);
            });
        }

        const btnPdfGrid = e.target.closest('.btn-ficha-pdf-grid');
        if (btnPdfGrid) {
            const t = btnPdfGrid.getAttribute('data-tipo');
            const i = btnPdfGrid.getAttribute('data-id');
            crmExecutarAcaoProposta(t, i, function (rt, ri) {
                baixarFichaPdfGrid(rt || t, ri || i);
            });
        }

        const btnAud = e.target.closest('.btn-auditoria');
        if (btnAud) {
            const t = btnAud.getAttribute('data-tipo');
            const i = btnAud.getAttribute('data-id');
            crmExecutarAcaoProposta(t, i, function (rt, ri) {
                abrirModalAuditoria(rt || t, ri || i);
            });
        }

        const btnEv = e.target.closest('.btn-evoluir');
        if (btnEv) {
            const t = btnEv.getAttribute('data-tipo');
            const i = btnEv.getAttribute('data-id');
            crmExecutarAcaoProposta(t, i, function (rt, ri) {
                abrirModalEvoluir(rt || t, ri || i);
            });
        }

        const btnArq = e.target.closest('.btn-arquivos-contrato');
        if (btnArq) {
            const cid = btnArq.getAttribute('data-id');
            const ctipo = btnArq.getAttribute('data-tipo') || 'contrato';
            if (cid) {
                crmExecutarAcaoProposta(ctipo, cid, function (rt, ri) {
                    abrirModalArquivosContrato(rt || ctipo, ri || cid);
                });
            }
        }

        const btnPendGrid = e.target.closest('.btn-crm-pendencias');
        if (btnPendGrid) {
            const cidp = btnPendGrid.getAttribute('data-id');
            if (cidp) abrirModalPendenciasContrato(cidp);
        }
    });

    function _auditoriaTextoMudanca(h) {
        if (h.etapa_nova_label) {
            const de =
                (h.etapa_anterior_label || '—') +
                ' › ' +
                (h.sub_anterior_label || '—');
            const para = (h.etapa_nova_label || '—') + ' › ' + (h.sub_nova_label || '—');
            return 'De ' + de + ' → ' + para;
        }
        const deE = h.estado_anterior_label || h.estado_anterior || '—';
        const paraE = h.estado_novo_label || h.estado_novo || '—';
        return 'De ' + deE + ' → ' + paraE;
    }

    function _auditoriaStatusDestino(h) {
        if (h.etapa_nova_label) {
            return (h.etapa_nova_label || '—') + ' › ' + (h.sub_nova_label || '—');
        }
        return h.estado_novo_label || h.estado_novo || '—';
    }

    function renderAuditoriaConteudo(d) {
        const meta = d.meta || {};
        const nome = meta.nome_cliente || '—';
        const prop = meta.proposta_codigo || '—';
        const ctr = meta.contrato_codigo || '';
        const sol = meta.solicitante || '';
        let metaHtml =
            '<strong class="text-body">' +
            esc(nome) +
            '</strong><br>' +
            'Proposta: <span class="font-monospace">' +
            esc(prop) +
            '</span>';
        if (ctr) {
            metaHtml += ' · Contrato: <span class="font-monospace">' + esc(ctr) + '</span>';
        }
        if (sol) {
            metaHtml +=
                '<br><span class="text-secondary">Solicitante (referência): ' + esc(sol) + '</span>';
        }
        document.getElementById('auditoriaMeta').innerHTML = metaHtml;

        const hist = d.historico || [];
        const host = document.getElementById('auditoriaTimeline');
        if (!hist.length) {
            host.innerHTML = '<p class="text-muted mb-0">Sem registros de auditoria para este registro.</p>';
            return;
        }
        let html = '<div class="timeline-wrap">';
        hist.forEach(function (h) {
            const statusTxt = _auditoriaStatusDestino(h);
            const mud = _auditoriaTextoMudanca(h);
            const quem = h.usuario && h.usuario !== '—' ? esc(h.usuario) : '—';
            html +=
                '<div class="timeline-item">' +
                '<div class="timeline-dot"></div>' +
                '<div class="timeline-content">' +
                '<div class="d-flex justify-content-between align-items-start flex-wrap gap-1">' +
                '<span class="fw-semibold text-dark">Tabulação / status: ' +
                esc(statusTxt) +
                '</span>' +
                '<span class="text-muted small text-nowrap">' +
                esc(h.data || '') +
                '</span>' +
                '</div>' +
                '<div class="small text-secondary mt-1">Alteração: ' +
                esc(mud) +
                '</div>' +
                '<div class="small mt-1"><i class="bx bx-user-check me-1"></i>Executado por: ' +
                quem +
                '</div>';
            if (h.observacao) {
                html +=
                    '<div class="small fst-italic mt-2 text-muted border-start border-2 ps-2">' +
                    esc(h.observacao) +
                    '</div>';
            }
            html += '</div></div>';
        });
        html += '</div>';
        host.innerHTML = html;
    }

    function abrirModalAuditoria(tipo, id) {
        document.getElementById('auditoriaTituloTexto').textContent = 'Auditoria do fluxo';
        document.getElementById('auditoriaMeta').innerHTML =
            '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Carregando...';
        document.getElementById('auditoriaTimeline').innerHTML = '';
        const modalEl = document.getElementById('modalAuditoriaCrm');
        bootstrap.Modal.getOrCreateInstance(modalEl).show();

        getJson(
            base +
                'auditoria-fluxo/?tipo=' +
                encodeURIComponent(tipo) +
                '&id=' +
                encodeURIComponent(id)
        ).then(function (d) {
            if (!d.ok) {
                document.getElementById('auditoriaMeta').innerHTML = '';
                document.getElementById('auditoriaTimeline').innerHTML =
                    '<p class="text-danger mb-0">' + esc(d.erro || 'Erro ao carregar auditoria.') + '</p>';
                showToast(d.erro || 'Erro ao carregar auditoria.', 'danger');
                return;
            }
            const rotulo =
                d.tipo === 'contrato'
                    ? 'Contrato'
                    : d.tipo === 'simulacao'
                      ? 'Simulação'
                      : 'Solicitação digitação';
            document.getElementById('auditoriaTituloTexto').textContent = 'Auditoria — ' + rotulo;
            renderAuditoriaConteudo(d);
        }).catch(function () {
            document.getElementById('auditoriaMeta').innerHTML = '';
            document.getElementById('auditoriaTimeline').innerHTML =
                '<p class="text-danger mb-0">Erro de comunicação.</p>';
            showToast('Erro ao carregar auditoria.', 'danger');
        });
    }

    document.getElementById('modalArquivosContrato').addEventListener('hidden.bs.modal', function () {
        blurFocoAtivo();
        if (_crmArquivosPendente === 'video') {
            _crmArquivosPendente = null;
            const inp = document.getElementById('crmUpVidFile');
            if (inp) inp.value = '';
            const cid = _crmArquivosContratoId;
            if (cid) document.getElementById('crmUpVidContratoId').value = cid;
            bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCrmUploadVideo')).show();
        } else if (_crmArquivosPendente === 'arquivo') {
            _crmArquivosPendente = null;
            const f = document.getElementById('crmUpArqFile');
            const t = document.getElementById('crmUpArqTitulo');
            if (f) f.value = '';
            if (t) t.value = '';
            const cid = _crmArquivosContratoId;
            const ctipo = _crmArquivosTipo || 'contrato';
            if (cid) {
                document.getElementById('crmUpArqContratoId').value = cid;
                const hidTipo = document.getElementById('crmUpArqTipo');
                if (hidTipo) hidTipo.value = ctipo;
            }
            bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCrmUploadArquivo')).show();
        }
    });

    document.getElementById('crmArqBtnVideo').addEventListener('click', function () {
        if (!_crmArquivosContratoId) return;
        document.getElementById('crmUpVidContratoId').value = _crmArquivosContratoId;
        _crmArquivosPendente = 'video';
        blurFocoAtivo();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalArquivosContrato')).hide();
    });

    document.getElementById('crmArqBtnArquivo').addEventListener('click', function () {
        if (!_crmArquivosContratoId) return;
        document.getElementById('crmUpArqContratoId').value = _crmArquivosContratoId;
        const hidTipo = document.getElementById('crmUpArqTipo');
        if (hidTipo) hidTipo.value = _crmArquivosTipo || 'contrato';
        _crmArquivosPendente = 'arquivo';
        blurFocoAtivo();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalArquivosContrato')).hide();
    });

    ['modalCrmUploadVideo', 'modalCrmUploadArquivo'].forEach(function (mid) {
        const el = document.getElementById(mid);
        if (el) {
            el.addEventListener('hide.bs.modal', blurFocoAtivo);
        }
    });

    document.getElementById('crmUpVidConfirmar').addEventListener('click', function () {
        const cid = document.getElementById('crmUpVidContratoId').value;
        const inp = document.getElementById('crmUpVidFile');
        const btn = document.getElementById('crmUpVidConfirmar');
        if (!cid || !inp || !inp.files || !inp.files[0]) {
            showToast('Selecione um vídeo.', 'warning');
            return;
        }
        const arqVid = inp.files[0];
        if (arqVid.size > VIDEO_UPLOAD_MAX_BYTES) {
            showToast(MSG_VIDEO_TAMANHO, 'danger');
            return;
        }
        btn.disabled = true;
        const fd = new FormData();
        fd.append('video', arqVid);
        postMultipart(base + 'contrato/' + encodeURIComponent(cid) + '/upload-video/', fd).then(function (r) {
            btn.disabled = false;
            if (!r.ok) {
                showToast(r.erro || 'Erro ao enviar vídeo.', 'danger');
                return;
            }
            showToast('Vídeo enviado com sucesso.', 'success');
            blurFocoAtivo();
            bootstrap.Modal.getInstance(document.getElementById('modalCrmUploadVideo')).hide();
            inp.value = '';
            if (_pagoTcModal) {
                _pagoTcModal.flag_video_enviado = true;
            }
            const modalEvEl = document.getElementById('modalEvoluir');
            if (modalEvEl && modalEvEl.classList.contains('show')) {
                const selSub = document.getElementById('evoluirSub');
                const optSub = selSub && selSub.options[selSub.selectedIndex];
                const reqSub = optSub ? optSub.getAttribute('data-requer') : null;
                const acSub = optSub ? optSub.getAttribute('data-acao') || optSub.value : null;
                _toggleExtraFields(reqSub, acSub);
                return;
            }
            abrirModalArquivosContrato(cid);
        }).catch(function () {
            btn.disabled = false;
            showToast('Erro de comunicação.', 'danger');
        });
    });

    document.getElementById('crmUpArqConfirmar').addEventListener('click', function () {
        const cid = document.getElementById('crmUpArqContratoId').value;
        const hidTipo = document.getElementById('crmUpArqTipo');
        const arqTipo = (hidTipo && hidTipo.value) || _crmArquivosTipo || 'contrato';
        const inp = document.getElementById('crmUpArqFile');
        const tit = document.getElementById('crmUpArqTitulo');
        const btn = document.getElementById('crmUpArqConfirmar');
        if (!cid || !inp || !inp.files || !inp.files[0]) {
            showToast('Selecione um arquivo.', 'warning');
            return;
        }
        btn.disabled = true;
        const fd = new FormData();
        fd.append('arquivo', inp.files[0]);
        const tx = (tit && tit.value) ? String(tit.value).trim() : '';
        if (tx) fd.append('titulo', tx);
        const urlUpload = arqTipo === 'solicitacao_dig'
            ? base + 'solicitacao-dig/' + encodeURIComponent(cid) + '/cliente-arquivo/'
            : base + 'contrato/' + encodeURIComponent(cid) + '/cliente-arquivo/';
        postMultipart(urlUpload, fd).then(function (r) {
            btn.disabled = false;
            if (!r.ok) {
                showToast(r.erro || 'Erro ao enviar arquivo.', 'danger');
                return;
            }
            showToast('Arquivo enviado com sucesso.', 'success');
            blurFocoAtivo();
            bootstrap.Modal.getInstance(document.getElementById('modalCrmUploadArquivo')).hide();
            inp.value = '';
            if (tit) tit.value = '';
            abrirModalArquivosContrato(arqTipo, cid);
        }).catch(function () {
            btn.disabled = false;
            showToast('Erro de comunicação.', 'danger');
        });
    });

    const btnConfirmarGerarContrato = document.getElementById('btnConfirmarGerarContrato');
    if (btnConfirmarGerarContrato) {
        btnConfirmarGerarContrato.addEventListener('click', confirmarGerarContratoObrigatorio);
    }

    function abrirModalFicha(tipo, id) {
        window._crmFichaContext = { tipo: tipo, id: id };
        const modal = new bootstrap.Modal(document.getElementById('modalFicha'));
        const hostRep = document.getElementById('fichaRepasseResumo');
        if (hostRep) {
            hostRep.className = 'd-none mb-3';
            hostRep.innerHTML = '';
        }
        document.getElementById('fichaConteudoPessoais').innerHTML = '<div class="text-center py-4"><span class="spinner-border spinner-border-sm me-2"></span>Carregando...</div>';
        document.getElementById('fichaConteudoProposta').innerHTML = '';
        const ulArq0 = document.getElementById('fichaListaArquivos');
        const semArq0 = document.getElementById('fichaSemArquivos');
        const midiaTopo0 = document.getElementById('fichaMidiaResumo');
        if (ulArq0) ulArq0.innerHTML = '';
        if (semArq0) semArq0.classList.add('d-none');
        if (midiaTopo0) midiaTopo0.innerHTML = '';
        const btnPdf = document.getElementById('btnFichaPdf');
        if (btnPdf) btnPdf.classList.add('d-none');
        const btnEd0 = document.getElementById('btnFichaEditar');
        const btnPend0 = document.getElementById('btnFichaPendencias');
        if (btnEd0) {
            btnEd0.classList.add('d-none');
            btnEd0.removeAttribute('data-contrato-id');
            btnEd0.removeAttribute('data-ficha-tipo');
        }
        if (btnPend0) btnPend0.classList.add('d-none');
        // Ativa a aba de dados pessoais ao abrir
        const tabPessoais = document.querySelector('#tabsFicha .nav-link:first-child');
        if (tabPessoais) bootstrap.Tab.getOrCreateInstance(tabPessoais).show();
        modal.show();

        // Validação [6] — critério 10 (performance): omitir o histórico do payload.
        // A linha do tempo agora é exclusiva do modal de Auditoria (coluna Ações).
        getJson(base + 'ficha/?tipo=' + encodeURIComponent(tipo) + '&id=' + encodeURIComponent(id) + '&with_historico=0').then(function (d) {
            if (!d.ok) { showToast(d.erro || 'Erro ao carregar ficha.', 'danger'); return; }
            renderFichaConteudo(d);
            const ctx = window._crmFichaContext || {};
            _carregarFichaArquivos(ctx.tipo, ctx.id);
            const btnEd = document.getElementById('btnFichaEditar');
            const btnPend = document.getElementById('btnFichaPendencias');
            const podeEditarFicha = (ctx.tipo === 'contrato' || ctx.tipo === 'solicitacao_dig')
                && ctx.id != null && ctx.id !== '';
            if (podeEditarFicha) {
                const sid = String(ctx.id);
                if (btnEd) {
                    btnEd.setAttribute('data-contrato-id', sid);
                    btnEd.setAttribute('data-ficha-tipo', ctx.tipo);
                    btnEd.classList.remove('d-none');
                }
                if (btnPend && ctx.tipo === 'contrato') {
                    btnPend.setAttribute('data-contrato-id', sid);
                    btnPend.classList.remove('d-none');
                } else if (btnPend) {
                    btnPend.classList.add('d-none');
                    btnPend.removeAttribute('data-contrato-id');
                }
            } else {
                if (btnEd) {
                    btnEd.classList.add('d-none');
                    btnEd.removeAttribute('data-contrato-id');
                    btnEd.removeAttribute('data-ficha-tipo');
                }
                if (btnPend) {
                    btnPend.classList.add('d-none');
                    btnPend.removeAttribute('data-contrato-id');
                }
            }
        }).catch(function () {
            document.getElementById('fichaConteudoPessoais').innerHTML = '<p class="text-danger">Erro ao carregar dados.</p>';
        });
    }

    document.getElementById('btnFichaPdf').addEventListener('click', function () {
        const ctx = window._crmFichaContext || {};
        if (!ctx.tipo || ctx.id == null || ctx.id === '') return;
        window.location.href = base + 'ficha/pdf/?tipo=' + encodeURIComponent(ctx.tipo) + '&id=' + encodeURIComponent(String(ctx.id));
    });

    /** Rótulo legível para contato dinâmico (ficha CRM). */
    function _crmLabelTipoContatoDinamico(ct) {
        if (ct && ct.tipo_label) return String(ct.tipo_label);
        const t = (ct && ct.tipo) ? String(ct.tipo).toUpperCase() : '';
        const map = { CELULAR: 'Celular', TELEFONE_FIXO: 'Telefone fixo', EMAIL: 'E-mail' };
        return map[t] || (ct && ct.tipo ? String(ct.tipo) : 'Contato');
    }

    /** Primeiro valor não vazio entre contatos dinâmicos com o tipo informado (código em maiúsculas). */
    function _crmValorPrimeiroContatoDinamico(contatos, tipo) {
        const list = Array.isArray(contatos) ? contatos : [];
        const u = String(tipo || '').toUpperCase();
        for (let i = 0; i < list.length; i++) {
            const c = list[i];
            if (c && String(c.tipo || '').toUpperCase() === u) {
                const raw = (c.valor != null && c.valor !== '') ? String(c.valor).trim() : '';
                if (raw) return raw;
            }
        }
        return '';
    }

    function _crmEmailEditPreferido(dp) {
        const v = _crmValorPrimeiroContatoDinamico(dp.contatos_dinamicos || [], 'EMAIL');
        if (v) return v;
        return (dp.email != null && String(dp.email).trim()) ? String(dp.email).trim() : '';
    }

    function _crmTelefoneEditPreferido(dp) {
        const cds = dp.contatos_dinamicos || [];
        let v = _crmValorPrimeiroContatoDinamico(cds, 'CELULAR');
        if (v) return v;
        v = _crmValorPrimeiroContatoDinamico(cds, 'TELEFONE_FIXO');
        if (v) return v;
        return (dp.telefone != null && String(dp.telefone).trim()) ? String(dp.telefone).trim() : '';
    }

    function _crmFmtMoedaFicha(v) {
        if (v === '' || v === null || v === undefined) return '';
        const s = String(v).trim();
        if (!s) return '';
        const n = parseFloat(s.replace(',', '.'));
        if (isNaN(n)) return 'R$ ' + s;
        return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function _crmBancarioTemDados(b) {
        if (!b) return false;
        return !!(b.banco || b.agencia || b.conta || b.matricula || b.incluir_seguro || b.senha_cadastrada);
    }

    function _crmHtmlFichaSecaoTitulo(titulo) {
        return '<div class="ficha-secao col-12"><h6 class="ficha-secao-titulo">' + esc(titulo) + '</h6>';
    }

    function _crmHtmlFichaCampoGrid(pares) {
        let h = '<div class="row g-2 mb-2">';
        (pares || []).forEach(function (r) {
            const val = r[1];
            if (val === '' || val === null || val === undefined) return;
            h += '<div class="col-md-4"><label class="form-label small text-muted mb-0">' + esc(r[0]) +
                '</label><p class="fw-semibold mb-2">' + esc(String(val)) + '</p></div>';
        });
        return h + '</div></div>';
    }

    /** Seção somente leitura: todos e-mails/telefones dinâmicos ou fallback aos campos fixos do cliente. */
    function _crmHtmlSecaoContatosCliente(dp) {
        dp = dp || {};
        const cds = Array.isArray(dp.contatos_dinamicos) ? dp.contatos_dinamicos : [];
        const ordemTipo = { EMAIL: 1, CELULAR: 2, TELEFONE_FIXO: 3 };
        const itens = [];
        cds.forEach(function (ct) {
            const t = String(ct.tipo || '').toUpperCase();
            const o = ordemTipo[t];
            if (!o) return;
            const val = (ct.valor != null && String(ct.valor).trim()) ? String(ct.valor).trim() : '';
            if (!val) return;
            itens.push({ o: o, lbl: _crmLabelTipoContatoDinamico(ct), val: val });
        });
        itens.sort(function (a, b) { return a.o - b.o; });
        let inner = '<div class="row g-2">';
        if (itens.length > 0) {
            itens.forEach(function (it) {
                inner += '<div class="col-md-4"><span class="small text-muted">' + esc(it.lbl) + '</span><p class="fw-semibold mb-0 small">' + esc(it.val) + '</p></div>';
            });
        } else {
            const fixos = [
                ['E-mail', dp.email],
                ['Telefone', dp.telefone],
                ['Telefone residencial', dp.telefone_residencial],
            ];
            let algum = false;
            fixos.forEach(function (r) {
                const v = r[1] != null ? String(r[1]).trim() : '';
                if (!v) return;
                algum = true;
                inner += '<div class="col-md-4"><span class="small text-muted">' + esc(r[0]) + '</span><p class="fw-semibold mb-0 small">' + esc(v) + '</p></div>';
            });
            if (!algum) {
                inner += '<p class="small text-muted mb-0">Nenhum contato cadastrado.</p>';
            }
        }
        inner += '</div>';
        return (
            '<div class="border rounded-2 p-3 bg-light">' +
            '<h6 class="small fw-semibold text-uppercase text-muted mb-2"><i class="bx bx-envelope me-1"></i>E-mails e telefones</h6>' +
            inner +
            '</div>'
        );
    }

    function _crmRenderRepasseBloco(rep) {
        const host = document.getElementById('fichaRepasseResumo');
        if (!host) return;
        const r = rep || {};
        const tem = !!r.tem_repasse;
        const badgeCls = tem ? 'bg-warning text-dark' : 'bg-secondary';
        const cardCls = tem ? 'alert alert-warning border-warning mb-0 py-3' : 'alert alert-light border mb-0 py-3';
        let detalhe = '';
        if (tem) {
            detalhe =
                '<div class="row g-2 small mt-2">' +
                '<div class="col-md-4"><span class="text-muted d-block">Solicitante (responsável)</span><span class="fw-semibold">' +
                esc(r.nome_responsavel || '—') +
                '</span></div>' +
                '<div class="col-md-4"><span class="text-muted d-block">Repassado por</span><span class="fw-semibold">' +
                esc(r.nome_repasse || '—') +
                '</span></div>' +
                '<div class="col-md-4"><span class="text-muted d-block">Quem abriu a solicitação</span><span class="fw-semibold">' +
                esc(r.nome_solicitante_criador || '—') +
                '</span></div>' +
                '</div>';
        }
        host.className = 'mb-3';
        host.innerHTML =
            '<div class="' +
            cardCls +
            '">' +
            '<div class="d-flex flex-wrap align-items-center gap-2">' +
            '<span class="fw-semibold"><i class="bx bx-transfer-alt me-1"></i>Repasse de carteira</span>' +
            '<span class="badge rounded-pill ' +
            badgeCls +
            '">' +
            (tem ? 'Sim' : 'Não') +
            '</span>' +
            '</div>' +
            '<p class="small mb-0 mt-2">' +
            esc(r.resumo || (tem ? 'Cliente extra em repasse.' : 'Sem repasse nesta carteira.')) +
            '</p>' +
            detalhe +
            '</div>';
    }

    function _crmPreencherRepassePagoTc(m) {
        const data = m || {};
        const tem = !!data.tem_repasse;
        const badgeRep = document.getElementById('evoluirPctcRepasseBadge');
        if (badgeRep) {
            badgeRep.textContent = tem ? 'Repasse: Sim' : 'Repasse: Não';
            badgeRep.className = 'badge rounded-pill ' + (tem ? 'bg-warning text-dark' : 'bg-secondary');
        }
        const solEl = document.getElementById('evoluirPctcRepasseSolicitante');
        const origEl = document.getElementById('evoluirPctcRepasseOrigem');
        const origWrap = document.getElementById('evoluirPctcRepasseOrigemWrap');
        const criEl = document.getElementById('evoluirPctcRepasseCriador');
        const resumoEl = document.getElementById('evoluirPctcRepasseResumo');
        const respNome = data.nome_responsavel || '—';
        if (solEl) solEl.textContent = respNome;
        if (origEl) origEl.textContent = tem ? data.nome_repasse || '—' : '—';
        if (origWrap) {
            if (tem) origWrap.classList.remove('d-none');
            else origWrap.classList.add('d-none');
        }
        const criador =
            (data.destinatarios || []).find(function (d) {
                return d.papel === 'vendedor';
            })?.nome ||
            respNome;
        if (criEl) criEl.textContent = criador;
        if (resumoEl) {
            if (tem) {
                resumoEl.textContent =
                    'O cliente foi repassado por ' +
                    (data.nome_repasse || '—') +
                    ' para o solicitante ' +
                    (data.nome_responsavel || '—') +
                    '. No Pago TC, o valor de TC será dividido 50% para cada um.';
            } else {
                resumoEl.textContent =
                    'Sem repasse: o RegisterMoney de TC será lançado integralmente para o solicitante/responsável.';
            }
        }
        const card = document.getElementById('evoluirPctcRepasseCard');
        if (card) {
            card.classList.toggle('border-warning', tem);
            card.classList.toggle('bg-light', !tem);
        }
    }

    function renderFichaConteudo(d) {
        const tipoFicha = d.tipo || (window._crmFichaContext && window._crmFichaContext.tipo);
        _crmRenderRepasseBloco(d.repasse);
        const btnPdfEl = document.getElementById('btnFichaPdf');
        if (btnPdfEl) {
            if (tipoFicha === 'simulacao') {
                btnPdfEl.classList.add('d-none');
            } else {
                btnPdfEl.classList.remove('d-none');
            }
        }
        // Dados pessoais (contatos concentrados na seção única; sem duplicar no grid)
        const dp = d.dados_pessoais || {};
        const rows = [
            ['Nome completo', dp.nome_completo],
            ['CPF', dp.cpf],
            ['Sexo', dp.sexo],
            ['Data de nascimento', dp.data_nascimento],
            ['Naturalidade', dp.naturalidade],
            ['País de origem', dp.pais_origem],
            ['RG', dp.numero_rg + (dp.orgao_emissor_rg ? ' / ' + dp.orgao_emissor_rg : '') + (dp.uf_emissao_rg ? ' - ' + dp.uf_emissao_rg : '')],
            ['Nome da mãe', dp.nome_mae],
            ['Nome do pai', dp.nome_pai],
        ];
        rows.push(['CEP', dp.cep], ['Endereço', dp.logradouro]);
        const temContratoFicha = !!d.contrato;
        const ctrDp = d.contrato;
        let htmlPessoais = temContratoFicha ? '' : _crmHtmlFichaSecaoTitulo('Contato');
        if (!temContratoFicha) {
            htmlPessoais += '<\u0064iv class="col-12 mb-3">' + _crmHtmlSecaoContatosCliente(dp) + '</\u0064iv></\u0064iv>';
        }
        htmlPessoais += _crmHtmlFichaSecaoTitulo('Dados pessoais');
        rows.forEach(function (r) {
            if (!r[1]) return;
            htmlPessoais += '<div class="col-md-4"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-2">' + esc(r[1]) + '</p></div>';
        });
        if (!temContratoFicha) {
            (dp.representantes || []).forEach(function (rp) {
                htmlPessoais += '<div class="col-md-6"><label class="form-label small text-muted mb-0">Representante</label><p class="fw-semibold mb-2">' + esc(rp.nome_representante) + ' — ' + esc(rp.cpf_representante) + '</p></div>';
            });
        }
        (dp.enderecos_dinamicos || []).forEach(function (ed) {
            const bits = [ed.cep, ed.logradouro].filter(Boolean).join(' — ');
            if (!bits) return;
            htmlPessoais += '<div class="col-md-4"><label class="form-label small text-muted mb-0">Endereço adicional</label><p class="fw-semibold mb-2">' + esc(bits) + (ed.principal ? ' <span class="badge bg-secondary">Principal</span>' : '') + '</p></div>';
        });
        htmlPessoais += '</div>';
        if (temContratoFicha) {
            htmlPessoais += _crmHtmlFichaSecaoTitulo('Contato');
            htmlPessoais += '<\u0064iv class="col-12 mb-3">' + _crmHtmlSecaoContatosCliente(dp) + '</\u0064iv></\u0064iv>';
        }
        const dbCli = dp.dados_bancarios;
        htmlPessoais += _crmHtmlFichaSecaoTitulo('Dados bancários do cliente');
        if (dbCli) {
            [
                ['Banco', dbCli.banco],
                ['Agência', dbCli.agencia],
                ['DV agência', dbCli.dv_agencia],
                ['Conta', dbCli.conta],
                ['DV conta', dbCli.dv_conta],
                ['Tipo de conta', dbCli.tipo_conta],
                ['Tipo de pagamento', dbCli.tipo_pagamento],
                ['Matrícula', dbCli.matricula],
            ].forEach(function (r) {
                if (!r[1]) return;
                htmlPessoais += '<div class="col-md-3"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-2">' + esc(r[1]) + '</p></div>';
            });
            if (dbCli.incluir_seguro) {
                htmlPessoais += '<div class="col-md-3"><label class="form-label small text-muted mb-0">Seguro</label><p class="fw-semibold mb-2">Sim</p></div>';
            }
            if (dbCli.senha_cadastrada) {
                htmlPessoais += '<div class="col-md-3"><label class="form-label small text-muted mb-0">Senha bancária</label><p class="fw-semibold mb-2 text-muted">Cadastrada</p></div>';
            }
        }
        htmlPessoais += _crmHtmlFichaSecaoTitulo('Outros');
        htmlPessoais += _crmHtmlFichaCampoGrid([
            ['Data criação cadastro', dp.data_criacao],
            ['Última atualização cadastro', dp.data_atualizacao],
            ['Data criação contrato', ctrDp && ctrDp.data_criacao ? ctrDp.data_criacao : ''],
        ]);
        if (temContratoFicha && (dp.representantes || []).length) {
            htmlPessoais += _crmHtmlFichaSecaoTitulo('Representante');
            (dp.representantes || []).forEach(function (rp) {
                htmlPessoais += '<\u0064iv class="col-md-6"><label class="form-label small text-muted mb-0">Nome</label><p class="fw-semibold mb-2">' + esc(rp.nome_representante) + '</p></\u0064iv>';
                htmlPessoais += '<\u0064iv class="col-md-6"><label class="form-label small text-muted mb-0">CPF</label><p class="fw-semibold mb-2">' + esc(rp.cpf_representante) + '</p></\u0064iv>';
            });
            htmlPessoais += '</\u0064iv>';
        }
        document.getElementById('fichaConteudoPessoais').innerHTML = htmlPessoais || '<p class="text-muted">Sem dados pessoais cadastrados.</p>';

        const solCtr = d.solicitacao;
        const mostrarCtrFicha = !!d.contrato || !!(solCtr && ((solCtr.numero_contrato_banco_pre || '').trim() || (solCtr.link_formalizacao_pre || '').trim()));
        const titProposta = temContratoFicha ? 'Dados Proposta' : 'Proposta de Empréstimo';

        function _crmHtmlFichaBlocoContrato() {
            if (!mostrarCtrFicha) return '';
            let h = _crmHtmlFichaSecaoTitulo('Dados do Contrato');
            if (d.contrato) {
                const c = d.contrato;
                const vin = c.vinculo_port_refin || {};
                if (vin.papel && vin.contrato_codigo) {
                    const lblVin = vin.papel === 'REFIN'
                        ? 'Vinculado ao PORT'
                        : 'REFIN gerado';
                    h += '<div class="col-12 mb-2"><span class="badge bg-info-subtle text-info">' +
                        esc(lblVin) + ': ' + esc(vin.contrato_codigo) +
                        (vin.proposta_codigo ? ' (proposta ' + esc(vin.proposta_codigo) + ')' : '') +
                        '</span></div>';
                }
                h += '<\u0064iv class="row g-2">';
                [['Nº contrato', c.codigo], ['Etapa', c.etapa_operacional], ['Sub-status', c.sub_status_operacional],
                 ['Tabela CMS', c.tabela_cms], ['Valor TC', c.valor_tc ? 'R$ ' + c.valor_tc : ''],
                 ['Valor AF', c.valor_af ? 'R$ ' + c.valor_af : ''], ['Valor Parcela', c.valor_parcela ? 'R$ ' + c.valor_parcela : ''],
                 ['Prazo', c.prazo ? c.prazo + ' meses' : ''], ['Valor Liberado', c.valor_liberado ? 'R$ ' + c.valor_liberado : ''],
                 ['Valor Saldo', (c.exibe_valor_saldo && c.valor_saldo) ? 'R$ ' + c.valor_saldo : ''],
                 ['Portabilidade', c.portabilidade ? 'Sim' : 'Não']].forEach(function (r) {
                    if (!r[1]) return;
                    h += '<\u0064iv class="col-md-3"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-1">' + esc(r[1]) + '</p></\u0064iv>';
                });
                if (c.link_formalizacao) {
                    h += '<\u0064iv class="col-12"><label class="form-label small text-muted mb-0">Link de Formalização</label><p class="mb-1"><a href="' + esc(c.link_formalizacao) + '" target="_blank" rel="noopener">' + esc(c.link_formalizacao) + '</a></p></\u0064iv>';
                }
                h += '</\u0064iv>';
            } else if (solCtr) {
                h += '<\u0064iv class="row g-2">';
                [['Nº contrato (banco)', solCtr.numero_contrato_banco_pre], ['Link formalização', solCtr.link_formalizacao_pre]].forEach(function (r) {
                    if (!r[1]) return;
                    h += '<\u0064iv class="col-md-6"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-1">' + esc(r[1]) + '</p></\u0064iv>';
                });
                h += '</\u0064iv>';
            }
            return h;
        }

        // Proposta / Contrato
        let htmlProp = temContratoFicha ? _crmHtmlFichaBlocoContrato() : '';
        (d.propostas || []).forEach(function (p, i) {
            htmlProp += '<h6 class="ficha-secao-titulo mb-2 mt-' + (i > 0 ? '3' : (temContratoFicha ? '3' : '0')) + '">' + titProposta + (d.propostas.length > 1 ? ' #' + (i + 1) : '') + ' — ' + esc(p.codigo) + '</h6>';
            htmlProp += '<div class="row g-2 mb-3">';
            [['Banco', p.banco], ['Convênio', p.convenio], ['Produto', p.produto],
             ['Tabela', p.tabela_cms],
             [
                 'Solicitante',
                 d.repasse && d.repasse.tem_repasse
                     ? (d.repasse.nome_responsavel || p.solicitante) +
                       ' (repasse de ' +
                       (d.repasse.nome_repasse || '—') +
                       ')'
                     : p.solicitante,
             ],
             ['Valor TC', p.valor_tc ? 'R$ ' + p.valor_tc : ''],
             ['Valor AF', p.valor_af ? 'R$ ' + p.valor_af : ''],
             ['Valor Parcela', p.valor_parcela ? 'R$ ' + p.valor_parcela : ''], ['Prazo', p.prazo ? p.prazo + ' meses' : ''],
             ['Valor Liberado', p.valor_liberado ? 'R$ ' + p.valor_liberado : ''],
             ['Valor Saldo', (p.exibe_valor_saldo && p.valor_saldo) ? 'R$ ' + p.valor_saldo : '']].forEach(function (r) {
                if (!r[1]) return;
                htmlProp += '<div class="col-md-3"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-1">' + esc(r[1]) + '</p></div>';
            });
            htmlProp += '</div>';
            if (p.produto_exige_portado) {
                const rotPortLbl = p.rotulo_contrato_origem || 'Contrato de origem (portado)';
                htmlProp += '<div class="border rounded-2 p-3 mb-3 bg-light ficha-secao">';
                htmlProp += '<div class="fw-semibold small ficha-secao-titulo mb-2"><i class="bx bx-transfer-alt me-1"></i>' + esc(rotPortLbl) + '</div>';
                const portadosList = p.contratos_portados || [];
                if (!portadosList.length) {
                    htmlProp += '<p class="small text-muted mb-0">Nenhum contrato de origem informado.</p>';
                } else {
                portadosList.forEach(function (cp, j) {
                    htmlProp += '<div class="row g-2' + (j > 0 ? ' mt-2 pt-2 border-top' : '') + '">';
                    [
                        ['Banco (origem)', cp.banco],
                        ['Nº do contrato', cp.numero_contrato],
                        ['Valor parcela', cp.valor_parcela ? 'R$ ' + cp.valor_parcela : ''],
                        ['Valor AF', cp.valor_af ? 'R$ ' + cp.valor_af : ''],
                        ['Saldo devedor total', cp.valor_devedor_total ? 'R$ ' + cp.valor_devedor_total : ''],
                        ['Prazo total (meses)', cp.prazo_total !== '' && cp.prazo_total != null ? String(cp.prazo_total) : ''],
                        ['Prazo restante (meses)', cp.prazo_restante !== '' && cp.prazo_restante != null ? String(cp.prazo_restante) : ''],
                    ].forEach(function (r) {
                        if (r[1] === '' || r[1] === null || r[1] === undefined) return;
                        htmlProp += '<div class="col-md-3"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-1">' + esc(String(r[1])) + '</p></div>';
                    });
                    htmlProp += '</div>';
                });
                }
                htmlProp += '</div>';
            }
            const dbp = p.dados_bancarios_proposta;
            if (_crmBancarioTemDados(dbp)) {
                htmlProp += '<div class="border rounded-2 p-2 mb-3 bg-white"><div class="small text-muted mb-1">Dados bancários (proposta)</div><div class="row g-2">';
                [['Banco', dbp.banco], ['Agência', dbp.agencia], ['Conta', dbp.conta], ['Tipo', dbp.tipo_conta]].forEach(function (r) {
                    if (!r[1]) return;
                    htmlProp += '<div class="col-md-3"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-0 small">' + esc(r[1]) + '</p></div>';
                });
                htmlProp += '</div></div>';
            }
        });
        if (!temContratoFicha) {
            htmlProp += _crmHtmlFichaBlocoContrato();
        }
        if (!temContratoFicha && d.contrato) {
            const c = d.contrato;
            htmlProp += '<div class="row g-2">';
            [['Nº contrato', c.codigo], ['Etapa', c.etapa_operacional], ['Sub-status', c.sub_status_operacional],
             ['Tabela CMS', c.tabela_cms], ['Valor TC', c.valor_tc ? 'R$ ' + c.valor_tc : ''],
             ['Valor AF', c.valor_af ? 'R$ ' + c.valor_af : ''], ['Valor Parcela', c.valor_parcela ? 'R$ ' + c.valor_parcela : ''],
             ['Prazo', c.prazo ? c.prazo + ' meses' : ''], ['Valor Liberado', c.valor_liberado ? 'R$ ' + c.valor_liberado : ''],
             ['Valor Saldo', (c.exibe_valor_saldo && c.valor_saldo) ? 'R$ ' + c.valor_saldo : ''],
             ['Portabilidade', c.portabilidade ? 'Sim' : 'Não']].forEach(function (r) {
                if (!r[1]) return;
                htmlProp += '<div class="col-md-3"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-1">' + esc(r[1]) + '</p></div>';
            });
            if (c.link_formalizacao) {
                htmlProp += '<div class="col-12"><label class="form-label small text-muted mb-0">Link de Formalização</label><p class="mb-1"><a href="' + esc(c.link_formalizacao) + '" target="_blank" rel="noopener">' + esc(c.link_formalizacao) + '</a></p></div>';
            }
            htmlProp += '</div>';
        } else if (!temContratoFicha && mostrarCtrFicha && solCtr) {
            htmlProp += '<div class="row g-2">';
            [['Nº contrato (banco)', solCtr.numero_contrato_banco_pre], ['Link formalização', solCtr.link_formalizacao_pre]].forEach(function (r) {
                if (!r[1]) return;
                htmlProp += '<div class="col-md-6"><label class="form-label small text-muted mb-0">' + esc(r[0]) + '</label><p class="fw-semibold mb-1">' + esc(r[1]) + '</p></div>';
            });
            htmlProp += '</div>';
        }
        document.getElementById('fichaConteudoProposta').innerHTML = htmlProp || '<p class="text-muted">Sem proposta/contrato registrado.</p>';

        // Validação [6]: a linha do tempo foi removida do modal de ficha.
        // O histórico fica disponível exclusivamente no modal de Auditoria
        // (botão de histórico na coluna Ações, consumindo api/v2/auditoria-fluxo/).
    }

    /* ══════════════════════════════
       MODAL EVOLUIR
    ══════════════════════════════ */
    function abrirModalEvoluir(tipo, id) {
        document.getElementById('evoluirTipo').value = tipo;
        document.getElementById('evoluirId').value = id;
        document.getElementById('evoluirGrupoEtapa').classList.remove('d-none');
        const _lblSub0 = document.querySelector('#evoluirGrupoSub label.form-label');
        if (_lblSub0) {
            _lblSub0.innerHTML = 'Status <span class="text-danger">*</span>';
        }
        document.getElementById('evoluirEtapa').innerHTML = '<option value="">Carregando...</option>';
        document.getElementById('evoluirSub').innerHTML = '<option value="">Selecione o status...</option>';
        document.getElementById('evoluirLink').value = '';
        document.getElementById('evoluirObs').value = '';
        document.getElementById('evoluirAlerta').classList.add('d-none');
        _toggleExtraFields(null);
        document.getElementById('evoluirGrupoSub').classList.add('d-none');
        _transicoes = [];
        _modoLivreEvoluir = false;
        _pagoTcModal = null;
        _pagoCmsModal = null;
        _refinPortDefaults = null;
        _evoluirPendenteRefinPort = null;
        _evoluirPendenteSaldoPort = null;
        _valorSaldoPendente = null;

        new bootstrap.Modal(document.getElementById('modalEvoluir')).show();

        getJson(base + 'transicoes-disponiveis/?tipo=' + encodeURIComponent(tipo) + '&id=' + encodeURIComponent(id)).then(function (d) {
            if (!d.ok) {
                document.getElementById('evoluirEtapa').innerHTML = '<option value="">Erro ao carregar transições</option>';
                return;
            }
            _transicoes = d.transicoes || [];
            _modoLivreEvoluir = !!(d.modo_livre && tipo === 'contrato');
            _pagoTcModal = d.pago_tc_modal || null;
            _pagoCmsModal = d.pago_cms_modal || null;
            _refinPortDefaults = d.refin_port_defaults || null;
            const alertaLivre = document.getElementById('evoluirAlerta');
            if (_modoLivreEvoluir && alertaLivre) {
                alertaLivre.className = 'alert alert-info small py-2 mb-2';
                alertaLivre.textContent =
                    'Contrato gerado: você pode ir para qualquer etapa/status. Ao escolher Pagamento, o vídeo de conscientização deve estar anexado (se exigido).';
                alertaLivre.classList.remove('d-none');
            }
            // Guardar solicitacao_digitacao_id caso seja solicitacao_dig
            if (d.solicitacao_digitacao_id) {
                document.getElementById('evoluirId').setAttribute('data-sol-id', d.solicitacao_digitacao_id);
            }
            _populateEtapas();
            _syncEvoluirEnviosVendedorWrap();
        });
    }

    function _populateEtapas() {
        const sel = document.getElementById('evoluirEtapa');
        const grupoEtapa = document.getElementById('evoluirGrupoEtapa');
        const grupoSub = document.getElementById('evoluirGrupoSub');
        const lblSub = grupoSub ? grupoSub.querySelector('label.form-label') : null;
        const tipo = document.getElementById('evoluirTipo').value;
        /* Pré-contrato: uma lista só (Tabulação) com Gerar / Pendenciar / Cancelar visíveis de imediato */
        const preSol =
            tipo === 'solicitacao_dig' &&
            _transicoes.length &&
            _transicoes.every(function (t) {
                return String(t.etapa || '').indexOf('PRE_SOL_') === 0;
            });
        if (preSol) {
            grupoEtapa.classList.add('d-none');
            grupoSub.classList.remove('d-none');
            if (lblSub) {
                lblSub.innerHTML = 'Tabulação <span class="text-danger">*</span>';
            }
            const selSub = document.getElementById('evoluirSub');
            selSub.innerHTML = '<option value="">Selecione Gerar, Pendenciar ou Cancelar...</option>';
            const sorted = _transicoes.slice().sort(function (a, b) {
                const oa = (a.ordem != null && a.ordem !== undefined) ? a.ordem : 9999;
                const ob = (b.ordem != null && b.ordem !== undefined) ? b.ordem : 9999;
                if (oa !== ob) return oa - ob;
                return (a.etapa_label || '').localeCompare(b.etapa_label || '');
            });
            sorted.forEach(function (t) {
                const opt = document.createElement('option');
                opt.value = t.acao;
                opt.textContent = t.etapa_label || t.sub_label;
                opt.setAttribute('data-requer', t.requer_extra || '');
                opt.setAttribute('data-exige-saldo', t.exige_valor_saldo_port ? '1' : '0');
                selSub.appendChild(opt);
            });
            _toggleExtraFields(null);
            return;
        }

        grupoEtapa.classList.remove('d-none');
        if (lblSub) {
            lblSub.innerHTML = 'Status <span class="text-danger">*</span>';
        }

        /* Agrupa por etapa; ordem = menor índice vindo da API (pipeline estável) */
        const porEtapa = new Map();
        _transicoes.forEach(function (t) {
            const ord = (t.ordem != null && t.ordem !== undefined) ? t.ordem : 9999;
            if (!porEtapa.has(t.etapa)) {
                porEtapa.set(t.etapa, { etapa: t.etapa, label: t.etapa_label, ordem: ord });
            } else {
                const cur = porEtapa.get(t.etapa);
                if (ord < cur.ordem) cur.ordem = ord;
            }
        });
        const etapas = Array.from(porEtapa.values());
        etapas.sort(function (a, b) {
            if (a.ordem !== b.ordem) return a.ordem - b.ordem;
            return (a.label || '').localeCompare(b.label || '');
        });
        if (etapas.length === 0) {
            sel.innerHTML = '<option value="">Nenhuma transição disponível</option>';
            grupoSub.classList.add('d-none');
            return;
        }
        sel.innerHTML = '<option value="">Selecione a etapa...</option>';
        etapas.forEach(function (e) {
            const opt = document.createElement('option');
            opt.value = e.etapa;
            opt.textContent = e.label;
            sel.appendChild(opt);
        });
        /* Se só há uma etapa, pré-seleciona */
        if (etapas.length === 1) {
            sel.value = etapas[0].etapa;
            _onEtapaChange();
        }
    }

    document.getElementById('evoluirEtapa').addEventListener('change', _onEtapaChange);

    function _onEtapaChange() {
        const etapa = document.getElementById('evoluirEtapa').value;
        const grupoSub = document.getElementById('evoluirGrupoSub');
        const selSub = document.getElementById('evoluirSub');
        _toggleExtraFields(null);

        if (!etapa) { grupoSub.classList.add('d-none'); return; }

        let subs = _transicoes.filter(t => t.etapa === etapa);
        subs.sort(function (a, b) {
            const oa = (a.ordem != null && a.ordem !== undefined) ? a.ordem : 9999;
            const ob = (b.ordem != null && b.ordem !== undefined) ? b.ordem : 9999;
            if (oa !== ob) return oa - ob;
            return (a.sub_label || '').localeCompare(b.sub_label || '');
        });
        selSub.innerHTML = '<option value="">Selecione o status...</option>';
        subs.forEach(function (t) {
            const opt = document.createElement('option');
            if (_modoLivreEvoluir) {
                opt.value = _valorOptionTransicaoModoLivre(t);
                opt.setAttribute('data-acao', t.acao || 'operacional_definir_status');
            } else {
                opt.value = t.acao;
            }
            opt.textContent = t.sub_label;
            opt.setAttribute('data-requer', t.requer_extra || '');
            opt.setAttribute('data-exige-saldo', t.exige_valor_saldo_port ? '1' : '0');
            selSub.appendChild(opt);
        });
        grupoSub.classList.remove('d-none');

        // Pré-seleciona se só há um
        if (subs.length === 1) {
            selSub.value = _modoLivreEvoluir
                ? _valorOptionTransicaoModoLivre(subs[0])
                : subs[0].acao;
            _onSubChange();
        }
    }

    document.getElementById('evoluirSub').addEventListener('change', _onSubChange);

    function _onSubChange() {
        const selSub = document.getElementById('evoluirSub');
        const opt = selSub.options[selSub.selectedIndex];
        let acao = selSub.value;
        if (_modoLivreEvoluir) {
            acao = (opt && opt.getAttribute('data-acao')) || 'operacional_definir_status';
        }
        const requer = _requerExtraEvoluir(opt, selSub.value, document.getElementById('evoluirEtapa').value);
        _toggleExtraFields(requer, acao, opt);
        _syncEvoluirEnviosVendedorWrap();
    }

    function _destinoEvolucaoPagoCliente(acao, etapaVal, subVal) {
        if (acao === 'operacional_pago_cliente') {
            return true;
        }
        return (
            acao === 'operacional_definir_status'
            && String(etapaVal || '') === 'PAGAMENTO'
            && String(subVal || '') === 'PG_PAGO_CLIENTE'
        );
    }

    function _exigeValorSaldoPortEvoluir(acao, opt, etapaVal, subVal) {
        if (!_destinoEvolucaoPagoCliente(acao, etapaVal, subVal)) {
            return false;
        }
        if (opt && opt.getAttribute('data-exige-saldo') === '1') {
            return true;
        }
        return !!(_refinPortDefaults && _refinPortDefaults.exige_valor_saldo_port);
    }

    /** Port + Refin: modal REFIN (requer_extra ou refin_port_defaults). */
    function _exigeFluxoRefinPortPagoCliente(acao, opt, etapaVal, subVal) {
        if (!_destinoEvolucaoPagoCliente(acao, etapaVal, subVal)) {
            return false;
        }
        const requer = opt ? (opt.getAttribute('data-requer') || '') : '';
        if (requer === 'refin_port') {
            return true;
        }
        return !!(
            _refinPortDefaults
            && _refinPortDefaults.port_mais_refin
            && !_refinPortDefaults.refin_ja_existe
            && !_refinPortDefaults.erro_config
        );
    }

    function _carregarRefinPortDefaultsSeNecessario(contratoId, cb) {
        if (_refinPortDefaults !== null && _refinPortDefaults !== undefined) {
            cb();
            return;
        }
        getJson(base + 'contrato/' + encodeURIComponent(contratoId) + '/refin-port-defaults/')
            .then(function (d) {
                if (d && d.ok && d.port_mais_refin) {
                    _refinPortDefaults = d;
                }
                cb();
            })
            .catch(function () {
                cb();
            });
    }

    function _montarPayloadPagoClienteEvoluir(pend, refinPort) {
        const payload = {
            tipo: pend.tipo,
            id: pend.id,
            observacao: pend.observacao || '',
        };
        if (refinPort) {
            payload.refin_port = refinPort;
            if (refinPort.valor_saldo && !payload.valor_saldo) {
                payload.valor_saldo = refinPort.valor_saldo;
            }
        }
        if (_valorSaldoPendente) {
            payload.valor_saldo = _valorSaldoPendente;
        }
        const subDest = String(pend.sub || '').trim();
        const etapaDest = String(pend.etapa || '').trim();
        if (
            subDest === 'PG_PAGO_CLIENTE'
            || (
                pend.acao === 'operacional_definir_status'
                && etapaDest
                && subDest
            )
        ) {
            payload.acao = 'operacional_definir_status';
            payload.etapa = etapaDest || 'PAGAMENTO';
            payload.sub = subDest || 'PG_PAGO_CLIENTE';
        } else {
            payload.acao = 'operacional_pago_cliente';
        }
        return payload;
    }

    function _abrirModalValorSaldoPort(tipo, id, observacao, needsRefin, evoluirCtx) {
        evoluirCtx = evoluirCtx || {};
        _evoluirPendenteSaldoPort = {
            tipo: tipo,
            id: id,
            observacao: observacao || '',
            needsRefin: !!needsRefin,
            acao: evoluirCtx.acao || 'operacional_pago_cliente',
            etapa: evoluirCtx.etapa || '',
            sub: evoluirCtx.sub || '',
        };
        _valorSaldoPendente = null;
        const inp = document.getElementById('valorSaldoPortInput');
        if (inp) {
            inp.value = '';
        }
        const al = document.getElementById('valorSaldoPortAlerta');
        if (al) {
            al.textContent = '';
            al.classList.add('d-none');
        }
        const modalEv = bootstrap.Modal.getInstance(document.getElementById('modalEvoluir'));
        if (modalEv) {
            modalEv.hide();
        }
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalValorSaldoPort')).show();
    }

    function _labelPapelPctc(p) {
        const map = { responsável: 'Responsável', repasse: 'Repasse', vendedor: 'Vendedor' };
        return map[p] || esc(p);
    }

    /** UI do bloco “venda associada a loja?” (Pago TC). */
    function _atualizarUiPctcAssocLoja() {
        const m = _pagoTcModal || {};
        const lojas = m.lojas_elegiveis || [];
        const rSim = document.getElementById('evoluirPctcAssocLojaSim');
        const wrapSel = document.getElementById('evoluirPctcLojaSelectWrap');
        const altSem = document.getElementById('evoluirPctcLojaSemOpcoes');
        const sim = !!(rSim && rSim.checked);
        if (altSem) {
            if (sim && lojas.length === 0) altSem.classList.remove('d-none');
            else altSem.classList.add('d-none');
        }
        if (wrapSel) {
            if (sim && lojas.length > 0) wrapSel.classList.remove('d-none');
            else wrapSel.classList.add('d-none');
        }
        _atualizarBloqueioVideoPctc();
    }

    /** Lê escolha de loja para o JSON registermoney (sempre envia as chaves). */
    function _pctcPayloadLojaRm() {
        const rSim = document.getElementById('evoluirPctcAssocLojaSim');
        const assoc = !!(rSim && rSim.checked);
        const sel = document.getElementById('evoluirPctcLojaId');
        let lid = null;
        if (assoc && sel && sel.value) {
            const n = parseInt(sel.value, 10);
            lid = isFinite(n) && n > 0 ? n : null;
        }
        return { venda_associada_loja: assoc, loja_id: lid };
    }

    /** Monta o JSON registermoney completo para upload de comprovante TC (1º RegisterMoney). */
    function _buildRegistermoneyJsonComprovante(opts) {
        opts = opts || {};
        const gv = function (id) {
            const el = document.getElementById(id);
            return el ? String(el.value || '').trim() : '';
        };
        const mTc = _pagoTcModal || {};
        const snapCms = function (k) {
            const v = mTc[k];
            if (v === undefined || v === null) return '';
            return String(v).trim();
        };
        const lp = _pctcPayloadLojaRm();
        const fc = document.getElementById('evoluirPctcFlagCms');
        const selC = document.getElementById('evoluirPctcClassificador');
        const fm3 = document.getElementById('evoluirPctcForcarM3');
        const zerando = _estaZerandoTcModal();
        let veNum = _parseNumFlex(gv('evoluirPctcValorEst'));
        // Fallback ao TC do servidor só no upload de comprovante (não ao salvar/zerar no modal).
        if ((!isFinite(veNum) || veNum <= 0) && opts.permitirFallbackTc !== false && !zerando) {
            veNum = Number(_tcCompValorTc) || 0;
        }
        let veNorm;
        if (zerando) {
            veNorm = '0';
        } else if (isFinite(veNum) && veNum > 0) {
            veNorm = String(veNum);
        } else {
            veNorm = gv('evoluirPctcValorEst');
        }
        const afNum = _parseNumFlex(gv('evoluirPctcAf'));
        const afNorm =
            isFinite(afNum) && afNum > 0 ? String(afNum) : gv('evoluirPctcAf');
        const payload = {
            valor_est: veNorm,
            valor_est_tc: veNorm,
            af: afNorm,
            valor_cms_recebido: snapCms('valor_cms_recebido'),
            valor_cms_repassado: snapCms('valor_cms_repassado'),
            valor_cms_plastico: snapCms('valor_cms_plastico'),
            flag_cms_pago: fc ? !!fc.checked : false,
            classificacao_valor_id: selC && selC.value ? parseInt(selC.value, 10) : null,
            classificador_id: selC && selC.value ? parseInt(selC.value, 10) : null,
            venda_associada_loja: lp.venda_associada_loja,
            loja_id: lp.loja_id,
            forcar_m3: fm3 ? !!fm3.checked : false,
        };
        return payload;
    }

    /** Payload dos campos superiores do modal Pago TC (salvar dados / comprovante). */
    function _buildPayloadSalvarDadosPagoTc() {
        const cid = _contratoIdPagoTc();
        const rm = _buildRegistermoneyJsonComprovante({ permitirFallbackTc: false });
        const obs = document.getElementById('evoluirObs');
        return {
            contrato_id: cid ? parseInt(cid, 10) : 0,
            observacao: obs ? String(obs.value || '').trim() : '',
            valor_est_tc: rm.valor_est,
            valor_est: rm.valor_est,
            af: rm.af,
            valor_cms_recebido: rm.valor_cms_recebido,
            valor_cms_repassado: rm.valor_cms_repassado,
            valor_cms_plastico: rm.valor_cms_plastico,
            flag_cms_pago: rm.flag_cms_pago,
            classificacao_valor_id: rm.classificacao_valor_id,
            classificador_id: rm.classificador_id,
            venda_associada_loja: rm.venda_associada_loja,
            loja_id: rm.loja_id,
            forcar_m3: rm.forcar_m3,
        };
    }

    /** Valida campos superiores do modal (TC, classificador, loja). Retorna mensagem ou null. */
    function _tcModalInputNum() {
        const ve = (document.getElementById('evoluirPctcValorEst') || {}).value;
        return _parseNumFlex(ve);
    }

    /** True quando o input está vazio/0 mas o snapshot do servidor ainda tinha TC > 0. */
    function _estaZerandoTcModal() {
        const veNum = _tcModalInputNum();
        const tcOriginal = Number(_tcCompValorTc) || 0;
        return (!isFinite(veNum) || veNum <= 0) && tcOriginal > 0;
    }

    function _atualizarHintPagoTcZerado(semTcInput) {
        const hint = document.getElementById('evoluirPagoTcHint');
        if (!hint) return;
        if (semTcInput && _estaZerandoTcModal()) {
            hint.textContent = 'TC zerado — comprovante não necessário. Confirme para registrar.';
            return;
        }
        if (semTcInput && (Number(_tcCompValorTc) || 0) <= 0) {
            hint.textContent = 'Sem TC — comprovante não necessário. Confirme para registrar.';
            return;
        }
        const m = _pagoTcModal || {};
        if (m.tabela_cms_titulo) {
            hint.textContent = 'Tabela (snapshot): ' + m.tabela_cms_titulo;
        } else {
            hint.textContent = 'Valores sugeridos a partir do snapshot da tabela na contratação.';
        }
    }

    function _validarDadosPagoTcModal() {
        const cl = document.getElementById('evoluirPctcClassificador');
        if (!cl || !cl.value) {
            return 'Selecione o classificador de valor.';
        }
        const lojaChk = _pctcPayloadLojaRm();
        const lojasM = (_pagoTcModal || {}).lojas_elegiveis || [];
        if (lojaChk.venda_associada_loja && lojasM.length === 0) {
            return 'Marque “Não” em venda associada a loja ou cadastre lojas nos funcionários.';
        }
        if (lojaChk.venda_associada_loja && !lojaChk.loja_id) {
            return 'Selecione a loja da venda.';
        }
        return null;
    }

    function _salvarDadosPagoTcModal() {
        const cid = _contratoIdPagoTc();
        if (!cid) {
            showToast('Contrato não identificado.', 'danger');
            return;
        }
        const errVal = _validarDadosPagoTcModal();
        if (errVal) {
            showToast(errVal, 'warning');
            return;
        }
        const btn = document.getElementById('evoluirPctcSalvarDados');
        if (btn) btn.disabled = true;
        postJson(base + 'salvar-dados-pago-tc-modal/', _buildPayloadSalvarDadosPagoTc())
            .then(function (r) {
                if (btn) btn.disabled = false;
                _atualizarBloqueioVideoPctc();
                if (!r || !r.ok) {
                    showToast((r && r.erro) || 'Erro ao salvar dados do modal.', 'danger');
                    return;
                }
                const vTc = parseFloat(String(r.valor_tc || r.valor_est_tc || '').replace(',', '.'));
                if (r.tc_zerado || (isFinite(vTc) && vTc <= 0)) {
                    _tcCompValorTc = 0;
                    _tcCompSomaServidor = 0;
                    if (_pagoTcModal) _pagoTcModal.valor_est_tc = '0';
                    const inpTc = document.getElementById('evoluirPctcValorEst');
                    if (inpTc) inpTc.value = '0';
                    _atualizarBadgeTc(0, 0);
                    _syncVisibilidadeBlocoBoletosTc();
                    showToast(
                        'Valor TC zerado. Comprovante não é necessário — confirme a evolução.',
                        'success'
                    );
                } else if (isFinite(vTc) && vTc > 0) {
                    _tcCompValorTc = vTc;
                    if (_pagoTcModal) _pagoTcModal.valor_est_tc = String(vTc);
                    const inpTc = document.getElementById('evoluirPctcValorEst');
                    if (inpTc) inpTc.value = String(vTc);
                    const extra = document.getElementById('evoluirTcCompValor');
                    const extraN = extra ? _parseValorComprovanteCampo(extra.value) : 0;
                    _atualizarBadgeTc(_tcCompSomaServidor + (extraN > 0 ? extraN : 0), _tcCompValorTc);
                    showToast('Dados do Pago TC salvos.', 'success');
                } else {
                    showToast('Dados do Pago TC salvos.', 'success');
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                _atualizarBloqueioVideoPctc();
                showToast('Erro de comunicação ao salvar dados.', 'danger');
            });
    }

    /** Valida campos do modal Pago TC antes de enviar comprovante (TC > 0). Retorna mensagem ou null. */
    function _validarRegistermoneyComprovante() {
        const ve = (document.getElementById('evoluirPctcValorEst') || {}).value;
        const semTc = !isFinite(_parseNumFlex(ve)) || _parseNumFlex(ve) <= 0;
        if (semTc) return null;
        const cl = document.getElementById('evoluirPctcClassificador');
        if (!cl || !cl.value) {
            return 'Selecione o classificador de valor antes de enviar o comprovante.';
        }
        const lojaChk = _pctcPayloadLojaRm();
        const lojasM = (_pagoTcModal || {}).lojas_elegiveis || [];
        if (lojaChk.venda_associada_loja && lojasM.length === 0) {
            return 'Marque “Não” em venda associada a loja ou cadastre lojas nos funcionários.';
        }
        if (lojaChk.venda_associada_loja && !lojaChk.loja_id) {
            return 'Selecione a loja da venda antes de enviar o comprovante.';
        }
        if (!ve || !String(ve).trim()) {
            return 'Informe o valor TC antes de enviar o comprovante.';
        }
        return null;
    }

    function _parseNumFlex(s) {
        if (s == null || s === '') return NaN;
        let t = String(s).trim().replace(/\s/g, '');
        if (t.indexOf(',') >= 0 && t.indexOf('.') < 0) {
            t = t.replace(',', '.');
        } else if (t.indexOf('.') >= 0 && t.indexOf(',') >= 0) {
            t = t.replace(/\./g, '').replace(',', '.');
        }
        const n = parseFloat(t);
        return isFinite(n) ? n : NaN;
    }

    function _fmtBrlPctc(n) {
        if (!isFinite(n)) return '—';
        return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function _atualizarRankingPctc() {
        const wrap = document.getElementById('evoluirPctcRankingLinhas');
        if (!wrap) return;
        const m = _pagoTcModal || {};
        const dest = m.destinatarios || [];
        const sel = document.getElementById('evoluirPctcClassificador');
        const inp = document.getElementById('evoluirPctcValorEst');
        const opt = sel && sel.selectedIndex >= 0 ? sel.options[sel.selectedIndex] : null;
        const pctRaw = opt ? opt.getAttribute('data-percentual') : '';
        const pct = parseFloat(String(pctRaw || '').replace(',', '.'));
        const tc = _parseNumFlex(inp ? inp.value : '');
        const temRep = !!m.tem_repasse;

        if (!dest.length) {
            wrap.innerHTML = '<span class="text-muted small">Nenhum destinatário informado para prévia.</span>';
            return;
        }
        if (!isFinite(tc) || tc <= 0) {
            let html = '';
            dest.forEach(function (d) {
                html +=
                    '<div class="text-muted small">Ranking SIAPE — ' +
                    esc(d.nome) +
                    ' (' +
                    _labelPapelPctc(d.papel) +
                    '): —</div>';
            });
            wrap.innerHTML =
                html ||
                '<span class="text-muted small">Informe TC e classificador para prévia.</span>';
            return;
        }
        const fatia = temRep ? tc / 2 : tc;
        let html = '';
        dest.forEach(function (d) {
            html +=
                '<div class="small">Ranking SIAPE — ' +
                esc(d.nome) +
                ' (' +
                _labelPapelPctc(d.papel) +
                '): ' +
                _fmtBrlPctc(fatia) +
                '</div>';
            if (isFinite(pct)) {
                html +=
                    '<div class="small text-muted">Bonificação estimada — ' +
                    esc(d.nome) +
                    ': ' +
                    _fmtBrlPctc(fatia * (pct / 100)) +
                    ' (' +
                    pct +
                    '% do classificador)</div>';
            }
        });
        wrap.innerHTML = html;
    }

    function _atualizarBloqueioVideoPctc() {
        const m = _pagoTcModal || {};
        const alertEl = document.getElementById('evoluirPctcVideoAlert');
        const btn = document.getElementById('btnConfirmarEvolucao');
        const bloquear = m && _pagoTcModalBloqueiaPorVideo(m);
        const rSim = document.getElementById('evoluirPctcAssocLojaSim');
        const lojas = m.lojas_elegiveis || [];
        const bloquearLoja = !!(rSim && rSim.checked && lojas.length === 0);
        if (alertEl) {
            if (bloquear) alertEl.classList.remove('d-none');
            else alertEl.classList.add('d-none');
        }
        if (btn) btn.disabled = !!(bloquear || bloquearLoja);
        const btnSalvarDados = document.getElementById('evoluirPctcSalvarDados');
        if (btnSalvarDados) btnSalvarDados.disabled = !!(bloquear || bloquearLoja);
        const btnComp = document.getElementById('evoluirTcCompEnviar');
        if (btnComp) btnComp.disabled = !!bloquearLoja;
    }

    /** Bloco Adicionar Boletos: oculto quando Valor TC do modal é zero ou vazio. */
    function _syncVisibilidadeBlocoBoletosTc() {
        const gr = document.getElementById('evoluirGrupoPagoTc');
        const blocoComp = document.getElementById('evoluirPctcBlocoComprovantes');
        if (!gr || gr.classList.contains('d-none') || !blocoComp) return;
        const inp = document.getElementById('evoluirPctcValorEst');
        const valorTcNum = inp ? _parseNumFlex(inp.value) : NaN;
        const semTcInput = !isFinite(valorTcNum) || valorTcNum <= 0;
        if (semTcInput) {
            blocoComp.classList.add('d-none');
        } else {
            blocoComp.classList.remove('d-none');
        }
        _atualizarHintPagoTcZerado(semTcInput);
    }

    function _preencherPagoTcModal() {
        const m = _pagoTcModal || {};
        const valorTcNum = _parseNumFlex(m.valor_est_tc);
        const semTc = !isFinite(valorTcNum) || valorTcNum <= 0;
        function setv(id, v) {
            const el = document.getElementById(id);
            if (el) el.value = (v !== undefined && v !== null && v !== '') ? String(v) : '';
        }
        setv('evoluirPctcValorEst', m.valor_est_tc);
        setv('evoluirPctcAf', m.af);
        const chk = document.getElementById('evoluirPctcFlagCms');
        if (chk) chk.checked = !!m.flag_cms_pago;
        const selCl = document.getElementById('evoluirPctcClassificador');
        if (selCl) {
            selCl.innerHTML = '<option value="">Selecione...</option>';
            (m.classificadores || m.classificacoes || []).forEach(function (c) {
                const o = document.createElement('option');
                o.value = String(c.id);
                const pctStr = c.percentual_num != null && c.percentual_num !== '' ? String(c.percentual_num) : String(c.percentual || '0');
                o.setAttribute('data-percentual', pctStr);
                o.textContent =
                    (c.titulo || '') +
                    (c.percentual !== undefined && c.percentual !== null && c.percentual !== '' ? ' (' + c.percentual + '%)' : '');
                selCl.appendChild(o);
            });
            if (m.classificacao_default_id != null && m.classificacao_default_id !== '') {
                selCl.value = String(m.classificacao_default_id);
            }
        }
        _crmPreencherRepassePagoTc(m);
        const destWrap = document.getElementById('evoluirPctcDestinatariosWrap');
        const destUl = document.getElementById('evoluirPctcDestinatarios');
        const lista = m.destinatarios || [];
        if (destWrap && destUl) {
            if (lista.length) {
                destUl.innerHTML = lista
                    .map(function (d) {
                        return (
                            '<li><span class="text-muted">' +
                            esc(_labelPapelPctc(d.papel)) +
                            ':</span> ' +
                            esc(d.nome || '—') +
                            '</li>'
                        );
                    })
                    .join('');
                destWrap.classList.remove('d-none');
            } else {
                destUl.innerHTML = '';
                destWrap.classList.add('d-none');
            }
        }
        const formHint = document.getElementById('evoluirPctcRankingFormula');
        if (formHint) {
            if (m.ranking_formula_hint) {
                formHint.textContent = m.ranking_formula_hint;
                formHint.classList.remove('d-none');
            } else {
                formHint.textContent = '';
                formHint.classList.add('d-none');
            }
        }
        const lojas = m.lojas_elegiveis || [];
        const selLj = document.getElementById('evoluirPctcLojaId');
        const rNao = document.getElementById('evoluirPctcAssocLojaNao');
        const rSim = document.getElementById('evoluirPctcAssocLojaSim');
        if (m.venda_associada_loja_default) {
            if (rSim) rSim.checked = true;
            if (rNao) rNao.checked = false;
        } else {
            if (rNao) rNao.checked = true;
            if (rSim) rSim.checked = false;
        }
        if (selLj) {
            selLj.innerHTML = '<option value="">Selecione...</option>';
            lojas.forEach(function (L) {
                const o = document.createElement('option');
                o.value = String(L.id);
                o.textContent = L.nome || ('Loja #' + L.id);
                selLj.appendChild(o);
            });
            if (m.loja_id_default != null && m.loja_id_default !== '') {
                selLj.value = String(m.loja_id_default);
            }
        }
        _atualizarUiPctcAssocLoja();
        const hint = document.getElementById('evoluirPagoTcHint');
        if (hint) {
            if (m.tabela_cms_titulo) {
                hint.textContent = 'Tabela (snapshot): ' + m.tabela_cms_titulo;
            } else {
                hint.textContent = 'Valores sugeridos a partir do snapshot da tabela na contratação.';
            }
        }
        _atualizarRankingPctc();
        _atualizarBloqueioVideoPctc();
        const vCompLimpar = document.getElementById('evoluirTcCompValor');
        if (vCompLimpar) vCompLimpar.value = '';
        const aCompLimpar = document.getElementById('evoluirTcCompArquivo');
        if (aCompLimpar) aCompLimpar.value = '';
        const vTcIni = Number(m.valor_est_tc);
        _tcCompValorTc = isFinite(vTcIni) ? vTcIni : 0;
        _tcCompSomaServidor = 0;
        _atualizarBadgeTc(0, _tcCompValorTc);
        _carregarComprovantesTc();
        _syncVisibilidadeBlocoBoletosTc();
    }

    /* ── Pago TC: upload e lista de comprovantes (parcial/total) ── */
    function _formatarBRL(v) {
        try {
            const n = Number(v);
            if (!isFinite(n)) return 'R$ 0,00';
            return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch (e) {
            return 'R$ 0,00';
        }
    }

    /**
     * Máscara tipo caixa: só dígitos = centavos (1 → 0,01; 12 → 0,12; 123 → 1,23; 123456 → 1.234,56).
     * Reconstrói a exibição a partir dos dígitos extraídos do campo.
     */
    function _formatarValorComprovanteDigitosCentavos(digitsRaw) {
        const d = String(digitsRaw || '').replace(/\D/g, '');
        if (!d) return '';
        let cent = parseInt(d, 10);
        if (!isFinite(cent) || cent < 0) return '';
        if (cent > 999999999999) cent = 999999999999;
        const reais = cent / 100;
        return reais.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    /** Valor em reais a partir do conteúdo do campo (mesma regra: só dígitos = centavos). */
    function _parseValorComprovanteCampo(raw) {
        const d = String(raw || '').replace(/\D/g, '');
        if (!d) return 0;
        const cent = parseInt(d, 10);
        if (!isFinite(cent) || cent < 0) return 0;
        return cent / 100;
    }

    function _contratoIdPagoTc() {
        const m = _pagoTcModal || {};
        if (m.contrato_id) return String(m.contrato_id);
        const tipo = (document.getElementById('evoluirTipo') || {}).value;
        const id = (document.getElementById('evoluirId') || {}).value;
        if (tipo === 'contrato' || tipo === 'contrato_exec' || tipo === 'contrato_execucao') {
            return id ? String(id) : '';
        }
        return '';
    }

    function _atualizarBadgeTc(soma, valorTc) {
        const s = Number(soma || 0);
        const t = Number(valorTc || 0);
        const badge = document.getElementById('evoluirTcBadgeStatus');
        const saldoEl = document.getElementById('evoluirTcSaldo');
        const somaEl = document.getElementById('evoluirTcSomaAcumulada');
        const tcEl = document.getElementById('evoluirTcValorTc');
        if (somaEl) somaEl.textContent = _formatarBRL(s);
        if (tcEl) tcEl.textContent = _formatarBRL(t);
        if (saldoEl) saldoEl.textContent = _formatarBRL(Math.max(0, t - s));
        if (!badge) return;
        if (t <= 0) {
            badge.textContent = 'Sem TC';
            badge.className = 'badge rounded-pill bg-secondary';
        } else if (s <= 0) {
            badge.textContent = 'Aguardando Pagamento';
            badge.className = 'badge rounded-pill bg-secondary';
        } else if (s < t) {
            badge.textContent = 'Pago TC Parcial';
            badge.className = 'badge rounded-pill bg-warning text-dark';
        } else {
            badge.textContent = 'Pago TC Total';
            badge.className = 'badge rounded-pill bg-success';
        }
    }

    function _renderComprovantesTc(lista) {
        const tbody = document.getElementById('evoluirTcCompLista');
        if (!tbody) return;
        if (!lista || !lista.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-muted small text-center py-2">Nenhum comprovante registrado.</td></tr>';
            return;
        }
        tbody.innerHTML = lista.map(function (c) {
            const dt = c.criado_em ? new Date(c.criado_em).toLocaleString('pt-BR') : '—';
            const arq = c.arquivo_url
                ? '<a href="' + c.arquivo_url + '" target="_blank" rel="noopener">Ver</a>'
                : '<span class="text-muted">—</span>';
            const btnExc =
                '<button type="button" class="btn btn-link btn-sm text-danger p-0 ms-1 js-excluir-comp-tc" ' +
                'data-comp-id="' + esc(String(c.id || '')) + '" title="Excluir comprovante">' +
                '<i class="bx bx-trash"></i></button>';
            return '<tr>' +
                '<td class="small">' + esc(dt) + '</td>' +
                '<td class="small">' + _formatarBRL(c.valor) + '</td>' +
                '<td class="small">' + esc(c.criado_por || '—') + '</td>' +
                '<td class="small">' + arq + '</td>' +
                '<td class="small text-end">' + btnExc + '</td>' +
                '</tr>';
        }).join('');
    }

    function _excluirComprovanteTc(compId) {
        const cid = _contratoIdPagoTc();
        if (!cid || !compId) {
            showToast('Dados insuficientes para excluir o comprovante.', 'warning');
            return;
        }
        if (!window.confirm('Excluir este comprovante TC?')) return;
        postJson(base + 'comprovante-tc/excluir/', {
            contrato_id: parseInt(cid, 10),
            comprovante_id: parseInt(compId, 10),
        })
            .then(function (j) {
                if (!j || !j.ok) {
                    showToast((j && j.erro) || 'Falha ao excluir comprovante.', 'danger');
                    return;
                }
                const soma = parseFloat(String(j.soma_acumulada || '0').replace(',', '.'));
                _tcCompSomaServidor = isFinite(soma) ? soma : 0;
                const vtc = parseFloat(String(j.valor_tc || '').replace(',', '.'));
                if (isFinite(vtc)) _tcCompValorTc = vtc;
                _renderComprovantesTc(j.comprovantes || []);
                _atualizarBadgeTc(_tcCompSomaServidor, _tcCompValorTc);
                _syncVisibilidadeBlocoBoletosTc();
                showToast('Comprovante excluído.', 'success');
            })
            .catch(function () {
                showToast('Erro de comunicação ao excluir comprovante.', 'danger');
            });
    }

    function _renderEnviosVendedorListaHtml(lista, ulId, emptyId, wrapId) {
        const ul = document.getElementById(ulId);
        const empty = document.getElementById(emptyId);
        const wrap = wrapId ? document.getElementById(wrapId) : null;
        if (!ul || !empty) return;
        if (wrap) wrap.classList.remove('d-none');
        if (!lista || !lista.length) {
            empty.classList.remove('d-none');
            ul.classList.add('d-none');
            ul.innerHTML = '';
            if (wrap && wrapId === 'fichaBlkEnviosVendedor') wrap.classList.add('d-none');
            return;
        }
        empty.classList.add('d-none');
        ul.classList.remove('d-none');
        ul.innerHTML = lista.map(function (ev) {
            const dt = ev.criado_em ? new Date(ev.criado_em).toLocaleString('pt-BR') : '—';
            const nome = ev.enviado_por_nome || ev.enviado_por || '—';
            const arq = ev.arquivo_url
                ? '<a href="' + ev.arquivo_url + '" target="_blank" rel="noopener">Ver</a>'
                : '<span class="text-muted">—</span>';
            return '<li class="list-group-item px-0 py-1 d-flex justify-content-between align-items-start gap-2">' +
                '<div><span class="fw-semibold">' + esc(ev.titulo || '—') + '</span>' +
                '<span class="d-block small text-muted">' + esc(nome) + ' · ' + esc(dt) + '</span></div>' +
                '<div class="text-nowrap">' + arq + '</div></li>';
        }).join('');
    }

    function _renderEnviosVendedor(lista) {
        _renderEnviosPendentesBoletos(lista);
    }

    function _renderEnviosPendentesBoletos(lista) {
        const tbody = document.getElementById('evoluirTcEnviosPendentes');
        const wrap = document.getElementById('evoluirTcEnviosPendentesWrap');
        const empty = document.getElementById('evoluirTcEnviosPendentesEmpty');
        if (!tbody || !empty) return;
        if (!lista || !lista.length) {
            if (wrap) wrap.classList.add('d-none');
            empty.classList.remove('d-none');
            tbody.innerHTML = '';
            return;
        }
        empty.classList.add('d-none');
        if (wrap) wrap.classList.remove('d-none');
        tbody.innerHTML = lista.map(function (ev) {
            const arq = ev.arquivo_url
                ? '<a href="' + ev.arquivo_url + '" target="_blank" rel="noopener">Ver</a>'
                : '<span class="text-muted">—</span>';
            return '<tr data-envio-id="' + esc(String(ev.id)) + '">' +
                '<td class="small">' + esc(ev.titulo || '—') + '</td>' +
                '<td class="small">' + arq + '</td>' +
                '<td class="small"><input type="text" class="form-control form-control-sm evoluir-tc-envio-valor" ' +
                'inputmode="decimal" autocomplete="off" placeholder="0,00" data-envio-id="' + esc(String(ev.id)) + '"></td>' +
                '<td class="small text-end">' +
                '<button type="button" class="btn btn-sm btn-outline-primary btn-confirmar-envio-boleto" data-envio-id="' +
                esc(String(ev.id)) + '">Confirmar</button></td></tr>';
        }).join('');
    }

    function _confirmarEnvioVendedorComoBoleto(envioId) {
        const contratoId = _contratoIdPagoTc();
        const alertaEl = document.getElementById('evoluirTcCompAlerta');
        if (!contratoId || !envioId) return;
        const inp = document.querySelector(
            '.evoluir-tc-envio-valor[data-envio-id="' + String(envioId) + '"]'
        );
        const valor = inp ? _parseValorComprovanteCampo(inp.value) : 0;
        if (!inp || !String(inp.value || '').trim() || !isFinite(valor) || valor <= 0) {
            if (alertaEl) {
                alertaEl.textContent = 'Informe o valor do boleto antes de confirmar.';
                alertaEl.classList.remove('d-none');
            }
            return;
        }
        if (alertaEl) alertaEl.classList.add('d-none');
        const errRmEnv = _validarRegistermoneyComprovante();
        if (errRmEnv) {
            if (alertaEl) {
                alertaEl.textContent = errRmEnv;
                alertaEl.classList.remove('d-none');
            }
            return;
        }
        const fd = new FormData();
        fd.append('contrato_id', contratoId);
        fd.append('envio_id', String(envioId));
        fd.append('valor', String(valor));
        const veEnv = (document.getElementById('evoluirPctcValorEst') || {}).value;
        if (veEnv && String(veEnv).trim()) {
            fd.append('registermoney', JSON.stringify(_buildRegistermoneyJsonComprovante()));
        }
        postMultipart('/contratos/api/v2/comprovante-tc/from-envio-vendedor/', fd)
            .then(function (j) {
                if (!j || !j.ok) {
                    throw new Error((j && j.erro) || 'Falha ao confirmar boleto.');
                }
                const sOk = Number(j.soma_acumulada);
                const tOk = Number(j.valor_tc);
                _tcCompSomaServidor = isFinite(sOk) ? sOk : 0;
                _tcCompValorTc = isFinite(tOk) ? tOk : 0;
                _atualizarBadgeTc(_tcCompSomaServidor, _tcCompValorTc);
                if (typeof showToast === 'function') {
                    showToast(
                        j.total_atingido ? 'Boleto confirmado — Pago TC Total.' : 'Boleto confirmado — Pago TC Parcial.',
                        'success'
                    );
                }
                _carregarComprovantesTc();
            })
            .catch(function (e) {
                if (alertaEl) {
                    alertaEl.textContent = e && e.message ? e.message : 'Erro ao confirmar boleto.';
                    alertaEl.classList.remove('d-none');
                }
            });
    }

    function _renderFichaEnviosVendedor(lista) {
        _renderEnviosVendedorListaHtml(lista, 'fichaEnviosVendedorLista', 'fichaEnviosVendedorEmpty', 'fichaBlkEnviosVendedor');
    }

    function _syncEvoluirEnviosVendedorWrap() {
        /* Bloco legado oculto; pendências do vendedor ficam em Adicionar Boletos (Pago TC). */
    }

    function _carregarComprovantesTc() {
        const contratoId = _contratoIdPagoTc();
        if (!contratoId) return;
        getJson('/contratos/api/v2/comprovantes-tc/?contrato_id=' + encodeURIComponent(contratoId))
            .then(function (d) {
                if (!d || !d.ok) return;
                _renderComprovantesTc(d.comprovantes || []);
                _renderEnviosPendentesBoletos(d.envios_vendedor || []);
                const soma = Number(d.soma);
                const vtc = Number(d.valor_tc);
                _tcCompSomaServidor = isFinite(soma) ? soma : 0;
                _tcCompValorTc = isFinite(vtc) ? vtc : 0;
                const inpComp = document.getElementById('evoluirTcCompValor');
                const extra = inpComp ? _parseValorComprovanteCampo(inpComp.value) : 0;
                _atualizarBadgeTc(_tcCompSomaServidor + (extra > 0 ? extra : 0), _tcCompValorTc);
            })
            .catch(function () { /* silencioso: UI principal ainda funciona */ });
    }

    function _enviarComprovanteTc() {
        const contratoId = _contratoIdPagoTc();
        const alertaEl = document.getElementById('evoluirTcCompAlerta');
        const valorInp = document.getElementById('evoluirTcCompValor');
        const arqInp = document.getElementById('evoluirTcCompArquivo');
        const btn = document.getElementById('evoluirTcCompEnviar');
        function erro(msg) {
            if (alertaEl) {
                alertaEl.textContent = msg;
                alertaEl.classList.remove('d-none');
            }
        }
        if (alertaEl) alertaEl.classList.add('d-none');
        if (!contratoId) return erro('Contrato não identificado para upload.');
        const valor = _parseValorComprovanteCampo(valorInp && valorInp.value);
        if (!valorInp || !String(valorInp.value || '').trim() || !isFinite(valor) || valor <= 0) {
            return erro('Informe um valor válido (> 0).');
        }
        const arquivo = arqInp && arqInp.files && arqInp.files[0];
        if (!arquivo) return erro('Anexe o arquivo do comprovante.');
        const errRm = _validarRegistermoneyComprovante();
        if (errRm) return erro(errRm);

        const fd = new FormData();
        fd.append('contrato_id', contratoId);
        fd.append('valor', String(valor));
        fd.append('arquivo', arquivo);
        let tcModalNum = _parseNumFlex(
            (document.getElementById('evoluirPctcValorEst') || {}).value
        );
        if (!isFinite(tcModalNum) || tcModalNum <= 0) {
            tcModalNum = Number(_tcCompValorTc) || 0;
        }
        if (tcModalNum > 0) {
            fd.append('registermoney', JSON.stringify(_buildRegistermoneyJsonComprovante()));
        }

        if (btn) btn.disabled = true;
        postMultipart('/contratos/api/v2/comprovante-tc/', fd).then(function (j) {
            if (!j || !j.ok) {
                throw new Error((j && j.erro) || 'Falha ao enviar comprovante.');
            }
            if (valorInp) valorInp.value = '';
            if (arqInp) arqInp.value = '';
            const sOk = Number(j.soma_acumulada);
            const tOk = Number(j.valor_tc);
            _tcCompSomaServidor = isFinite(sOk) ? sOk : 0;
            _tcCompValorTc = isFinite(tOk) ? tOk : 0;
            _atualizarBadgeTc(_tcCompSomaServidor, _tcCompValorTc);
            if (typeof showToast === 'function') {
                showToast(j.total_atingido ? 'Pago TC Total registrado.' : 'Pago TC Parcial registrado.', 'success');
            }
            _carregarComprovantesTc();
        }).catch(function (e) {
            erro(e && e.message ? e.message : 'Erro inesperado ao enviar comprovante.');
        }).finally(function () {
            if (btn) btn.disabled = false;
        });
    }

    function _preencherPagoCmsModal() {
        const m = _pagoCmsModal;
        const tit = document.getElementById('evoluirPcmsTitulo');
        const r1 = document.getElementById('evoluirPcmsTaxaRec');
        const r2 = document.getElementById('evoluirPcmsTaxaRep');
        const r3 = document.getElementById('evoluirPcmsTaxaPla');
        if (!tit || !r1 || !r2 || !r3) return;
        if (!m) {
            tit.value = '';
            r1.value = '';
            r2.value = '';
            r3.value = '';
            return;
        }
        tit.value = m.tabela_cms_titulo || '—';
        r1.value = m.taxa_recebido != null && m.taxa_recebido !== '' ? String(m.taxa_recebido) : '';
        r2.value = m.taxa_repasse != null && m.taxa_repasse !== '' ? String(m.taxa_repasse) : '';
        r3.value = m.taxa_plastico != null && m.taxa_plastico !== '' ? String(m.taxa_plastico) : '';
    }

    /* Modo livre: value do option = sub (definir_status) ou acao (fluxo restrito). */
    function _valorOptionTransicaoModoLivre(t) {
        const ac = (t && t.acao) ? String(t.acao) : 'operacional_definir_status';
        if (ac === 'operacional_definir_status') {
            return t.sub || '';
        }
        return ac;
    }

    function _acaoOptionTransicaoModoLivre(t, opt) {
        if (opt && opt.getAttribute('data-acao')) {
            return opt.getAttribute('data-acao');
        }
        if (t && t.acao) {
            return t.acao;
        }
        return 'operacional_definir_status';
    }

    /** Exige link quando o destino é Link disponível (modo livre ou catálogo sem data-requer). */
    function _requerExtraEvoluir(opt, subVal, etapaVal) {
        const requerOpt = opt ? (opt.getAttribute('data-requer') || '') : '';
        if (requerOpt) {
            return requerOpt;
        }
        const sub = String(subVal || '').trim();
        const etapa = String(etapaVal || '').trim();
        if (
            sub === 'FORM_LINK_DISPONIVEL'
            || (etapa === 'FORMALIZACAO' && sub === 'FORM_LINK_DISPONIVEL')
        ) {
            return 'link_formalizacao';
        }
        return requerOpt || null;
    }

    function _abrirModalVideoDesdeEvoluir() {
        const tipo = document.getElementById('evoluirTipo').value;
        const id = document.getElementById('evoluirId').value;
        if (tipo !== 'contrato' || !id) {
            showToast('Contrato não identificado para envio de vídeo.', 'warning');
            return;
        }
        document.getElementById('crmUpVidContratoId').value = String(id);
        blurFocoAtivo();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCrmUploadVideo')).show();
    }

    function _toggleExtraFields(requer, acao, opt) {
        const grLink = document.getElementById('evoluirGrupoLink');
        const grTab = document.getElementById('evoluirGrupoTabela');
        const grNumCt = document.getElementById('evoluirGrupoNumContrato');
        const inpNumCt = document.getElementById('evoluirNumContrato');
        const grPagoTc = document.getElementById('evoluirGrupoPagoTc');
        const grPagoCms = document.getElementById('evoluirGrupoPagoCms');
        const grObs = document.getElementById('evoluirGrupoObs');
        const lblObs = document.getElementById('evoluirLabelObs');
        const alerta = document.getElementById('evoluirAlerta');
        const btnConf = document.getElementById('btnConfirmarEvolucao');
        if (btnConf && requer !== 'registermoney_tc') btnConf.disabled = false;

        grLink.classList.add('d-none');
        grTab.classList.add('d-none');
        if (grNumCt) {
            grNumCt.classList.add('d-none');
            if (inpNumCt) inpNumCt.value = '';
        }
        if (grPagoTc) grPagoTc.classList.add('d-none');
        if (grPagoCms) grPagoCms.classList.add('d-none');
        grObs.classList.remove('d-none');
        lblObs.textContent = 'Observação';
        alerta.className = 'alert alert-warning py-2 small';
        alerta.classList.add('d-none');

        if (requer === 'link_formalizacao') {
            grLink.classList.remove('d-none');
        } else if (requer === 'tabela_cms') {
            grTab.classList.remove('d-none');
            if (grNumCt) grNumCt.classList.remove('d-none');
            _carregarTabelasCms();
        } else if (requer === 'registermoney_tc') {
            if (grPagoTc) grPagoTc.classList.remove('d-none');
            _preencherPagoTcModal();
            _syncVisibilidadeBlocoBoletosTc();
        } else if (requer === 'pago_cms_taxas') {
            if (grPagoCms) grPagoCms.classList.remove('d-none');
            _preencherPagoCmsModal();
        } else if (requer === 'observacao') {
            lblObs.innerHTML = 'Observação <span class="text-danger">*</span>';
        } else if (requer === 'form_propostas') {
            grObs.classList.add('d-none');
            alerta.className = 'alert alert-info small py-2 mb-0';
            alerta.textContent = 'Ao confirmar, abre o formulário para registrar, editar, incluir ou remover linhas de proposta.';
            alerta.classList.remove('d-none');
        } else if (
            requer === 'refin_port'
            || _exigeFluxoRefinPortPagoCliente(
                acao,
                opt,
                (document.getElementById('evoluirEtapa') || {}).value,
                (document.getElementById('evoluirSub') || {}).value
            )
        ) {
            alerta.className = 'alert alert-info py-2 small mb-0';
            alerta.textContent =
                'Ao confirmar, informe o Valor Saldo (PORT) e, em seguida, os dados do contrato REFIN (banco e convênio iguais ao PORT).';
            alerta.classList.remove('d-none');
            if (_refinPortDefaults && _refinPortDefaults.erro_config) {
                alerta.className = 'alert alert-danger py-2 small mb-0';
                alerta.textContent = _refinPortDefaults.erro_config;
                if (btnConf) btnConf.disabled = true;
            }
        } else if (
            _exigeValorSaldoPortEvoluir(
                acao,
                opt,
                (document.getElementById('evoluirEtapa') || {}).value,
                (document.getElementById('evoluirSub') || {}).value
            )
            && requer !== 'refin_port'
        ) {
            alerta.className = 'alert alert-info py-2 small mb-0';
            alerta.textContent =
                'Produto PORT: ao confirmar, informe o Valor Saldo antes de concluir o Pago Cliente.';
            alerta.classList.remove('d-none');
        } else if (requer === 'video_pagamento') {
            const etapaVid = document.getElementById('evoluirEtapa');
            const etapaAtual = etapaVid ? String(etapaVid.value || '') : '';
            if (etapaAtual !== 'PAGAMENTO') {
                alerta.classList.add('d-none');
            } else if (_pagoTcModal && _pagoTcModalBloqueiaPorVideo(_pagoTcModal)) {
                alerta.className = 'alert alert-danger py-2 small mb-0';
                alerta.innerHTML =
                    'Envio do vídeo de conscientização é obrigatório antes de ir para Pagamento. ' +
                    '<button type="button" class="btn btn-sm btn-outline-danger ms-1" id="evoluirBtnAnexarVideo">Anexar vídeo</button>';
                alerta.classList.remove('d-none');
                const btnVid = document.getElementById('evoluirBtnAnexarVideo');
                if (btnVid) {
                    btnVid.onclick = function () {
                        _abrirModalVideoDesdeEvoluir();
                    };
                }
                if (btnConf) btnConf.disabled = true;
            } else {
                alerta.className = 'alert alert-info py-2 small mb-0';
                alerta.textContent =
                    'Ao confirmar, o contrato será movido para Pagamento (Aguardando Pagamento Cliente).';
                alerta.classList.remove('d-none');
            }
        }
        if (acao === 'operacional_pago_cliente' && _pagoTcModal && _pagoTcModalBloqueiaPorVideo(_pagoTcModal)) {
            alerta.className = 'alert alert-danger py-2 small';
            alerta.textContent = 'Envio do vídeo de conscientização obrigatório antes do Pago Cliente.';
            alerta.classList.remove('d-none');
            if (btnConf) btnConf.disabled = true;
        }
    }

    function _carregarTabelasCms() {
        const tipo = document.getElementById('evoluirTipo').value;
        const id = document.getElementById('evoluirId').value;
        const sel = document.getElementById('evoluirTabelaCms');
        sel.innerHTML = '<option value="">Carregando...</option>';
        sel.disabled = true;

        // Para solicitacao_dig, busca tabelas pelo ID da solicitação
        const solId = tipo === 'solicitacao_dig' ? id : null;
        if (!solId) {
            sel.innerHTML = '<option value="">Não aplicável</option>';
            return;
        }
        getJson(base + 'tabelas-cms/?solicitacao_digitacao_id=' + encodeURIComponent(solId)).then(function (d) {
            sel.disabled = false;
            if (!d.ok || !d.tabelas || !d.tabelas.length) {
                sel.innerHTML = '<option value="">Nenhuma tabela disponível para este banco/produto</option>';
                return;
            }
            sel.innerHTML = '<option value="">Selecione a tabela CMS...</option>';
            // Mapeamento dos rótulos do Classificador Banco (M1 100% / M2 50% / M3 0%).
            // Exibir ao lado do título ajuda o operador a escolher a tabela correta.
            const _labelClassif = { 'M1': 'M1 - 100%', 'M2': 'M2 - 50%', 'M3': 'M3 - 0%' };
            d.tabelas.forEach(function (t) {
                const opt = document.createElement('option');
                opt.value = t.id;
                const cls = (t.classificador_banco || '').toString().toUpperCase();
                const sufixo = _labelClassif[cls] ? ' [' + _labelClassif[cls] + ']' : '';
                opt.textContent = t.titulo + sufixo;
                if (cls) opt.setAttribute('data-classificador', cls);
                sel.appendChild(opt);
            });
            const idProposta = d.tabela_cms_id_proposta != null ? String(d.tabela_cms_id_proposta) : '';
            if (idProposta) {
                const jaExiste = Array.from(sel.options).some(function (o) {
                    return String(o.value) === idProposta;
                });
                if (!jaExiste) {
                    const extra = document.createElement('option');
                    extra.value = idProposta;
                    extra.textContent = (d.tabela_cms_titulo_proposta || 'Tabela da proposta');
                    sel.appendChild(extra);
                }
                sel.value = idProposta;
            }
        }).catch(function () {
            sel.disabled = false;
            sel.innerHTML = '<option value="">Erro ao carregar tabelas</option>';
        });
    }

    /* ── Modal propostas simuladas (registro operacional) ── */
    let _catalogosPropostasCache = null;
    let _propostasSimSolicitacaoId = null;

    function _ensureCatalogosPropostas() {
        if (_catalogosPropostasCache) {
            return Promise.resolve(_catalogosPropostasCache);
        }
        return getJson(base + 'catalogos/').then(function (d) {
            if (!d.ok) {
                throw new Error(d.erro || 'Catálogos indisponíveis.');
            }
            _catalogosPropostasCache = d;
            return d;
        });
    }

    function _propostaSimMontarSelect(classe, itens, selecionado, placeholder) {
        const sel = document.createElement('select');
        sel.className = 'form-select form-select-sm ' + classe;
        const o0 = document.createElement('option');
        o0.value = '';
        o0.textContent = placeholder;
        sel.appendChild(o0);
        (itens || []).forEach(function (it) {
            const o = document.createElement('option');
            o.value = String(it.id);
            o.textContent = it.titulo || it.codigo || String(it.id);
            if (selecionado != null && String(selecionado) === String(it.id)) {
                o.selected = true;
            }
            sel.appendChild(o);
        });
        return sel;
    }

    function _propostaSimParseDecimalStr(v) {
        if (v === null || v === undefined) return '';
        const s = String(v).trim();
        if (!s) return '';
        return s.replace(/\s/g, '').replace(',', '.');
    }

    function _propostaSimParsePrazo(v) {
        const s = (v !== undefined && v !== null) ? String(v).trim() : '';
        if (!s) return null;
        const n = parseInt(s, 10);
        if (!Number.isNaN(n) && n >= 0) return n;
        return null;
    }

    function adicionarLinhaPropostaSim(dados, catalogos) {
        dados = dados || {};
        const bancos = catalogos.bancos || [];
        const convenios = catalogos.convenios || [];
        const produtos = catalogos.produtos || [];
        const wrap = document.getElementById('propostasSimRows');
        const row = document.createElement('div');
        row.className = 'proposta-sim-linha';
        if (dados.id) {
            row.dataset.propostaId = String(dados.id);
        }

        const r1 = document.createElement('div');
        r1.className = 'row g-2 align-items-end';

        function col(label, el) {
            const c = document.createElement('div');
            c.className = 'col-md-4';
            const lb = document.createElement('label');
            lb.className = 'form-label small text-muted mb-0';
            lb.textContent = label;
            c.appendChild(lb);
            c.appendChild(el);
            return c;
        }

        const sb = _propostaSimMontarSelect('js-proposta-banco', bancos, dados.banco_id, 'Banco…');
        const sc = _propostaSimMontarSelect('js-proposta-convenio', convenios, dados.convenio_id, 'Convênio…');
        const sp = _propostaSimMontarSelect('js-proposta-produto', produtos, dados.produto_id, 'Produto…');
        r1.appendChild(col('Banco', sb));
        r1.appendChild(col('Convênio', sc));
        r1.appendChild(col('Produto', sp));

        const r2 = document.createElement('div');
        r2.className = 'row g-2 mt-1';

        function inpNum(classe, valor, ph) {
            const i = document.createElement('input');
            i.type = 'text';
            i.className = 'form-control form-control-sm ' + classe;
            i.placeholder = ph;
            i.autocomplete = 'off';
            i.value = valor != null && valor !== '' ? String(valor) : '';
            return i;
        }

        function colInp(label, el, colClass) {
            const c = document.createElement('div');
            c.className = colClass || 'col-6 col-md';
            const lb = document.createElement('label');
            lb.className = 'form-label small text-muted mb-0';
            lb.textContent = label;
            c.appendChild(lb);
            c.appendChild(el);
            return c;
        }

        const iParcela = inpNum('js-proposta-parcela', dados.valor_parcela, 'Parcela');
        const iPrazo = inpNum('js-proposta-prazo', dados.prazo, 'Prazo');
        const iAf = inpNum('js-proposta-af', dados.valor_af, 'AF');
        const iTc = inpNum('js-proposta-tc', dados.valor_tc, 'TC');
        const iLib = inpNum('js-proposta-lib', dados.valor_liberado, 'Liberado');

        r2.appendChild(colInp('Valor parcela', iParcela, 'col-6 col-md'));
        r2.appendChild(colInp('Prazo', iPrazo, 'col-6 col-md'));
        r2.appendChild(colInp('AF', iAf, 'col-6 col-md'));
        r2.appendChild(colInp('TC', iTc, 'col-6 col-md'));
        r2.appendChild(colInp('Liberado', iLib, 'col-6 col-md'));

        row.appendChild(r1);
        row.appendChild(r2);

        const btnRm = document.createElement('button');
        btnRm.type = 'button';
        btnRm.className = 'btn btn-sm btn-link text-danger proposta-sim-remove p-0';
        btnRm.setAttribute('aria-label', 'Remover linha');
        btnRm.innerHTML = '<i class="bx bx-trash"></i>';
        btnRm.addEventListener('click', function () {
            const todas = wrap.querySelectorAll('.proposta-sim-linha');
            if (todas.length <= 1) {
                showToast('Informe ao menos uma proposta.', 'warning');
                return;
            }
            row.remove();
        });
        row.appendChild(btnRm);

        wrap.appendChild(row);
    }

    function coletarPropostasSimDoForm() {
        const rows = document.querySelectorAll('#propostasSimRows .proposta-sim-linha');
        const out = [];
        rows.forEach(function (row) {
            const b = row.querySelector('.js-proposta-banco');
            const c = row.querySelector('.js-proposta-convenio');
            const p = row.querySelector('.js-proposta-produto');
            if (!b || !c || !p || !b.value || !c.value || !p.value) {
                throw new Error('incompleto');
            }
            const item = {
                banco_id: parseInt(b.value, 10),
                convenio_id: parseInt(c.value, 10),
                produto_id: parseInt(p.value, 10),
                valor_parcela: _propostaSimParseDecimalStr(row.querySelector('.js-proposta-parcela').value),
                prazo: _propostaSimParsePrazo(row.querySelector('.js-proposta-prazo').value),
                valor_af: _propostaSimParseDecimalStr(row.querySelector('.js-proposta-af').value),
                valor_tc: _propostaSimParseDecimalStr(row.querySelector('.js-proposta-tc').value),
                valor_liberado: _propostaSimParseDecimalStr(row.querySelector('.js-proposta-lib').value),
            };
            const pid = row.dataset.propostaId;
            if (pid) {
                item.id = parseInt(pid, 10);
            }
            out.push(item);
        });
        return out;
    }

    function _preencherModalRefinPort(def) {
        def = def || {};
        const alerta = document.getElementById('refinPortAlerta');
        if (alerta) {
            alerta.classList.add('d-none');
            alerta.textContent = '';
            if (def.erro_config) {
                alerta.textContent = def.erro_config;
                alerta.classList.remove('d-none');
            }
        }
        document.getElementById('refinPortBanco').value = def.banco_titulo || '';
        document.getElementById('refinPortConvenio').value = def.convenio_titulo || '';
        document.getElementById('refinPortProduto').value = def.produto_refin_titulo || '';
        document.getElementById('refinPortNumContrato').value = '';
        const pd = def.proposta_defaults || {};
        document.getElementById('refinPortParcela').value = pd.valor_parcela != null ? String(pd.valor_parcela) : '';
        document.getElementById('refinPortPrazo').value = pd.prazo != null && pd.prazo !== '' ? String(pd.prazo) : '';
        document.getElementById('refinPortAf').value = pd.valor_af != null ? String(pd.valor_af) : '';
        document.getElementById('refinPortTc').value = pd.valor_tc != null ? String(pd.valor_tc) : '';
        document.getElementById('refinPortLiberado').value = pd.valor_liberado != null ? String(pd.valor_liberado) : '';
        const wrapSaldo = document.getElementById('refinPortValorSaldoWrap');
        const inpSaldo = document.getElementById('refinPortValorSaldo');
        const saldoExibir = _valorSaldoPendente || pd.valor_saldo || '';
        if (wrapSaldo && inpSaldo) {
            if (saldoExibir) {
                wrapSaldo.classList.remove('d-none');
                inpSaldo.value = String(saldoExibir);
            } else {
                wrapSaldo.classList.add('d-none');
                inpSaldo.value = '';
            }
        }
        const sel = document.getElementById('refinPortTabelaCms');
        sel.innerHTML = '<option value="">Selecione a tabela CMS...</option>';
        const _labelClassif = { M1: 'M1 - 100%', M2: 'M2 - 50%', M3: 'M3 - 0%' };
        (def.tabelas_cms || []).forEach(function (t) {
            const opt = document.createElement('option');
            opt.value = String(t.id);
            const cls = (t.classificador_banco || '').toString().toUpperCase();
            const sufixo = _labelClassif[cls] ? ' [' + _labelClassif[cls] + ']' : '';
            opt.textContent = (t.titulo || '') + sufixo;
            sel.appendChild(opt);
        });
        const wrapPort = document.getElementById('refinPortPortadosWrap');
        const ulPort = document.getElementById('refinPortPortadosLista');
        const portados = def.contratos_portados || [];
        if (wrapPort && ulPort) {
            if (!portados.length) {
                wrapPort.classList.add('d-none');
                ulPort.innerHTML = '';
            } else {
                wrapPort.classList.remove('d-none');
                ulPort.innerHTML = portados.map(function (cp) {
                    return '<li class="list-group-item py-1">' +
                        esc(cp.banco || '—') + ' — ' + esc(cp.numero_contrato || 's/n') +
                        (cp.valor_af ? ' · AF R$ ' + esc(cp.valor_af) : '') +
                        '</li>';
                }).join('');
            }
        }
        const btnRef = document.getElementById('btnConfirmarRefinPort');
        if (btnRef) {
            btnRef.disabled = !!(def.erro_config || def.refin_ja_existe);
        }
    }

    function _abrirModalRefinPort(tipo, id, observacao, evoluirCtx) {
        evoluirCtx = evoluirCtx || {};
        _evoluirPendenteRefinPort = {
            tipo: tipo,
            id: id,
            observacao: observacao || '',
            acao: evoluirCtx.acao || 'operacional_pago_cliente',
            etapa: evoluirCtx.etapa || '',
            sub: evoluirCtx.sub || '',
        };
        const carregar = function (def) {
            _preencherModalRefinPort(def);
            const modalEv = bootstrap.Modal.getInstance(document.getElementById('modalEvoluir'));
            if (modalEv) {
                modalEv.hide();
            }
            bootstrap.Modal.getOrCreateInstance(document.getElementById('modalRefinPort')).show();
        };
        if (_refinPortDefaults && !_refinPortDefaults.refin_ja_existe) {
            carregar(_refinPortDefaults);
            return;
        }
        getJson(base + 'contrato/' + encodeURIComponent(id) + '/refin-port-defaults/').then(function (d) {
            if (!d.ok) {
                showToast(d.erro || 'Não foi possível carregar dados do REFIN.', 'danger');
                return;
            }
            carregar(d);
        }).catch(function () {
            showToast('Erro ao carregar defaults do REFIN.', 'danger');
        });
    }

    function _coletarPayloadRefinPort() {
        const num = String(document.getElementById('refinPortNumContrato').value || '').trim().toUpperCase();
        const tid = document.getElementById('refinPortTabelaCms').value;
        const out = {
            numero_contrato: num,
            tabela_cms_id: tid ? parseInt(tid, 10) : null,
            proposta: {
                valor_parcela: document.getElementById('refinPortParcela').value,
                prazo: document.getElementById('refinPortPrazo').value,
                valor_af: document.getElementById('refinPortAf').value,
                valor_tc: document.getElementById('refinPortTc').value,
                valor_liberado: document.getElementById('refinPortLiberado').value,
            },
        };
        const inpSaldo = document.getElementById('refinPortValorSaldo');
        const rawSaldo = inpSaldo ? String(inpSaldo.value || '').trim() : '';
        if (rawSaldo) {
            out.valor_saldo = rawSaldo;
        } else if (_valorSaldoPendente) {
            out.valor_saldo = _valorSaldoPendente;
        }
        return out;
    }

    document.getElementById('btnConfirmarValorSaldoPort').addEventListener('click', function () {
        const pend = _evoluirPendenteSaldoPort;
        if (!pend) {
            showToast('Sessão do modal Valor Saldo expirada. Abra Evoluir novamente.', 'warning');
            return;
        }
        const raw = document.getElementById('valorSaldoPortInput').value;
        const n = _parseNumFlex(raw);
        if (!isFinite(n) || n < 0) {
            showToast('Informe um Valor Saldo válido (maior ou igual a zero).', 'warning');
            return;
        }
        _valorSaldoPendente = String(raw).trim();
        const al = document.getElementById('valorSaldoPortAlerta');
        if (al) {
            al.classList.add('d-none');
        }
        bootstrap.Modal.getInstance(document.getElementById('modalValorSaldoPort')).hide();
        if (pend.needsRefin) {
            _abrirModalRefinPort(pend.tipo, pend.id, pend.observacao, {
                acao: pend.acao,
                etapa: pend.etapa,
                sub: pend.sub,
            });
            return;
        }
        const btn = document.getElementById('btnConfirmarValorSaldoPort');
        if (btn) {
            btn.disabled = true;
        }
        postJson(base + 'evoluir/', _montarPayloadPagoClienteEvoluir(pend, null)).then(function (r) {
            if (btn) {
                btn.disabled = false;
            }
            if (!r.ok) {
                showToast(r.erro || 'Erro ao confirmar Pago Cliente.', 'danger');
                return;
            }
            _evoluirPendenteSaldoPort = null;
            _valorSaldoPendente = null;
            showToast('Pago Cliente confirmado.', 'success');
            safeReloadFilaUnificada();
        }).catch(function () {
            if (btn) {
                btn.disabled = false;
            }
            showToast('Falha de rede ao confirmar.', 'danger');
        });
    });

    document.getElementById('btnConfirmarRefinPort').addEventListener('click', function () {
        const pend = _evoluirPendenteRefinPort;
        if (!pend) {
            showToast('Sessão do modal REFIN expirada. Abra Evoluir novamente.', 'warning');
            return;
        }
        const refinPort = _coletarPayloadRefinPort();
        if (!refinPort.numero_contrato) {
            showToast('Informe o número do contrato REFIN.', 'warning');
            return;
        }
        if (!/^[A-Z0-9\-\.\/]{1,30}$/.test(refinPort.numero_contrato)) {
            showToast('Nº contrato REFIN inválido. Use apenas letras, números e -./ (até 30 caracteres).', 'warning');
            return;
        }
        if (!refinPort.tabela_cms_id) {
            showToast('Selecione a tabela CMS do REFIN.', 'warning');
            return;
        }
        if (
            _exigeValorSaldoPortEvoluir(pend.acao, null, pend.etapa, pend.sub)
            && !refinPort.valor_saldo
        ) {
            showToast('Informe o Valor Saldo (PORT) antes de confirmar o REFIN.', 'warning');
            return;
        }
        if (refinPort.valor_saldo && !_valorSaldoPendente) {
            _valorSaldoPendente = String(refinPort.valor_saldo);
        }
        const payload = _montarPayloadPagoClienteEvoluir(pend, refinPort);
        document.getElementById('btnConfirmarRefinPort').disabled = true;
        postJson(base + 'evoluir/', payload).then(function (r) {
            document.getElementById('btnConfirmarRefinPort').disabled = false;
            if (!r.ok) {
                const al = document.getElementById('refinPortAlerta');
                if (al) {
                    al.textContent = r.erro || 'Erro ao confirmar.';
                    al.classList.remove('d-none');
                }
                showToast(r.erro || 'Erro ao confirmar Pago Cliente + REFIN.', 'danger');
                return;
            }
            bootstrap.Modal.getInstance(document.getElementById('modalRefinPort')).hide();
            _evoluirPendenteRefinPort = null;
            _evoluirPendenteSaldoPort = null;
            _valorSaldoPendente = null;
            let msg = 'Pago Cliente confirmado.';
            if (r.contrato && r.contrato.contrato_refin_codigo) {
                msg += ' Contrato REFIN: ' + r.contrato.contrato_refin_codigo + '.';
            }
            showToast(msg, 'success');
            loadTabelaUnificada();
        }).catch(function () {
            document.getElementById('btnConfirmarRefinPort').disabled = false;
            showToast('Falha de rede ao confirmar.', 'danger');
        });
    });

    function abrirModalPropostasSimuladas(solicitacaoId) {
        _propostasSimSolicitacaoId = solicitacaoId;
        const modalEv = bootstrap.Modal.getInstance(document.getElementById('modalEvoluir'));
        if (modalEv) {
            modalEv.hide();
        }

        const elModal = document.getElementById('modalPropostasSimuladas');
        const modalPs = bootstrap.Modal.getOrCreateInstance(elModal);
        const rowsEl = document.getElementById('propostasSimRows');
        const btnAdd = document.getElementById('btnPropostasSimAdd');
        const btnSalvar = document.getElementById('btnSalvarPropostasSim');
        const obsEl = document.getElementById('propostasSimObservacao');
        if (obsEl) {
            obsEl.value = '';
        }

        rowsEl.innerHTML = '<div class="text-center text-muted py-3 small"><span class="spinner-border spinner-border-sm me-2" role="status"></span>Carregando…</div>';
        btnAdd.classList.add('d-none');
        btnSalvar.disabled = true;

        modalPs.show();

        Promise.all([
            _ensureCatalogosPropostas(),
            getJson(base + 'solicitacao-proposta/' + encodeURIComponent(solicitacaoId) + '/propostas/'),
        ]).then(function (res) {
            const catalogos = res[0];
            const pr = res[1];
            rowsEl.innerHTML = '';
            if (!pr.ok) {
                showToast(pr.erro || 'Erro ao carregar propostas.', 'danger');
                modalPs.hide();
                return;
            }
            if (obsEl) {
                obsEl.value = (pr.observacao_resposta != null && pr.observacao_resposta !== undefined)
                    ? String(pr.observacao_resposta)
                    : '';
            }
            const lista = pr.propostas || [];
            if (lista.length > 0) {
                lista.forEach(function (p) {
                    adicionarLinhaPropostaSim(p, catalogos);
                });
            } else {
                adicionarLinhaPropostaSim(null, catalogos);
            }
            btnAdd.classList.remove('d-none');
            btnSalvar.disabled = false;
        }).catch(function () {
            showToast('Erro ao carregar catálogos ou propostas.', 'danger');
            rowsEl.innerHTML = '';
            modalPs.hide();
        });
    }

    document.getElementById('btnPropostasSimAdd').addEventListener('click', function () {
        if (!_catalogosPropostasCache) return;
        adicionarLinhaPropostaSim(null, _catalogosPropostasCache);
    });

    document.getElementById('btnSalvarPropostasSim').addEventListener('click', function () {
        const sid = _propostasSimSolicitacaoId;
        if (!sid) return;
        let propostas;
        try {
            propostas = coletarPropostasSimDoForm();
        } catch (e) {
            showToast('Preencha banco, convênio e produto em todas as linhas.', 'warning');
            return;
        }
        if (!propostas.length) {
            showToast('Inclua ao menos uma proposta.', 'warning');
            return;
        }
        const btn = document.getElementById('btnSalvarPropostasSim');
        const obsTa = document.getElementById('propostasSimObservacao');
        const observacao = obsTa ? (obsTa.value || '').trim() : '';
        btn.disabled = true;
        postJson(base + 'solicitacao-proposta/responder/', {
            solicitacao_id: sid,
            resultado: 'propostas',
            observacao: observacao,
            propostas: propostas,
        }).then(function (r) {
            btn.disabled = false;
            if (!r.ok) {
                showToast(r.erro || 'Erro ao salvar propostas.', 'danger');
                return;
            }
            bootstrap.Modal.getInstance(document.getElementById('modalPropostasSimuladas')).hide();
            showToast('Propostas registradas com sucesso.', 'success');
            safeReloadFilaUnificada();
        }).catch(function () {
            btn.disabled = false;
            showToast('Erro de comunicação com o servidor.', 'danger');
        });
    });

    /* ── Pago TC: prévia ranking em tempo real ── */
    (function () {
        const ve = document.getElementById('evoluirPctcValorEst');
        const cl = document.getElementById('evoluirPctcClassificador');
        if (ve) {
            ve.addEventListener('input', function () {
                _atualizarRankingPctc();
                _syncVisibilidadeBlocoBoletosTc();
                const vTc = _parseNumFlex(ve.value);
                if (isFinite(vTc) && vTc > 0) {
                    _tcCompValorTc = vTc;
                    const extra = document.getElementById('evoluirTcCompValor');
                    const extraN = extra ? _parseValorComprovanteCampo(extra.value) : 0;
                    _atualizarBadgeTc(_tcCompSomaServidor + (extraN > 0 ? extraN : 0), _tcCompValorTc);
                } else {
                    _atualizarBadgeTc(_tcCompSomaServidor, 0);
                }
            });
        }
        if (cl) cl.addEventListener('change', _atualizarRankingPctc);
    })();
    (function () {
        const wrap = document.getElementById('evoluirPctcLojaWrap');
        if (!wrap) return;
        wrap.addEventListener('change', function (e) {
            if (
                e.target &&
                (e.target.id === 'evoluirPctcAssocLojaSim' ||
                    e.target.id === 'evoluirPctcAssocLojaNao' ||
                    e.target.id === 'evoluirPctcLojaId')
            ) {
                _atualizarUiPctcAssocLoja();
            }
        });
    })();
    document.getElementById('modalEvoluir').addEventListener('hidden.bs.modal', function () {
        const b = document.getElementById('btnConfirmarEvolucao');
        if (b) b.disabled = false;
        _tcCompSomaServidor = 0;
        _tcCompValorTc = 0;
    });

    /* ── Confirmar evolução ── */
    document.getElementById('btnConfirmarEvolucao').addEventListener('click', confirmarEvolucao);

    function confirmarEvolucao() {
        const tipo = document.getElementById('evoluirTipo').value;
        const id = parseInt(document.getElementById('evoluirId').value, 10);
        const selSub = document.getElementById('evoluirSub');
        const selEtapa = document.getElementById('evoluirEtapa');
        const opt = selSub.options[selSub.selectedIndex];
        const etapaVal = selEtapa ? String(selEtapa.value || '').trim() : '';
        const subVal = selSub ? String(selSub.value || '').trim() : '';
        let acao = selSub ? String(selSub.value || '').trim() : '';
        if (_modoLivreEvoluir && tipo === 'contrato') {
            acao = _acaoOptionTransicaoModoLivre(null, opt);
        }
        const requer = _requerExtraEvoluir(opt, subVal, etapaVal);
        const observacao = document.getElementById('evoluirObs').value.trim();
        const link = document.getElementById('evoluirLink').value.trim();
        const tabelaCmsId = document.getElementById('evoluirTabelaCms').value;
        const inpNumCt = document.getElementById('evoluirNumContrato');
        const numContrato = inpNumCt ? String(inpNumCt.value || '').trim().toUpperCase() : '';

        if (acao === 'operacional_definir_status' && tipo === 'contrato') {
            if (!etapaVal || !subVal) {
                showToast('Selecione uma etapa e um status.', 'warning');
                return;
            }
        } else if (!acao) {
            const ge = document.getElementById('evoluirGrupoEtapa');
            const msgPre =
                tipo === 'solicitacao_dig' && ge && ge.classList.contains('d-none')
                    ? 'Selecione Gerar contrato, Pendenciar ou Cancelar.'
                    : 'Selecione uma etapa e um status.';
            showToast(msgPre, 'warning');
            return;
        }
        if (
            tipo === 'contrato'
            && etapaVal === 'PAGAMENTO'
            && acao === 'operacional_definir_status'
            && _pagoTcModal
            && _pagoTcModalBloqueiaPorVideo(_pagoTcModal)
        ) {
            showToast(
                'Envio do vídeo de conscientização obrigatório antes de ir para Pagamento.',
                'danger'
            );
            return;
        }
        if (acao === 'operacional_pago_cliente' && _pagoTcModal && _pagoTcModalBloqueiaPorVideo(_pagoTcModal)) {
            showToast('Envio do vídeo de conscientização obrigatório antes do Pago Cliente.', 'danger');
            return;
        }

        /* Registrar propostas simuladas: abre modal dedicado (sem POST em evoluir/) */
        if (requer === 'form_propostas' && acao === 'sim_propostas') {
            abrirModalPropostasSimuladas(id);
            return;
        }
        if (requer === 'form_propostas') {
            showToast('Esta ação de propostas ainda não está disponível neste fluxo.', 'warning');
            return;
        }

        if (requer === 'link_formalizacao' && !link) {
            showToast('Informe o link de formalização.', 'warning');
            return;
        }
        if (requer === 'tabela_cms' && !tabelaCmsId) {
            showToast('Selecione uma tabela CMS.', 'warning');
            return;
        }
        if (requer === 'tabela_cms') {
            if (!numContrato) {
                showToast('Informe o Nº Contrato.', 'warning');
                if (inpNumCt) inpNumCt.focus();
                return;
            }
            if (!/^[A-Z0-9\-\.\/]{1,30}$/.test(numContrato)) {
                showToast('Nº Contrato inválido. Use apenas letras, números e -./ (até 30 caracteres).', 'warning');
                if (inpNumCt) inpNumCt.focus();
                return;
            }
        }
        if (requer === 'observacao' && !observacao) {
            showToast('Observação obrigatória para esta ação.', 'warning');
            return;
        }
        if (requer === 'registermoney_tc') {
            if (_pagoTcModal && _pagoTcModalBloqueiaPorVideo(_pagoTcModal)) {
                showToast('Envio do vídeo de conscientização obrigatório antes do Pago TC.', 'danger');
                return;
            }
            const ve = (document.getElementById('evoluirPctcValorEst') || {}).value;
            const semTc = !isFinite(_parseNumFlex(ve)) || _parseNumFlex(ve) <= 0;
            if (semTc && Number(_tcCompValorTc) > 0) {
                showToast('Salve os dados antes de confirmar ao zerar o Valor TC.', 'warning');
                return;
            }
            if (!semTc) {
                const lojaChk = _pctcPayloadLojaRm();
                const lojasM = (_pagoTcModal || {}).lojas_elegiveis || [];
                if (lojaChk.venda_associada_loja && lojasM.length === 0) {
                    showToast('Marque “Não” em venda associada a loja ou cadastre lojas nos funcionários.', 'danger');
                    return;
                }
                if (lojaChk.venda_associada_loja && !lojaChk.loja_id) {
                    showToast('Selecione a loja da venda.', 'warning');
                    return;
                }
            }
            if (!semTc && (!ve || !String(ve).trim())) {
                showToast('Informe o valor TC.', 'warning');
                return;
            }
            const cl = document.getElementById('evoluirPctcClassificador');
            if (!semTc && (!cl || !cl.value)) {
                showToast('Selecione o classificador de valor.', 'warning');
                return;
            }
            if (!semTc) {
                const errDados = _validarDadosPagoTcModal();
                if (errDados) {
                    showToast(errDados, 'warning');
                    return;
                }
                const veNum = _parseNumFlex(ve);
                const tcServidor = Number(_tcCompValorTc);
                const tcAlterado =
                    isFinite(veNum) &&
                    isFinite(tcServidor) &&
                    Math.abs(veNum - tcServidor) > 0.009;
                if (tcAlterado) {
                    showToast(
                        'O Valor TC foi alterado. Use “Salvar dados (TC, classificador, loja)” antes de confirmar ou enviar comprovante.',
                        'warning'
                    );
                    return;
                }
                if (!isFinite(_tcCompSomaServidor) || Number(_tcCompSomaServidor) <= 0) {
                    showToast(
                        'Para TC maior que zero, salve ao menos um comprovante antes de confirmar a evolução.',
                        'warning'
                    );
                    return;
                }
            }
        }
        if (requer === 'pago_cms_taxas') {
            const tr = (document.getElementById('evoluirPcmsTaxaRec') || {}).value;
            const tp = (document.getElementById('evoluirPcmsTaxaRep') || {}).value;
            const tpl = (document.getElementById('evoluirPcmsTaxaPla') || {}).value;
            if (!String(tr || '').trim() || !String(tp || '').trim() || !String(tpl || '').trim()) {
                showToast('Informe os três percentuais (recebido, repasse e plástico).', 'warning');
                return;
            }
        }

        const payload = { tipo, id, acao, observacao };
        if (acao === 'operacional_definir_status' && tipo === 'contrato') {
            payload.etapa = etapaVal;
            payload.sub = subVal;
        }
        if (link) payload.link_formalizacao = link;
        if (tabelaCmsId) payload.tabela_cms_id = parseInt(tabelaCmsId, 10);
        if (requer === 'tabela_cms' && numContrato) payload.contrato_codigo = numContrato;
        if (requer === 'registermoney_tc') {
            const gv = function (id) {
                const el = document.getElementById(id);
                return el ? String(el.value || '').trim() : '';
            };
            const mTc = _pagoTcModal || {};
            const snapCms = function (k) {
                const v = mTc[k];
                if (v === undefined || v === null) return '';
                return String(v).trim();
            };
            payload.valor_est_tc = gv('evoluirPctcValorEst');
            payload.af = gv('evoluirPctcAf');
            /* CMS flat: não editáveis na tela; envia snapshot da API (pago_tc_modal). */
            payload.valor_cms_recebido = snapCms('valor_cms_recebido');
            payload.valor_cms_repassado = snapCms('valor_cms_repassado');
            payload.valor_cms_plastico = snapCms('valor_cms_plastico');
            const fc = document.getElementById('evoluirPctcFlagCms');
            payload.flag_cms_pago = fc ? !!fc.checked : false;
            const selC = document.getElementById('evoluirPctcClassificador');
            payload.classificacao_valor_id = selC && selC.value ? parseInt(selC.value, 10) : null;
            payload.classificador_id = selC && selC.value ? parseInt(selC.value, 10) : null;
            const lp = _pctcPayloadLojaRm();
            payload.venda_associada_loja = lp.venda_associada_loja;
            payload.loja_id = lp.loja_id;
            const fm3 = document.getElementById('evoluirPctcForcarM3');
            payload.forcar_m3 = fm3 ? !!fm3.checked : false;
        }
        if (requer === 'pago_cms_taxas') {
            const gv = function (id) {
                const el = document.getElementById(id);
                return el ? String(el.value || '').trim() : '';
            };
            payload.taxa_recebido_snapshot = gv('evoluirPcmsTaxaRec');
            payload.taxa_repasse_snapshot = gv('evoluirPcmsTaxaRep');
            payload.taxa_plastico_snapshot = gv('evoluirPcmsTaxaPla');
        }

        function _executarPostEvoluirContrato() {
            document.getElementById('btnConfirmarEvolucao').disabled = true;

            postJson(base + 'evoluir/', payload).then(function (r) {
                const btnEv = document.getElementById('btnConfirmarEvolucao');
                if (btnEv) btnEv.disabled = false;
                if (requer === 'registermoney_tc' && _pagoTcModal && _pagoTcModalBloqueiaPorVideo(_pagoTcModal) && btnEv) {
                    btnEv.disabled = true;
                }
                if (!r.ok) {
                    showToast(r.erro || 'Erro ao evoluir registro.', 'danger');
                    return;
                }
                bootstrap.Modal.getInstance(document.getElementById('modalEvoluir')).hide();
                let msgOk = 'Registro evoluído com sucesso.';
                if (
                    _destinoEvolucaoPagoCliente(acao, etapaVal, subVal)
                    && r.contrato
                    && r.contrato.contrato_refin_codigo
                ) {
                    msgOk += ' Contrato REFIN: ' + r.contrato.contrato_refin_codigo + '.';
                }
                showToast(msgOk, 'success');
                if (
                    tipo === 'contrato'
                    && acao === 'supervisor_formalizado'
                    && r.contrato
                    && r.contrato.flag_video_enviado === false
                    && r.contrato.exige_video_conscientizacao !== false
                ) {
                    const cidVid = r.contrato.id;
                    const hid = document.getElementById('crmUpVidContratoId');
                    const fin = document.getElementById('crmUpVidFile');
                    if (hid) hid.value = String(cidVid);
                    if (fin) fin.value = '';
                    setTimeout(function () {
                        const mEl = document.getElementById('modalCrmUploadVideo');
                        if (mEl) bootstrap.Modal.getOrCreateInstance(mEl).show();
                    }, 300);
                }
                safeReloadFilaUnificada();
            }).catch(function () {
                const btnEv = document.getElementById('btnConfirmarEvolucao');
                if (btnEv) btnEv.disabled = false;
                if (requer === 'registermoney_tc' && _pagoTcModal && _pagoTcModalBloqueiaPorVideo(_pagoTcModal) && btnEv) {
                    btnEv.disabled = true;
                }
                showToast('Erro de comunicação com o servidor.', 'danger');
            });
        }

        function _interceptarPortRefinAntesPost() {
            if (tipo !== 'contrato' || !_destinoEvolucaoPagoCliente(acao, etapaVal, subVal)) {
                _executarPostEvoluirContrato();
                return;
            }
            _carregarRefinPortDefaultsSeNecessario(id, function () {
                const evoluirCtx = { acao: acao, etapa: etapaVal, sub: subVal };
                const needsRefinPort = _exigeFluxoRefinPortPagoCliente(acao, opt, etapaVal, subVal);
                if (_exigeValorSaldoPortEvoluir(acao, opt, etapaVal, subVal)) {
                    _abrirModalValorSaldoPort(tipo, id, observacao, needsRefinPort, evoluirCtx);
                    return;
                }
                if (needsRefinPort) {
                    _abrirModalRefinPort(tipo, id, observacao, evoluirCtx);
                    return;
                }
                _executarPostEvoluirContrato();
            });
        }

        _interceptarPortRefinAntesPost();
    }

    /* ══════════════════════════════
       BOTÕES GLOBAIS
    ══════════════════════════════ */
    /* Evita sobreposição de fetch (SSE + botão Atualizar) */
    let _filaUnificadaCarregando = false;

    function safeReloadFilaUnificada() {
        if (_filaUnificadaCarregando) return;
        _filaUnificadaCarregando = true;
        loadTabelaUnificada().finally(function () {
            _filaUnificadaCarregando = false;
        });
    }

    var btnRefreshAll = document.getElementById('btnRefreshAll');
    if (btnRefreshAll) btnRefreshAll.addEventListener('click', safeReloadFilaUnificada);

    var btnEnviarComprovanteTc = document.getElementById('evoluirTcCompEnviar');
    if (btnEnviarComprovanteTc) btnEnviarComprovanteTc.addEventListener('click', _enviarComprovanteTc);

    var btnSalvarDadosPctc = document.getElementById('evoluirPctcSalvarDados');
    if (btnSalvarDadosPctc) btnSalvarDadosPctc.addEventListener('click', _salvarDadosPagoTcModal);

    var listaCompTc = document.getElementById('evoluirTcCompLista');
    if (listaCompTc) {
        listaCompTc.addEventListener('click', function (e) {
            const btn = e.target && e.target.closest ? e.target.closest('.js-excluir-comp-tc') : null;
            if (!btn) return;
            e.preventDefault();
            _excluirComprovanteTc(btn.getAttribute('data-comp-id'));
        });
    }

    var inpValorComprovanteTc = document.getElementById('evoluirTcCompValor');
    if (inpValorComprovanteTc) {
        inpValorComprovanteTc.addEventListener('input', function () {
            const digits = String(inpValorComprovanteTc.value || '').replace(/\D/g, '');
            const fmt = _formatarValorComprovanteDigitosCentavos(digits);
            if (inpValorComprovanteTc.value !== fmt) {
                inpValorComprovanteTc.value = fmt;
                try {
                    inpValorComprovanteTc.setSelectionRange(fmt.length, fmt.length);
                } catch (e2) { /* ignore */ }
            }
            const novo = digits ? parseInt(digits, 10) / 100 : 0;
            _atualizarBadgeTc(_tcCompSomaServidor + (novo > 0 ? novo : 0), _tcCompValorTc);
        });
        inpValorComprovanteTc.addEventListener('blur', function () {
            const inp = inpValorComprovanteTc;
            const digits = String(inp.value || '').replace(/\D/g, '');
            if (!digits) {
                inp.value = '';
                _atualizarBadgeTc(_tcCompSomaServidor, _tcCompValorTc);
                return;
            }
            inp.value = _formatarValorComprovanteDigitosCentavos(digits);
            const n = parseInt(digits, 10) / 100;
            _atualizarBadgeTc(_tcCompSomaServidor + (n > 0 ? n : 0), _tcCompValorTc);
        });
    }

    var tbodyEnviosPendentes = document.getElementById('evoluirTcEnviosPendentes');
    if (tbodyEnviosPendentes) {
        tbodyEnviosPendentes.addEventListener('click', function (ev) {
            const btn = ev.target.closest('.btn-confirmar-envio-boleto');
            if (!btn) return;
            const eid = btn.getAttribute('data-envio-id');
            if (eid) _confirmarEnvioVendedorComoBoleto(eid);
        });
        tbodyEnviosPendentes.addEventListener('input', function (ev) {
            const inp = ev.target.closest('.evoluir-tc-envio-valor');
            if (!inp) return;
            const digits = String(inp.value || '').replace(/\D/g, '');
            const fmt = _formatarValorComprovanteDigitosCentavos(digits);
            if (inp.value !== fmt) {
                inp.value = fmt;
                try {
                    inp.setSelectionRange(fmt.length, fmt.length);
                } catch (e2) { /* ignore */ }
            }
        });
    }

    /* ══════════════════════════════
       SSE — túnel com CRM supervisão (atualização em tempo real)
    ══════════════════════════════ */
    let _evtSourceCrm = null;
    let _sseLastRev = null;
    let _sseDebounceTimer = null;
    let _sseRetryDelayMs = 1000;
    const SSE_RETRY_MAX_MS = 10000;

    function scheduleSseReconnectCrm() {
        const espera = _sseRetryDelayMs;
        _sseRetryDelayMs = Math.min(_sseRetryDelayMs * 2, SSE_RETRY_MAX_MS);
        setTimeout(function () {
            connectSseCrm();
        }, espera);
    }

    function debounceReloadTabelaSse() {
        clearTimeout(_sseDebounceTimer);
        _sseDebounceTimer = setTimeout(function () {
            safeReloadFilaUnificada();
        }, 400);
    }

    function handleSseCrmMessage(ev) {
        try {
            const data = JSON.parse(ev.data);
            if (data.reconnect) {
                if (_evtSourceCrm) {
                    _evtSourceCrm.close();
                    _evtSourceCrm = null;
                }
                scheduleSseReconnectCrm();
                return;
            }
            if (data.changed && data.rev !== _sseLastRev) {
                _sseLastRev = data.rev;
                debounceReloadTabelaSse();
            }
        } catch (e) { /* ignora */ }
    }

    function connectSseCrm() {
        try {
            if (_evtSourceCrm) {
                _evtSourceCrm.close();
            }
            _evtSourceCrm = new EventSource('/siape/api/sse/crm-supervisao/');
            _evtSourceCrm.onopen = function () {
                _sseRetryDelayMs = 1000;
            };
            _evtSourceCrm.onmessage = handleSseCrmMessage;
        } catch (e) { /* SSE indisponível */ }
    }

    /* ══════════════════════════════
       VALIDAÇÃO [7] — EDIÇÃO (2 abas: Dados / Arquivos)
       ------------------------------------------------------------
       Abre o modalEditarDados, pré-popula os inputs via `data-edit-field`
       a partir de `api_get_ficha` (com_historico=0) e lista arquivos via
       `api_get_contrato_midia_arquivos`. Upload e exclusão de arquivos
       reaproveitam os endpoints existentes e o novo
       `api_post_excluir_cliente_arquivo`.
    ══════════════════════════════ */
    const _URL_EDITAR = base + 'contrato/editar-dados/';
    const _URL_EXCLUIR_ARQ = base + 'cliente-arquivo/excluir/';
    let _edContratoId = null;
    let _edTipo = 'contrato';

    // Mapeia valor vindo da ficha para o input data-edit-field. Aceita aliases
    // (ex.: cliente.rg lê `numero_rg`) e tipos simples (string/number/null).
    function _setEditField(path, valor) {
        const inp = document.querySelector('[data-edit-field="' + path + '"]');
        if (!inp) return;
        if (valor === null || valor === undefined) {
            inp.value = '';
            return;
        }
        inp.value = String(valor);
    }

    function _preencherEdicao(d) {
        // d: payload de api_get_ficha. A proposta vem como lista `propostas`
        // (pega-se a primeira); o contrato é um dict único.
        const dp = d.dados_pessoais || {};
        const prop = (Array.isArray(d.propostas) && d.propostas.length > 0) ? d.propostas[0] : {};
        const contrato = d.contrato || {};
        // Cliente (e-mail/telefone: preferência cadastro dinâmico, alinhado à ficha CRM)
        _setEditField('cliente.nome_completo', dp.nome_completo);
        _setEditField('cliente.email', _crmEmailEditPreferido(dp));
        _setEditField('cliente.telefone', _crmTelefoneEditPreferido(dp));
        const elResumo = document.getElementById('editClienteContatosResumo');
        if (elResumo) elResumo.innerHTML = _crmHtmlSecaoContatosCliente(dp);
        _setEditField('cliente.numero_rg', dp.numero_rg);
        _setEditField('cliente.data_nascimento', dp.data_nascimento_iso || dp.data_nascimento || '');
        _setEditField('cliente.nome_mae', dp.nome_mae);
        _setEditField('cliente.nome_pai', dp.nome_pai);
        _setEditField('cliente.naturalidade', dp.naturalidade);
        // Proposta
        _setEditField('proposta.valor_parcela', prop.valor_parcela);
        _setEditField('proposta.valor_af', prop.valor_af);
        _setEditField('proposta.valor_liberado', prop.valor_liberado);
        _setEditField('proposta.coeficiente', prop.coeficiente);
        _setEditField('proposta.prazo', prop.prazo);
        _setEditField('proposta.valor_tc', prop.valor_tc);
        // Contrato
        _setEditField('contrato.numero_contrato', contrato.codigo || contrato.numero_contrato || '');
        _setEditField('contrato.link_formalizacao', contrato.link_formalizacao || '');
    }

    function _edItemArquivoHtml(arq, omitirExcluir) {
        const url = (arq.url || '#');
        const titulo = esc(arq.titulo || arq.name || 'arquivo');
        const meta = esc(arq.data_criacao || '');
        const btnExcluir = omitirExcluir
            ? ''
            : (
                '<button type="button" class="btn btn-sm btn-outline-danger btn-ed-arq-del" data-arquivo-id="' + arq.id + '" title="Excluir">' +
                  '<i class="bx bx-trash"></i>' +
                '</button>'
            );
        return (
            '<li class="list-group-item d-flex align-items-center justify-content-between" data-arquivo-id="' + arq.id + '">' +
              '<div class="d-flex align-items-center gap-2">' +
                '<i class="bx bx-file text-primary"></i>' +
                '<a href="' + url + '" target="_blank" rel="noopener" class="fw-semibold text-decoration-none">' + titulo + '</a>' +
                (meta ? '<span class="text-muted small">· ' + meta + '</span>' : '') +
              '</div>' +
              btnExcluir +
            '</li>'
        );
    }

    function _renderEdicaoArquivos(lista, omitirExcluir) {
        const ul = document.getElementById('editArqLista');
        const vazio = document.getElementById('editArqSemArquivos');
        if (!ul) return;
        ul.innerHTML = '';
        if (!lista || lista.length === 0) {
            if (vazio) vazio.classList.remove('d-none');
            return;
        }
        if (vazio) vazio.classList.add('d-none');
        const ox = !!omitirExcluir;
        lista.forEach(function (a) { ul.insertAdjacentHTML('beforeend', _edItemArquivoHtml(a, ox)); });
    }

    function _carregarEdicaoArquivos(idRegistro) {
        const tipoEd = _edTipo || 'contrato';
        const url = tipoEd === 'solicitacao_dig'
            ? base + 'solicitacao-dig/' + encodeURIComponent(idRegistro) + '/midia-arquivos/'
            : base + 'contrato/' + encodeURIComponent(idRegistro) + '/midia-arquivos/';
        const omitirExcluir = tipoEd === 'solicitacao_dig';
        return getJson(url)
            .then(function (d) {
                if (!d || !d.ok) {
                    _renderEdicaoArquivos([], omitirExcluir);
                    return;
                }
                _renderEdicaoArquivos(d.arquivos || [], omitirExcluir);
            })
            .catch(function () { _renderEdicaoArquivos([], omitirExcluir); });
    }

    /** Lista somente leitura na aba Arquivos do modal Ficha (GET midia-arquivos). */
    function _carregarFichaArquivos(tipo, id) {
        const ul = document.getElementById('fichaListaArquivos');
        const sem = document.getElementById('fichaSemArquivos');
        const midiaTopo = document.getElementById('fichaMidiaResumo');
        if (!ul) return Promise.resolve();
        const t = String(tipo || '');
        if (midiaTopo) midiaTopo.innerHTML = '';
        if (t !== 'contrato' && t !== 'solicitacao_dig') {
            ul.innerHTML = '<li class="list-group-item text-muted small">Lista de arquivos disponível para contrato ou solicitação de digitação na esteira.</li>';
            if (sem) sem.classList.add('d-none');
            return Promise.resolve();
        }
        ul.innerHTML = '<li class="list-group-item text-muted"><span class="spinner-border spinner-border-sm me-1"></span>Carregando arquivos...</li>';
        if (sem) sem.classList.add('d-none');
        const url = t === 'solicitacao_dig'
            ? base + 'solicitacao-dig/' + encodeURIComponent(id) + '/midia-arquivos/'
            : base + 'contrato/' + encodeURIComponent(id) + '/midia-arquivos/';
        return getJson(url).then(function (d) {
            ul.innerHTML = '';
            if (!d || !d.ok) {
                ul.innerHTML = '<li class="list-group-item text-danger small">Não foi possível carregar a lista de arquivos.</li>';
                return;
            }
            const partesTopo = [];
            if (d.pdf_proposta && d.pdf_proposta.url) {
                partesTopo.push(
                    '<a href="' + String(d.pdf_proposta.url).replace(/"/g, '&quot;') + '" target="_blank" rel="noopener" class="me-2">' +
                    '<i class="bx bx-file-pdf"></i> ' + esc(d.pdf_proposta.name || 'PDF da proposta') + '</a>'
                );
            }
            if (t === 'contrato' && d.video && d.video.url) {
                partesTopo.push(
                    '<a href="' + String(d.video.url).replace(/"/g, '&quot;') + '" target="_blank" rel="noopener">' +
                    '<i class="bx bx-video"></i> ' + esc(d.video.name || 'Vídeo') + '</a>'
                );
            }
            if (midiaTopo && partesTopo.length) {
                midiaTopo.innerHTML = '<div class="d-flex flex-wrap gap-2 align-items-center">' + partesTopo.join('') + '</div>';
            }
            const lista = d.arquivos || [];
            if (!lista.length) {
                if (sem) sem.classList.remove('d-none');
                return;
            }
            if (sem) sem.classList.add('d-none');
            lista.forEach(function (a) { ul.insertAdjacentHTML('beforeend', _edItemArquivoHtml(a, true)); });
            if (t === 'contrato') {
                _renderFichaEnviosVendedor(d.envios_comprovante_vendedor || []);
            } else {
                _renderFichaEnviosVendedor([]);
            }
        }).catch(function () {
            ul.innerHTML = '<li class="list-group-item text-danger small">Erro ao carregar arquivos.</li>';
        });
    }

    function _limparEdicaoAlertas() {
        ['editDadosAlerta', 'editArqAlerta'].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) { el.classList.add('d-none'); el.textContent = ''; }
        });
    }

    function _mostrarEdicaoAlerta(alvoId, msg) {
        const el = document.getElementById(alvoId);
        if (!el) return;
        el.textContent = msg || 'Falha ao processar.';
        el.classList.remove('d-none');
    }

    // Com o modal de edição empilhado sobre a ficha, o HTML da ficha não era
    // invalidado após salvar; re-busca e re-renderiza se ainda estiver visível.
    function _recarregarFichaAbertaSeMesmoContrato(registroId) {
        const ctx = window._crmFichaContext;
        if (!ctx || String(ctx.id) !== String(registroId)) return;
        const tipo = ctx.tipo || 'contrato';
        if (tipo !== 'contrato' && tipo !== 'solicitacao_dig') return;
        const elFicha = document.getElementById('modalFicha');
        if (!elFicha || !elFicha.classList.contains('show')) return;
        getJson(
            base + 'ficha/?tipo=' + encodeURIComponent(tipo) + '&id=' + encodeURIComponent(String(registroId)) + '&with_historico=0'
        ).then(function (d) {
            if (d && d.ok) {
                renderFichaConteudo(d);
                _carregarFichaArquivos(tipo, registroId);
            }
        });
    }

    // Exposto no window para ser chamado pelo botão inline do ficha e pelo
    // supervisor (reutilização direta via `window.abrirModalEditarDados`).
    window.abrirModalEditarDados = function abrirModalEditarDados(tipo, id) {
        if (!id) return;
        _edTipo = tipo || 'contrato';
        _edContratoId = id;
        document.getElementById('editDadosContratoId').value = id;
        _limparEdicaoAlertas();
        // Reseta inputs
        document.querySelectorAll('#modalEditarDados [data-edit-field]').forEach(function (i) { i.value = ''; });
        const elResumoEd = document.getElementById('editClienteContatosResumo');
        if (elResumoEd) elResumoEd.innerHTML = '<p class="small text-muted mb-0">Carregando contatos...</p>';
        // Pré-contrato: CRM não permite anexar/excluir arquivos pela API de solicitação (somente leitura).
        const btnArqEd = document.getElementById('btnEditArqEnviar');
        if (btnArqEd) {
            if (_edTipo === 'solicitacao_dig') btnArqEd.classList.add('d-none');
            else btnArqEd.classList.remove('d-none');
        }
        // Força a aba Dados ativa
        const firstTab = document.querySelector('#tabsEditar .nav-link');
        if (firstTab) bootstrap.Tab.getOrCreateInstance(firstTab).show();
        const modal = new bootstrap.Modal(document.getElementById('modalEditarDados'));
        modal.show();
        // Popula campos + lista de arquivos em paralelo.
        getJson(base + 'ficha/?tipo=' + encodeURIComponent(_edTipo) + '&id=' + encodeURIComponent(id) + '&with_historico=0')
            .then(function (d) { if (d && d.ok) _preencherEdicao(d); });
        _carregarEdicaoArquivos(id);
    };

    // Salvar alterações — envia payload seguindo contratos da API expandida.
    on(document.getElementById('btnSalvarEdicaoDados'), 'click', function () {
        const id = _edContratoId || document.getElementById('editDadosContratoId').value;
        if (!id) return;
        _limparEdicaoAlertas();
        const payload = { cliente: {}, proposta: {}, contrato: {} };
        if ((_edTipo || '') === 'solicitacao_dig') {
            payload.solicitacao_digitacao_id = id;
        } else {
            payload.contrato_id = id;
        }
        document.querySelectorAll('#modalEditarDados [data-edit-field]').forEach(function (inp) {
            const caminho = inp.getAttribute('data-edit-field').split('.');
            const bucket = caminho[0];
            const chave = caminho[1];
            const valor = (inp.value || '').trim();
            if (!payload[bucket]) payload[bucket] = {};
            // Envia inclusive vazio quando o campo foi mostrado — permite que o
            // backend limpe um campo previamente preenchido (ex.: link formalização).
            payload[bucket][chave] = valor === '' ? null : valor;
        });
        postJson(_URL_EDITAR, payload).then(function (j) {
            if (!j || !j.ok) {
                const erros = (j && j.campos_invalidos) ? j.campos_invalidos.join('; ') : '';
                _mostrarEdicaoAlerta('editDadosAlerta', (j && j.erro ? j.erro : 'Falha ao salvar') + (erros ? ' — ' + erros : ''));
                return;
            }
            _recarregarFichaAbertaSeMesmoContrato(id);
            bootstrap.Modal.getInstance(document.getElementById('modalEditarDados'))?.hide();
            showToast('Alterações registradas.', 'success');
            safeReloadFilaUnificada();
        }).catch(function () {
            _mostrarEdicaoAlerta('editDadosAlerta', 'Erro de comunicação com o servidor.');
        });
    });

    // Upload de arquivo na aba Arquivos
    on(document.getElementById('btnEditArqEnviar'), 'click', function () {
        const id = _edContratoId || document.getElementById('editDadosContratoId').value;
        if (!id) return;
        if ((_edTipo || '') === 'solicitacao_dig') {
            _mostrarEdicaoAlerta('editArqAlerta', 'Anexar arquivo só após gerar o contrato na esteira.');
            return;
        }
        const fileInp = document.getElementById('editArqInputFile');
        const titInp = document.getElementById('editArqInputTitulo');
        const f = fileInp && fileInp.files && fileInp.files[0];
        if (!f) {
            _mostrarEdicaoAlerta('editArqAlerta', 'Selecione um arquivo para anexar.');
            return;
        }
        const fd = new FormData();
        fd.append('arquivo', f);
        if (titInp && titInp.value.trim()) fd.append('titulo', titInp.value.trim());
        postMultipart(base + 'contrato/' + encodeURIComponent(id) + '/cliente-arquivo/', fd).then(function (j) {
            if (!j || !j.ok) {
                _mostrarEdicaoAlerta('editArqAlerta', (j && j.erro) || 'Falha ao enviar arquivo.');
                return;
            }
            if (fileInp) fileInp.value = '';
            if (titInp) titInp.value = '';
            showToast('Arquivo anexado.', 'success');
            _carregarEdicaoArquivos(id);
        }).catch(function () {
            _mostrarEdicaoAlerta('editArqAlerta', 'Erro de comunicação ao enviar arquivo.');
        });
    });

    // Excluir arquivo — delegado no <ul> da lista
    on(document.getElementById('editArqLista'), 'click', function (ev) {
        const btn = ev.target.closest('.btn-ed-arq-del');
        if (!btn) return;
        const arquivoId = btn.getAttribute('data-arquivo-id');
        const id = _edContratoId || document.getElementById('editDadosContratoId').value;
        if (!id || !arquivoId) return;
        if ((_edTipo || '') === 'solicitacao_dig') {
            _mostrarEdicaoAlerta('editArqAlerta', 'Exclusão de arquivo só após gerar o contrato na esteira.');
            return;
        }
        if (!confirm('Excluir este arquivo? Esta ação é irreversível.')) return;
        postJson(_URL_EXCLUIR_ARQ, { contrato_id: id, arquivo_id: arquivoId }).then(function (j) {
            if (!j || !j.ok) {
                _mostrarEdicaoAlerta('editArqAlerta', (j && j.erro) || 'Falha ao excluir arquivo.');
                return;
            }
            showToast('Arquivo excluído.', 'success');
            _carregarEdicaoArquivos(id);
        }).catch(function () {
            _mostrarEdicaoAlerta('editArqAlerta', 'Erro de comunicação ao excluir arquivo.');
        });
    });

    /* ══════════════════════════════
       Validação [9] — Pendências (modal operacional + lista + multi-tipo)
    ══════════════════════════════ */
    function _pendenciaTiposSelecionados() {
        const ids = ['pendenciaTipoDc', 'pendenciaTipoProp', 'pendenciaTipoArq'];
        const map = { pendenciaTipoDc: 'DADOS_CLIENTE', pendenciaTipoProp: 'DADOS_PROPOSTA', pendenciaTipoArq: 'FALTA_ARQUIVO' };
        const out = [];
        ids.forEach(function (id) {
            const el = document.getElementById(id);
            if (el && el.checked) out.push(map[id]);
        });
        return out;
    }

    function _renderListaPendenciasModal(pendencias) {
        const ul = document.getElementById('pendenciasLista');
        const vazio = document.getElementById('pendenciasVazia');
        if (!ul) return;
        ul.innerHTML = '';
        const lista = (pendencias || []).filter(function (p) { return !p.resolvido; });
        if (!lista.length) {
            if (vazio) vazio.classList.remove('d-none');
            return;
        }
        if (vazio) vazio.classList.add('d-none');
        lista.forEach(function (p) {
            const li = document.createElement('li');
            li.className = 'list-group-item small d-flex justify-content-between align-items-start gap-2';
            li.innerHTML =
                '<div><span class="fw-semibold">' + esc(p.tipo_label || p.tipo) + '</span>' +
                '<div class="text-muted mt-1">' + esc(p.observacao || '') + '</div>' +
                '<div class="text-muted" style="font-size:0.75rem">Por ' + esc(p.criado_por || '') + ' · ' + esc(p.criado_em || '') + '</div></div>' +
                '<button type="button" class="btn btn-sm btn-outline-secondary btn-pendencia-resolver flex-shrink-0" data-acess="SS35" data-pendencia-id="' +
                String(p.id) +
                '">Resolver</button>';
            ul.appendChild(li);
        });
    }

    function abrirModalPendenciasContrato(contratoId) {
        const hid = document.getElementById('pendenciasContratoId');
        const al = document.getElementById('pendenciaAlerta');
        const slotCont = document.getElementById('pendenciasClienteContatos');
        if (al) {
            al.classList.add('d-none');
            al.textContent = '';
        }
        if (hid) hid.value = String(contratoId || '');
        if (slotCont) {
            slotCont.innerHTML = '<p class="small text-muted mb-0"><span class="spinner-border spinner-border-sm me-1"></span>Carregando contatos do cliente...</p>';
        }
        ['pendenciaTipoDc', 'pendenciaTipoProp', 'pendenciaTipoArq'].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.checked = false;
        });
        const obs = document.getElementById('pendenciaObs');
        if (obs) obs.value = '';
        const cidEnc = encodeURIComponent(String(contratoId));
        Promise.all([
            getJson(base + 'pendencias/?contrato_id=' + cidEnc),
            getJson(base + 'ficha/?tipo=contrato&id=' + cidEnc + '&with_historico=0').catch(function () { return null; }),
        ]).then(function (arr) {
            const d = arr[0];
            const dFicha = arr[1];
            if (slotCont) {
                if (dFicha && dFicha.ok && dFicha.dados_pessoais) {
                    slotCont.innerHTML = _crmHtmlSecaoContatosCliente(dFicha.dados_pessoais);
                } else {
                    slotCont.innerHTML = '<p class="small text-muted mb-0">Contatos do cliente indisponíveis no momento.</p>';
                }
            }
            if (!d || !d.ok) {
                _renderListaPendenciasModal([]);
                showToast((d && d.erro) || 'Erro ao listar pendências.', 'danger');
            } else {
                _renderListaPendenciasModal(d.pendencias || []);
            }
            const m = document.getElementById('modalPendencias');
            if (m) bootstrap.Modal.getOrCreateInstance(m).show();
        }).catch(function () {
            if (slotCont) slotCont.innerHTML = '<p class="small text-muted mb-0">Contatos do cliente indisponíveis no momento.</p>';
            _renderListaPendenciasModal([]);
            showToast('Erro ao carregar pendências.', 'danger');
            const m = document.getElementById('modalPendencias');
            if (m) bootstrap.Modal.getOrCreateInstance(m).show();
        });
    }

    on(document.getElementById('pendenciasLista'), 'click', function (ev) {
        const btn = ev.target.closest('.btn-pendencia-resolver');
        if (!btn) return;
        const pid = btn.getAttribute('data-pendencia-id');
        if (!pid) return;
        postJson(base + 'pendencia/resolver/', { pendencia_id: parseInt(pid, 10) }).then(function (j) {
            if (!j || !j.ok) {
                showToast((j && j.erro) || 'Não foi possível resolver.', 'danger');
                return;
            }
            showToast('Pendência marcada como resolvida.', 'success');
            const cid = document.getElementById('pendenciasContratoId');
            if (cid && cid.value) {
                getJson(base + 'pendencias/?contrato_id=' + encodeURIComponent(cid.value)).then(function (d) {
                    if (d && d.ok) _renderListaPendenciasModal(d.pendencias || []);
                });
            }
            safeReloadFilaUnificada();
        }).catch(function () {
            showToast('Erro de comunicação.', 'danger');
        });
    });

    on(document.getElementById('btnSalvarPendencia'), 'click', function () {
        const cidEl = document.getElementById('pendenciasContratoId');
        const al = document.getElementById('pendenciaAlerta');
        const cid = cidEl ? cidEl.value : '';
        const tipos = _pendenciaTiposSelecionados();
        const obs = (document.getElementById('pendenciaObs') && document.getElementById('pendenciaObs').value || '').trim();
        if (!cid) {
            if (al) {
                al.textContent = 'Contrato inválido.';
                al.classList.remove('d-none');
            }
            return;
        }
        if (!tipos.length) {
            if (al) {
                al.textContent = 'Selecione ao menos um tipo de pendência.';
                al.classList.remove('d-none');
            }
            return;
        }
        if (!obs) {
            if (al) {
                al.textContent = 'Observação é obrigatória.';
                al.classList.remove('d-none');
            }
            return;
        }
        if (al) al.classList.add('d-none');
        postJson(base + 'pendencia/', { contrato_id: cid, tipos: tipos, observacao: obs }).then(function (j) {
            if (!j || !j.ok) {
                if (al) {
                    al.textContent = (j && j.erro) || 'Falha ao registrar.';
                    al.classList.remove('d-none');
                }
                return;
            }
            bootstrap.Modal.getInstance(document.getElementById('modalPendencias'))?.hide();
            showToast('Pendência(s) registrada(s).', 'success');
            safeReloadFilaUnificada();
        }).catch(function () {
            if (al) {
                al.textContent = 'Erro de comunicação.';
                al.classList.remove('d-none');
            }
        });
    });

    const btnFichaPendEl = document.getElementById('btnFichaPendencias');
    if (btnFichaPendEl) {
        btnFichaPendEl.addEventListener('click', function () {
            const id = this.getAttribute('data-contrato-id') || '';
            if (!id) return;
            blurFocoAtivo();
            bootstrap.Modal.getInstance(document.getElementById('modalFicha'))?.hide();
            setTimeout(function () {
                abrirModalPendenciasContrato(id);
            }, 200);
        });
    }

    /* ══════════════════════════════
       INIT
    ══════════════════════════════ */
    safeReloadFilaUnificada();
    connectSseCrm();
})();
