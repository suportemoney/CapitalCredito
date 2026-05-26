/* ================================================
   CATÁLOGOS CONTRATOS — JS
   Template: contratos/v2/config.html
   ================================================ */
(function () {
    'use strict';

    const base = '/contratos/api/v2/config/';
    let cache = { bancos: [], convenios: [], produtos: [], tabelas_cms: [] };
    const isSuperuser = document.getElementById('config-container').dataset.superuser === 'true';
    let cmsSortCampo = '';
    let cmsSortDir = 'asc';

    /* ── CSRF ── */
    function csrf() {
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        if (m) return m[1];
        const inp = document.querySelector('[name=csrfmiddlewaretoken]');
        return inp ? inp.value : '';
    }

    /* ── Fetch JSON ── */
    function reqJson(url, opts) {
        const o = { credentials: 'same-origin', ...opts };
        o.headers = Object.assign({ 'X-CSRFToken': csrf() }, o.headers || {});
        return fetch(url, o).then(function (r) { return r.json(); });
    }

    /* ── Consulta de dependências (TabelaCms) antes de inativar ──
       Usada pelos handlers de inativação para alertar o operador quando
       o item do catálogo está em uso por tabelas CMS ativas. Retorna uma
       Promise<boolean>: true = continuar, false = cancelar.
    */
    function confirmarInativacaoComDependencias(tipo, rotulo, id, atualmenteAtivo, msgPadrao) {
        if (!atualmenteAtivo) {
            // Reativação não precisa de alerta — delega ao confirm padrão.
            return Promise.resolve(confirm(msgPadrao));
        }
        return reqJson(base + 'dependencias/?tipo=' + tipo + '&id=' + id, { method: 'GET' })
            .then(function (r) {
                if (r && r.ok && r.ativas > 0) {
                    const msg = 'Este ' + rotulo + ' é referenciado por ' + r.ativas +
                                ' tabela(s) CMS ativa(s). Inativá-lo pode quebrar o filtro de propostas.\n\n' +
                                'Deseja continuar mesmo assim?';
                    return confirm(msg);
                }
                return confirm(msgPadrao);
            })
            .catch(function () {
                // Se a consulta falhar, mantém comportamento original.
                return confirm(msgPadrao);
            });
    }

    /* ── Toast ── */
    function showToast(msg, type) {
        const el = document.getElementById('toastMsg');
        const colors = { success: '#198754', danger: '#dc3545', warning: '#fd7e14', info: '#0dcaf0' };
        el.style.background = colors[type] || colors.info;
        document.getElementById('toastBody').textContent = msg;
        bootstrap.Toast.getOrCreateInstance(el, { delay: 3000 }).show();
    }

    /* ── Badges de status ── */
    function badgeAtivo(on) {
        return on
            ? '<span class="badge-ativo"><i class=\'bx bx-check\'></i> Ativo</span>'
            : '<span class="badge-inativo"><i class=\'bx bx-x\'></i> Inativo</span>';
    }

    /* ── escapeHtml ── */
    function esc(s) {
        if (!s) return '';
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    /* ── Atualiza contadores nas abas ── */
    function updateCounters() {
        document.getElementById('ctBanco').textContent = cache.bancos.length;
        document.getElementById('ctConv').textContent  = cache.convenios.length;
        document.getElementById('ctProd').textContent  = cache.produtos.length;
        document.getElementById('ctCms').textContent   = cache.tabelas_cms.length;
    }

    /* ── Busca client-side ── */
    function hookSearch(inputId, tbodyId) {
        document.getElementById(inputId).addEventListener('input', function () {
            const q = this.value.toLowerCase();
            document.getElementById(tbodyId).querySelectorAll('tr[data-titulo]').forEach(function (tr) {
                tr.style.display = tr.getAttribute('data-titulo').toLowerCase().includes(q) ? '' : 'none';
            });
        });
    }

    /* ── Filtros e ordenação — Tabelas CMS ── */
    function normTxt(s) {
        return (s || '').toString().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }

    function parseTaxaNum(val) {
        if (val == null || val === '') return null;
        const n = parseFloat(String(val).replace(',', '.'));
        return isNaN(n) ? null : n;
    }

    function lerFiltrosCms() {
        const el = function (id) { return document.getElementById(id); };
        const buscaGlobal = (el('searchCms') && el('searchCms').value.trim()) || '';
        const tituloCol = (el('filtCmsTitulo') && el('filtCmsTitulo').value.trim()) || '';
        return {
            tituloCol: tituloCol,
            buscaGlobal: buscaGlobal,
            banco: (el('filtCmsBanco') && el('filtCmsBanco').value.trim()) || '',
            convenio: (el('filtCmsConvenio') && el('filtCmsConvenio').value.trim()) || '',
            produto: (el('filtCmsProduto') && el('filtCmsProduto').value.trim()) || '',
            recMin: el('filtCmsRecMin') ? el('filtCmsRecMin').value.trim() : '',
            recMax: el('filtCmsRecMax') ? el('filtCmsRecMax').value.trim() : '',
            repMin: el('filtCmsRepMin') ? el('filtCmsRepMin').value.trim() : '',
            repMax: el('filtCmsRepMax') ? el('filtCmsRepMax').value.trim() : '',
            classif: (el('filtCmsClassif') && el('filtCmsClassif').value) || '',
            status: (el('filtCmsStatus') && el('filtCmsStatus').value) || ''
        };
    }

    function passaFaixaTaxa(valorItem, minStr, maxStr) {
        const temMin = minStr !== '';
        const temMax = maxStr !== '';
        if (!temMin && !temMax) return true;
        const num = parseTaxaNum(valorItem);
        if (num === null) return false;
        if (temMin) {
            const min = parseFloat(minStr);
            if (!isNaN(min) && num < min) return false;
        }
        if (temMax) {
            const max = parseFloat(maxStr);
            if (!isNaN(max) && num > max) return false;
        }
        return true;
    }

    function passaFiltroCms(item, filtros) {
        const alvoTitulo = normTxt(item.titulo);
        if (filtros.buscaGlobal && alvoTitulo.indexOf(normTxt(filtros.buscaGlobal)) < 0) return false;
        if (filtros.tituloCol && alvoTitulo.indexOf(normTxt(filtros.tituloCol)) < 0) return false;
        if (filtros.banco && normTxt(item.banco_titulo).indexOf(normTxt(filtros.banco)) < 0) return false;
        if (filtros.convenio && normTxt(item.convenio_titulo).indexOf(normTxt(filtros.convenio)) < 0) return false;
        if (filtros.produto && normTxt(item.produto_titulo).indexOf(normTxt(filtros.produto)) < 0) return false;
        if (!passaFaixaTaxa(item.taxa_recebido, filtros.recMin, filtros.recMax)) return false;
        if (!passaFaixaTaxa(item.taxa_repasse, filtros.repMin, filtros.repMax)) return false;
        if (filtros.classif) {
            const cls = (item.classificador_banco || 'M1').toString().toUpperCase();
            if (cls !== filtros.classif.toUpperCase()) return false;
        }
        if (filtros.status !== '') {
            const ativo = !!item.status;
            if (filtros.status === '1' && !ativo) return false;
            if (filtros.status === '0' && ativo) return false;
        }
        return true;
    }

    function valorOrdenacaoCms(item, campo) {
        if (campo === 'id') return item.id;
        if (campo === 'status') return item.status ? 1 : 0;
        if (campo === 'taxa_recebido' || campo === 'taxa_repasse') {
            const v = parseTaxaNum(item[campo]);
            return v === null ? -Infinity : v;
        }
        if (campo === 'classificador_banco') return (item.classificador_banco || 'M1').toString().toUpperCase();
        return (item[campo] || '').toString();
    }

    function compararCms(a, b, campo, dir) {
        const fator = dir === 'asc' ? 1 : -1;
        const va = valorOrdenacaoCms(a, campo);
        const vb = valorOrdenacaoCms(b, campo);
        if (campo === 'id' || campo === 'status' || campo === 'taxa_recebido' || campo === 'taxa_repasse') {
            if (va < vb) return -1 * fator;
            if (va > vb) return 1 * fator;
            return 0;
        }
        const sa = normTxt(va);
        const sb = normTxt(vb);
        if (sa < sb) return -1 * fator;
        if (sa > sb) return 1 * fator;
        return 0;
    }

    function aplicarFiltrosOrdenacaoCms(lista) {
        const filtros = lerFiltrosCms();
        let out = (lista || []).filter(function (item) { return passaFiltroCms(item, filtros); });
        if (cmsSortCampo) {
            out = out.slice().sort(function (a, b) {
                return compararCms(a, b, cmsSortCampo, cmsSortDir);
            });
        }
        return out;
    }

    function atualizarIconesOrdenacaoCms() {
        const thead = document.getElementById('theadTabelaCms');
        if (!thead) return;
        thead.querySelectorAll('.cms-th-sortable').forEach(function (th) {
            th.classList.remove('sort-asc', 'sort-desc');
            const icon = th.querySelector('.cms-sort-icon');
            if (icon) {
                icon.classList.remove('bx-sort-up', 'bx-sort-down');
                icon.classList.add('bx-sort');
            }
        });
        if (!cmsSortCampo) return;
        const ativo = thead.querySelector('.cms-th-sortable[data-sort="' + cmsSortCampo + '"]');
        if (!ativo) return;
        ativo.classList.add(cmsSortDir === 'asc' ? 'sort-asc' : 'sort-desc');
        const iconAtivo = ativo.querySelector('.cms-sort-icon');
        if (iconAtivo) {
            iconAtivo.classList.remove('bx-sort');
            iconAtivo.classList.add(cmsSortDir === 'asc' ? 'bx-sort-up' : 'bx-sort-down');
        }
    }

    function cmsTemFiltrosAtivos() {
        const f = lerFiltrosCms();
        return !!(f.buscaGlobal || f.tituloCol || f.banco || f.convenio || f.produto ||
            f.recMin || f.recMax || f.repMin || f.repMax || f.classif || f.status !== '');
    }

    /* ================================================
       RENDER FUNCTIONS
    ================================================ */

    function renderBancos() {
        const tb = document.getElementById('tbodyBanco');
        tb.innerHTML = '';
        if (!cache.bancos.length) {
            tb.innerHTML = '<tr><td colspan="5" class="empty-state"><i class=\'bx bx-building\'></i>Nenhum banco cadastrado</td></tr>';
            return;
        }
        cache.bancos.forEach(function (x) {
            const tr = document.createElement('tr');
            tr.setAttribute('data-titulo', x.titulo || '');
            const toggleLbl  = x.status ? 'Desativar' : 'Ativar';
            const toggleIcon = x.status ? 'bx-toggle-right' : 'bx-toggle-left';
            const toggleCls  = x.status ? 'btn-outline-warning' : 'btn-outline-success';
            tr.innerHTML =
                '<td class="text-muted small">#' + x.id + '</td>' +
                '<td class="fw-semibold">' + esc(x.titulo) + '</td>' +
                '<td class="text-muted small">' + esc(x.codigo || '—') + '</td>' +
                '<td>' + badgeAtivo(x.status) + '</td>' +
                '<td class="text-end">' +
                  '<button type="button" class="btn btn-acao btn-outline-primary me-1 btn-ed-banco" data-id="' + x.id + '" title="Editar"><i class=\'bx bx-pencil\'></i></button>' +
                  '<button type="button" class="btn btn-acao ' + toggleCls + ' btn-inat-banco me-1" data-id="' + x.id + '" title="' + toggleLbl + '"><i class=\'bx ' + toggleIcon + '\'></i></button>' +
                  '<button type="button" class="btn btn-acao btn-outline-danger btn-del-banco" data-id="' + x.id + '" title="Excluir definitivo"><i class=\'bx bx-trash\'></i></button>' +
                '</td>';
            tb.appendChild(tr);
        });
    }

    function renderConvenios() {
        const tb = document.getElementById('tbodyConvenio');
        tb.innerHTML = '';
        if (!cache.convenios.length) {
            tb.innerHTML = '<tr><td colspan="4" class="empty-state"><i class=\'bx bx-handshake\'></i>Nenhum convênio cadastrado</td></tr>';
            return;
        }
        cache.convenios.forEach(function (x) {
            const tr = document.createElement('tr');
            tr.setAttribute('data-titulo', x.titulo || '');
            const toggleLbl  = x.status ? 'Desativar' : 'Ativar';
            const toggleIcon = x.status ? 'bx-toggle-right' : 'bx-toggle-left';
            const toggleCls  = x.status ? 'btn-outline-warning' : 'btn-outline-success';
            tr.innerHTML =
                '<td class="text-muted small">#' + x.id + '</td>' +
                '<td class="fw-semibold">' + esc(x.titulo) + '</td>' +
                '<td>' + badgeAtivo(x.status) + '</td>' +
                '<td class="text-end">' +
                  '<button type="button" class="btn btn-acao btn-outline-primary me-1 btn-ed-conv" data-id="' + x.id + '" title="Editar"><i class=\'bx bx-pencil\'></i></button>' +
                  '<button type="button" class="btn btn-acao ' + toggleCls + ' btn-inat-conv me-1" data-id="' + x.id + '" title="' + toggleLbl + '"><i class=\'bx ' + toggleIcon + '\'></i></button>' +
                  '<button type="button" class="btn btn-acao btn-outline-danger btn-del-conv" data-id="' + x.id + '" title="Excluir definitivo"><i class=\'bx bx-trash\'></i></button>' +
                '</td>';
            tb.appendChild(tr);
        });
    }

    function renderProdutos() {
        const tb = document.getElementById('tbodyProduto');
        tb.innerHTML = '';
        if (!cache.produtos.length) {
            tb.innerHTML = '<tr><td colspan="5" class="empty-state"><i class=\'bx bx-package\'></i>Nenhum produto cadastrado</td></tr>';
            return;
        }
        cache.produtos.forEach(function (x) {
            const tr = document.createElement('tr');
            tr.setAttribute('data-titulo', x.titulo || '');
            const toggleLbl  = x.status ? 'Desativar' : 'Ativar';
            const toggleIcon = x.status ? 'bx-toggle-right' : 'bx-toggle-left';
            const toggleCls  = x.status ? 'btn-outline-warning' : 'btn-outline-success';
            let flagsHtml = '<span class="text-muted small">—</span>';
            const badges = [];
            if (x.flag_port_mais_refin) {
                badges.push('<span class="badge bg-warning-subtle text-warning">P+R</span>');
            }
            if (x.flag_refin_da_port) {
                badges.push('<span class="badge bg-info-subtle text-info">R/P</span>');
            }
            if (badges.length) {
                flagsHtml = badges.join(' ');
            }
            tr.innerHTML =
                '<td class="text-muted small">#' + x.id + '</td>' +
                '<td class="fw-semibold">' + esc(x.titulo) + '</td>' +
                '<td>' + flagsHtml + '</td>' +
                '<td>' + badgeAtivo(x.status) + '</td>' +
                '<td class="text-end">' +
                  '<button type="button" class="btn btn-acao btn-outline-primary me-1 btn-ed-prod" data-id="' + x.id + '" title="Editar"><i class=\'bx bx-pencil\'></i></button>' +
                  '<button type="button" class="btn btn-acao ' + toggleCls + ' btn-inat-prod me-1" data-id="' + x.id + '" title="' + toggleLbl + '"><i class=\'bx ' + toggleIcon + '\'></i></button>' +
                  '<button type="button" class="btn btn-acao btn-outline-danger btn-del-prod" data-id="' + x.id + '" title="Excluir definitivo"><i class=\'bx bx-trash\'></i></button>' +
                '</td>';
            tb.appendChild(tr);
        });
    }

    // Retorna um badge colorido para o Classificador Banco (M1/M2/M3)
    function badgeClassificador(cls) {
        const v = (cls || 'M1').toString().toUpperCase();
        const map = {
            'M1': { cls: 'bg-success-subtle text-success', title: 'M1 (100%)' },
            'M2': { cls: 'bg-warning-subtle text-warning', title: 'M2 (50%)'  },
            'M3': { cls: 'bg-danger-subtle text-danger',   title: 'M3 (0%)'   }
        };
        const info = map[v] || map['M1'];
        return '<span class="badge ' + info.cls + '" title="' + info.title + '">' + v + '</span>';
    }

    function renderTabelas() {
        const tb = document.getElementById('tbodyTabela');
        tb.innerHTML = '';
        atualizarIconesOrdenacaoCms();
        if (!cache.tabelas_cms.length) {
            tb.innerHTML = '<tr><td colspan="9" class="empty-state"><i class=\'bx bx-table\'></i>Nenhuma tabela cadastrada</td></tr>';
            return;
        }
        const lista = aplicarFiltrosOrdenacaoCms(cache.tabelas_cms);
        if (!lista.length) {
            const msg = cmsTemFiltrosAtivos()
                ? 'Nenhum resultado para os filtros aplicados'
                : 'Nenhuma tabela cadastrada';
            tb.innerHTML = '<tr><td colspan="9" class="empty-state"><i class=\'bx bx-table\'></i>' + msg + '</td></tr>';
            return;
        }
        lista.forEach(function (x) {
            const tr = document.createElement('tr');
            tr.setAttribute('data-titulo', x.titulo || '');
            const tx = (x.taxa_recebido || '—') + ' / ' + (x.taxa_repasse || '—') + ' / ' + (x.taxa_plastico || '—');
            tr.innerHTML =
                '<td class="text-muted small">#' + x.id + '</td>' +
                '<td class="fw-semibold">' + esc(x.titulo) + '</td>' +
                '<td>' + esc(x.banco_titulo) + '</td>' +
                '<td>' + esc(x.convenio_titulo) + '</td>' +
                '<td>' + esc(x.produto_titulo) + '</td>' +
                '<td class="small text-muted font-monospace">' + esc(tx) + '</td>' +
                '<td>' + badgeClassificador(x.classificador_banco) + '</td>' +
                '<td>' + badgeAtivo(x.status) + '</td>' +
                '<td class="text-end">' +
                  '<button type="button" class="btn btn-acao btn-outline-primary me-1 btn-ed-tab" data-id="' + x.id + '" title="Editar"><i class=\'bx bx-pencil\'></i></button>' +
                  '<button type="button" class="btn btn-acao btn-outline-danger btn-del-tab" data-id="' + x.id + '" title="Excluir"><i class=\'bx bx-trash\'></i></button>' +
                '</td>';
            tb.appendChild(tr);
        });
    }

    /* ================================================
       LOAD
    ================================================ */
    function loadResumo() {
        return reqJson(base + 'resumo/', { headers: { 'Accept': 'application/json' } }).then(function (d) {
            if (!d.ok) { showToast(d.erro || 'Erro ao carregar dados.', 'danger'); return; }
            cache.bancos       = d.bancos       || [];
            cache.convenios    = d.convenios    || [];
            cache.produtos     = d.produtos     || [];
            cache.tabelas_cms  = d.tabelas_cms  || [];
            renderBancos();
            renderConvenios();
            renderProdutos();
            renderTabelas();
            updateCounters();
        });
    }

    /* ================================================
       SELECTS DA TABELA CMS
    ================================================ */
    function fillSelectsTabela(selectedBanco, selectedConv, selectedProd) {
        // Só itens ativos no select; na edição, inclui o registro selecionado se estiver inativo (exibe com sufixo).
        function opcoesParaSelect(listaCompleta, selId) {
            const ativos = (listaCompleta || []).filter(function (x) { return x.status; });
            if (selId == null || selId === '') {
                return ativos;
            }
            const idStr = String(selId);
            const selecionado = (listaCompleta || []).find(function (x) { return String(x.id) === idStr; });
            if (selecionado && !selecionado.status) {
                const jaIncluso = ativos.some(function (x) { return String(x.id) === idStr; });
                if (!jaIncluso) {
                    return ativos.concat([selecionado]);
                }
            }
            return ativos;
        }
        function fill(sel, listaCompleta, selId) {
            const list = opcoesParaSelect(listaCompleta, selId);
            sel.innerHTML = '';
            const opt0 = document.createElement('option');
            opt0.value = '';
            opt0.textContent = list.length ? '— selecione —' : '(cadastre itens primeiro)';
            sel.appendChild(opt0);
            list.forEach(function (x) {
                const o = document.createElement('option');
                o.value = x.id;
                o.textContent = x.titulo + (x.status ? '' : ' (inativo)');
                sel.appendChild(o);
            });
            if (selId != null && selId !== '') sel.value = String(selId);
            else if (list.length === 1) sel.selectedIndex = 1;
        }
        fill(document.getElementById('tabelaBancoId'),    cache.bancos,    selectedBanco);
        fill(document.getElementById('tabelaConvenioId'), cache.convenios, selectedConv);
        fill(document.getElementById('tabelaProdutoId'),  cache.produtos,  selectedProd);
    }

    /* ================================================
       OPEN MODALS
    ================================================ */
    function openBanco(item) {
        document.getElementById('bancoEditId').value              = item ? item.id : '';
        document.getElementById('bancoTitulo').value              = item ? item.titulo : '';
        document.getElementById('bancoCodigo').value              = item ? (item.codigo || '') : '';
        document.getElementById('bancoAtivo').checked             = item ? !!item.status : true;
        document.getElementById('modalBancoTitle').textContent    = item ? 'Editar Banco' : 'Novo Banco';
        new bootstrap.Modal(document.getElementById('modalBanco')).show();
    }

    function openConvenio(item) {
        document.getElementById('convenioEditId').value           = item ? item.id : '';
        document.getElementById('convenioTitulo').value           = item ? item.titulo : '';
        document.getElementById('convenioAtivo').checked          = item ? !!item.status : true;
        document.getElementById('modalConvTitle').textContent     = item ? 'Editar Convênio' : 'Novo Convênio';
        new bootstrap.Modal(document.getElementById('modalConvenio')).show();
    }

    function openProduto(item) {
        document.getElementById('produtoEditId').value            = item ? item.id : '';
        document.getElementById('produtoTitulo').value            = item ? item.titulo : '';
        document.getElementById('produtoAtivo').checked           = item ? !!item.status : true;
        document.getElementById('produtoFlagPortRefin').checked   = item ? !!item.flag_port_mais_refin : false;
        document.getElementById('produtoFlagRefinDaPort').checked = item ? !!item.flag_refin_da_port : false;
        document.getElementById('modalProdTitle').textContent     = item ? 'Editar Produto' : 'Novo Produto';
        new bootstrap.Modal(document.getElementById('modalProduto')).show();
    }

    document.getElementById('produtoFlagPortRefin').addEventListener('change', function () {
        if (this.checked) {
            document.getElementById('produtoFlagRefinDaPort').checked = false;
        }
    });
    document.getElementById('produtoFlagRefinDaPort').addEventListener('change', function () {
        if (this.checked) {
            document.getElementById('produtoFlagPortRefin').checked = false;
        }
    });

    function openTabela(item) {
        document.getElementById('tabelaEditId').value             = item ? item.id : '';
        document.getElementById('tabelaTitulo').value             = item ? item.titulo : '';
        document.getElementById('modalCmsTitle').textContent      = item ? 'Editar Tabela CMS' : 'Nova Tabela CMS';
        // Normaliza o classificador para sempre cair em M1/M2/M3; default M1 (regra de negócio)
        const selectClassif = document.getElementById('tabelaClassificadorBanco');
        if (item) {
            fillSelectsTabela(item.banco_id, item.convenio_id, item.produto_id);
            document.getElementById('tabelaTxRec').value   = item.taxa_recebido  != null ? item.taxa_recebido  : '';
            document.getElementById('tabelaTxRep').value   = item.taxa_repasse   != null ? item.taxa_repasse   : '';
            document.getElementById('tabelaTxPla').value   = item.taxa_plastico  != null ? item.taxa_plastico  : '';
            document.getElementById('tabelaAtivo').checked = !!item.status;
            if (selectClassif) {
                const cls = (item.classificador_banco || 'M1').toString().toUpperCase();
                selectClassif.value = ['M1', 'M2', 'M3'].indexOf(cls) >= 0 ? cls : 'M1';
            }
        } else {
            fillSelectsTabela(null, null, null);
            document.getElementById('tabelaTxRec').value   = '';
            document.getElementById('tabelaTxRep').value   = '';
            document.getElementById('tabelaTxPla').value   = '';
            document.getElementById('tabelaAtivo').checked = true;
            if (selectClassif) selectClassif.value = 'M1';
        }
        new bootstrap.Modal(document.getElementById('modalTabela')).show();
    }

    /* ================================================
       EVENTOS — botões globais
    ================================================ */
    document.getElementById('btnRefreshAll').onclick      = function () { loadResumo().then(function () { showToast('Dados atualizados.', 'success'); }); };
    document.querySelector('.btn-novo-banco').onclick     = function () { openBanco(null); };
    document.querySelector('.btn-novo-convenio').onclick  = function () { openConvenio(null); };
    document.querySelector('.btn-novo-produto').onclick   = function () { openProduto(null); };
    document.querySelector('.btn-novo-tabela').onclick    = function () { openTabela(null); };

    /* ================================================
       EVENTOS — tabelas (delegação)
    ================================================ */
    document.getElementById('tbodyBanco').addEventListener('click', function (e) {
        const btn = e.target.closest('button[data-id]');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        if (btn.classList.contains('btn-ed-banco')) {
            const b = cache.bancos.find(function (x) { return String(x.id) === id; });
            if (b) openBanco(b);
        }
        if (btn.classList.contains('btn-inat-banco')) {
            const b   = cache.bancos.find(function (x) { return String(x.id) === id; });
            const msg = b && b.status ? 'Desativar este banco?' : 'Ativar este banco?';
            confirmarInativacaoComDependencias('banco', 'banco', id, !!(b && b.status), msg).then(function (ok) {
                if (!ok) return;
                reqJson(base + 'banco/' + id + '/', { method: 'DELETE' }).then(function (r) {
                    showToast(r.ok ? 'Banco atualizado.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                    if (r.ok) loadResumo();
                });
            });
        }
        if (btn.classList.contains('btn-del-banco')) {
            if (!confirm('Excluir banco DEFINITIVAMENTE? Essa ação não pode ser desfeita.')) return;
            reqJson(base + 'banco/' + id + '/excluir/', { method: 'DELETE' }).then(function (r) {
                showToast(r.ok ? 'Banco excluído.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                if (r.ok) loadResumo();
            });
        }
    });

    document.getElementById('tbodyConvenio').addEventListener('click', function (e) {
        const btn = e.target.closest('button[data-id]');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        if (btn.classList.contains('btn-ed-conv')) {
            const b = cache.convenios.find(function (x) { return String(x.id) === id; });
            if (b) openConvenio(b);
        }
        if (btn.classList.contains('btn-inat-conv')) {
            const b   = cache.convenios.find(function (x) { return String(x.id) === id; });
            const msg = b && b.status ? 'Desativar este convênio?' : 'Ativar este convênio?';
            confirmarInativacaoComDependencias('convenio', 'convênio', id, !!(b && b.status), msg).then(function (ok) {
                if (!ok) return;
                reqJson(base + 'convenio/' + id + '/', { method: 'DELETE' }).then(function (r) {
                    showToast(r.ok ? 'Convênio atualizado.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                    if (r.ok) loadResumo();
                });
            });
        }
        if (btn.classList.contains('btn-del-conv')) {
            if (!confirm('Excluir convênio DEFINITIVAMENTE? Essa ação não pode ser desfeita.')) return;
            reqJson(base + 'convenio/' + id + '/excluir/', { method: 'DELETE' }).then(function (r) {
                showToast(r.ok ? 'Convênio excluído.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                if (r.ok) loadResumo();
            });
        }
    });

    document.getElementById('tbodyProduto').addEventListener('click', function (e) {
        const btn = e.target.closest('button[data-id]');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        if (btn.classList.contains('btn-ed-prod')) {
            const b = cache.produtos.find(function (x) { return String(x.id) === id; });
            if (b) openProduto(b);
        }
        if (btn.classList.contains('btn-inat-prod')) {
            const b   = cache.produtos.find(function (x) { return String(x.id) === id; });
            const msg = b && b.status ? 'Desativar este produto?' : 'Ativar este produto?';
            confirmarInativacaoComDependencias('produto', 'produto', id, !!(b && b.status), msg).then(function (ok) {
                if (!ok) return;
                reqJson(base + 'produto/' + id + '/', { method: 'DELETE' }).then(function (r) {
                    showToast(r.ok ? 'Produto atualizado.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                    if (r.ok) loadResumo();
                });
            });
        }
        if (btn.classList.contains('btn-del-prod')) {
            if (!confirm('Excluir produto DEFINITIVAMENTE? Essa ação não pode ser desfeita.')) return;
            reqJson(base + 'produto/' + id + '/excluir/', { method: 'DELETE' }).then(function (r) {
                showToast(r.ok ? 'Produto excluído.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                if (r.ok) loadResumo();
            });
        }
    });

    document.getElementById('tbodyTabela').addEventListener('click', function (e) {
        const btn = e.target.closest('button[data-id]');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        if (btn.classList.contains('btn-ed-tab')) {
            const b = cache.tabelas_cms.find(function (x) { return String(x.id) === id; });
            if (b) openTabela(b);
        }
        if (btn.classList.contains('btn-del-tab')) {
            if (!confirm('Excluir esta tabela CMS DEFINITIVAMENTE? Se houver vínculos, será apenas inativada.')) return;
            reqJson(base + 'tabela-cms/' + id + '/', { method: 'DELETE' }).then(function (r) {
                showToast(r.ok ? 'Tabela removida.' : (r.erro || 'Erro'), r.ok ? 'success' : 'danger');
                if (r.ok) loadResumo();
            });
        }
    });

    /* ================================================
       EVENTOS — salvar
    ================================================ */
    document.getElementById('btnSalvarBanco').onclick = function () {
        const eid  = document.getElementById('bancoEditId').value;
        const body = {
            titulo: document.getElementById('bancoTitulo').value.trim(),
            codigo: document.getElementById('bancoCodigo').value.trim(),
            status: document.getElementById('bancoAtivo').checked
        };
        if (!body.titulo) { showToast('Informe o título do banco.', 'warning'); return; }
        const url    = eid ? base + 'banco/' + eid + '/' : base + 'banco/';
        const method = eid ? 'PATCH' : 'POST';
        reqJson(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) {
            if (!r.ok) { showToast(r.erro || 'Erro ao salvar.', 'danger'); return; }
            bootstrap.Modal.getInstance(document.getElementById('modalBanco')).hide();
            showToast(eid ? 'Banco atualizado.' : 'Banco criado com sucesso.', 'success');
            loadResumo();
        });
    };

    document.getElementById('btnSalvarConvenio').onclick = function () {
        const eid  = document.getElementById('convenioEditId').value;
        const body = {
            titulo: document.getElementById('convenioTitulo').value.trim(),
            status: document.getElementById('convenioAtivo').checked
        };
        if (!body.titulo) { showToast('Informe o título do convênio.', 'warning'); return; }
        const url    = eid ? base + 'convenio/' + eid + '/' : base + 'convenio/';
        const method = eid ? 'PATCH' : 'POST';
        reqJson(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) {
            if (!r.ok) { showToast(r.erro || 'Erro ao salvar.', 'danger'); return; }
            bootstrap.Modal.getInstance(document.getElementById('modalConvenio')).hide();
            showToast(eid ? 'Convênio atualizado.' : 'Convênio criado com sucesso.', 'success');
            loadResumo();
        });
    };

    document.getElementById('btnSalvarProduto').onclick = function () {
        const eid  = document.getElementById('produtoEditId').value;
        const body = {
            titulo: document.getElementById('produtoTitulo').value.trim(),
            status: document.getElementById('produtoAtivo').checked,
            flag_port_mais_refin: document.getElementById('produtoFlagPortRefin').checked,
            flag_refin_da_port: document.getElementById('produtoFlagRefinDaPort').checked
        };
        if (!body.titulo) { showToast('Informe o título do produto.', 'warning'); return; }
        if (body.flag_port_mais_refin && body.flag_refin_da_port) {
            showToast('Marque apenas uma flag: Port + Refin ou Refin da Port.', 'warning');
            return;
        }
        const url    = eid ? base + 'produto/' + eid + '/' : base + 'produto/';
        const method = eid ? 'PATCH' : 'POST';
        reqJson(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) {
            if (!r.ok) { showToast(r.erro || 'Erro ao salvar.', 'danger'); return; }
            bootstrap.Modal.getInstance(document.getElementById('modalProduto')).hide();
            if (!eid && r.ja_existia) showToast('Produto já existia e foi reaproveitado.', 'info');
            else showToast(eid ? 'Produto atualizado.' : 'Produto criado com sucesso.', 'success');
            loadResumo();
        });
    };

    document.getElementById('btnSalvarTabela').onclick = function () {
        const eid  = document.getElementById('tabelaEditId').value;
        // Classificador Banco é obrigatório; se não for enviado, backend cai no default M1 — forçamos aqui para ficar explícito
        const selClassif = document.getElementById('tabelaClassificadorBanco');
        const classifVal = (selClassif ? selClassif.value : 'M1').toString().toUpperCase();
        const body = {
            titulo:              document.getElementById('tabelaTitulo').value.trim(),
            banco_id:            parseInt(document.getElementById('tabelaBancoId').value, 10),
            convenio_id:         parseInt(document.getElementById('tabelaConvenioId').value, 10),
            produto_id:          parseInt(document.getElementById('tabelaProdutoId').value, 10),
            taxa_recebido:       document.getElementById('tabelaTxRec').value.trim() || null,
            taxa_repasse:        document.getElementById('tabelaTxRep').value.trim() || null,
            taxa_plastico:       document.getElementById('tabelaTxPla').value.trim() || null,
            classificador_banco: ['M1', 'M2', 'M3'].indexOf(classifVal) >= 0 ? classifVal : 'M1',
            status:              document.getElementById('tabelaAtivo').checked
        };
        if (!body.titulo) { showToast('Informe o título da tabela.', 'warning'); return; }
        if (!body.banco_id || !body.convenio_id || !body.produto_id) {
            showToast('Selecione banco, convênio e produto.', 'warning'); return;
        }
        if (['M1', 'M2', 'M3'].indexOf(body.classificador_banco) < 0) {
            showToast('Selecione um Classificador Banco válido (M1, M2 ou M3).', 'warning'); return;
        }
        const url    = eid ? base + 'tabela-cms/' + eid + '/' : base + 'tabela-cms/';
        const method = eid ? 'PATCH' : 'POST';
        reqJson(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) {
            if (!r.ok) { showToast(r.erro || 'Erro ao salvar.', 'danger'); return; }
            bootstrap.Modal.getInstance(document.getElementById('modalTabela')).hide();
            showToast(eid ? 'Tabela atualizada.' : 'Tabela criada com sucesso.', 'success');
            loadResumo();
        });
    };

    /* ── Busca client-side ── */
    hookSearch('searchBanco', 'tbodyBanco');
    hookSearch('searchConv',  'tbodyConvenio');
    hookSearch('searchProd',  'tbodyProduto');
    document.getElementById('searchCms').addEventListener('input', function () {
        renderTabelas();
    });

    /* Filtros e ordenação CMS no cabeçalho */
    const theadCms = document.getElementById('theadTabelaCms');
    if (theadCms) {
        theadCms.addEventListener('input', function (e) {
            if (e.target.classList.contains('cms-col-filter')) renderTabelas();
        });
        theadCms.addEventListener('change', function (e) {
            if (e.target.classList.contains('cms-col-filter')) renderTabelas();
        });
        theadCms.addEventListener('click', function (e) {
            const label = e.target.closest('.cms-th-label');
            const th = e.target.closest('.cms-th-sortable');
            if (!label || !th) return;
            if (e.target.closest('.cms-col-filter')) return;
            const campo = th.getAttribute('data-sort');
            if (!campo) return;
            if (cmsSortCampo === campo) {
                cmsSortDir = cmsSortDir === 'asc' ? 'desc' : 'asc';
            } else {
                cmsSortCampo = campo;
                cmsSortDir = (campo === 'id' || campo === 'taxa_recebido' || campo === 'status') ? 'desc' : 'asc';
            }
            renderTabelas();
        });
    }

    /* ================================================
       IMPORT EM LOTE CSV
    ================================================ */

    /* dicas de formato por tipo */
    var _importDicas = {
        banco:    'Formato esperado: <code>codigo_banco;nome_banco</code> (separador <strong>ponto-e-vírgula</strong>). Modelo: <code>bancos.csv</code>.',
        convenio: 'Formato esperado: coluna única com os nomes (aceita com ou sem cabeçalho <code>convenio</code>). Modelo: <code>convenios.csv</code>.',
        produto:  'Formato esperado: coluna única com os nomes (aceita com ou sem cabeçalho <code>produto</code>). Modelo: <code>produto.csv</code>.'
    };

    /* cores do header do modal por tipo */
    var _importCores = {
        banco:    'var(--color-banco)',
        convenio: 'var(--color-conv)',
        produto:  'var(--color-prod)'
    };

    /* textos do botão de confirmação por tipo */
    var _importTitulos = {
        banco:    'Importar Bancos',
        convenio: 'Importar Convênios',
        produto:  'Importar Produtos'
    };

    function openImportModal(tipo) {
        document.getElementById('importTipo').value = tipo;
        document.getElementById('importArquivo').value = '';
        document.getElementById('importResult').className = 'import-result d-none';
        document.getElementById('importResult').innerHTML = '';

        /* header dinâmico */
        var header = document.getElementById('importModalHeader');
        header.style.background = _importCores[tipo] || '#667eea';
        header.style.color = '#fff';
        header.querySelector('.btn-close').style.filter = 'invert(1) grayscale(1) brightness(2)';

        document.getElementById('importModalTitle').innerHTML =
            '<i class=\'bx bx-upload me-2\'></i>' + (_importTitulos[tipo] || 'Importar CSV');

        document.getElementById('importDica').innerHTML = _importDicas[tipo] || '';

        /* botão de enviar: cor por tipo */
        var btn = document.getElementById('btnEnviarImport');
        btn.style.background = _importCores[tipo] || '#667eea';
        btn.style.color = '#fff';
        btn.style.borderColor = _importCores[tipo] || '#667eea';

        new bootstrap.Modal(document.getElementById('modalImportCsv')).show();
    }

    /* bind nos botões de cada aba */
    document.querySelectorAll('.btn-import-csv').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openImportModal(btn.getAttribute('data-tipo'));
        });
    });

    /* submit do import */
    document.getElementById('btnEnviarImport').onclick = function () {
        var tipo    = document.getElementById('importTipo').value;
        var fileInp = document.getElementById('importArquivo');
        var result  = document.getElementById('importResult');

        if (!fileInp.files || !fileInp.files.length) {
            showToast('Selecione um arquivo CSV antes de importar.', 'warning');
            return;
        }

        var btn = document.getElementById('btnEnviarImport');
        btn.disabled = true;
        btn.innerHTML = '<i class=\'bx bx-loader-alt bx-spin me-1\'></i>Importando...';

        var fd = new FormData();
        fd.append('tipo', tipo);
        fd.append('arquivo', fileInp.files[0]);
        fd.append('csrfmiddlewaretoken', csrf());

        fetch('/contratos/api/v2/config/importar/', {
            method: 'POST',
            body: fd,
            credentials: 'same-origin'
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            btn.disabled = false;
            btn.innerHTML = '<i class=\'bx bx-cloud-upload me-1\'></i>Importar';

            if (!d.ok) {
                result.className = 'import-result warning';
                result.innerHTML = '<i class=\'bx bx-error-circle me-1\'></i>' + (d.erro || 'Erro ao importar.');
                return;
            }

            var temErros  = d.erros && d.erros.length;
            var cls       = temErros ? 'import-result warning' : 'import-result success';
            var jaExistiam = Number(d.ja_existiam || 0);
            var linhasVazias = Number(d.linhas_vazias || 0);
            var resumo = '<strong>' + d.criados + '</strong> criado(s), <strong>' + jaExistiam + '</strong> já existente(s), <strong>' + linhasVazias + '</strong> linha(s) vazia(s).';

            var html = '<i class=\'bx ' + (temErros ? 'bx-error-circle' : 'bx-check-circle') + ' me-1\'></i>' + resumo;
            if (temErros) {
                html += '<ul class="mt-2 mb-0 ps-3">';
                d.erros.forEach(function (e) { html += '<li>' + esc(e) + '</li>'; });
                html += '</ul>';
            }

            result.className = cls;
            result.innerHTML = html;

            if (d.criados > 0) {
                loadResumo();
                showToast(d.criados + ' registro(s) importado(s) com sucesso.', 'success');
            }
        })
        .catch(function () {
            btn.disabled = false;
            btn.innerHTML = '<i class=\'bx bx-cloud-upload me-1\'></i>Importar';
            showToast('Erro de conexão ao importar.', 'danger');
        });
    };

    /* ================================================
       AUDITORIA (superuser)
    ================================================ */
    let auditPage = 1;
    let auditTotalPages = 1;
    let cacheLogs = [];

    function badgeAcaoLog(acao, label) {
        const map = {
            criar: 'audit-badge audit-badge-criar',
            editar: 'audit-badge audit-badge-editar',
            inativar: 'audit-badge audit-badge-inativar',
            reativar: 'audit-badge audit-badge-reativar',
            excluir: 'audit-badge audit-badge-excluir',
            importar_csv: 'audit-badge audit-badge-import'
        };
        const cls = map[acao] || 'audit-badge';
        return '<span class="' + cls + '">' + esc(label || acao) + '</span>';
    }

    function fmtDataLog(iso) {
        if (!iso) return '—';
        try {
            const d = new Date(iso);
            return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
        } catch (e) {
            return iso;
        }
    }

    function renderLogs() {
        const tb = document.getElementById('tbodyLogs');
        if (!tb) return;
        tb.innerHTML = '';
        if (!cacheLogs.length) {
            tb.innerHTML = '<tr><td colspan="7" class="empty-state"><i class=\'bx bx-history\'></i>Nenhum registro encontrado</td></tr>';
            return;
        }
        cacheLogs.forEach(function (x, idx) {
            const tr = document.createElement('tr');
            tr.innerHTML =
                '<td class="small text-muted">' + esc(fmtDataLog(x.data)) + '</td>' +
                '<td class="small">' + esc(x.usuario_nome || '—') + '</td>' +
                '<td>' + badgeAcaoLog(x.acao, x.acao_display) + '</td>' +
                '<td class="small">' + esc(x.entidade_display || x.entidade) + '</td>' +
                '<td class="text-muted small">' + (x.registro_id != null ? '#' + x.registro_id : '—') + '</td>' +
                '<td class="small">' + esc(x.resumo || x.registro_titulo || '') + '</td>' +
                '<td class="text-end">' +
                  '<button type="button" class="btn btn-acao btn-outline-secondary btn-log-detalhe" data-idx="' + idx + '" title="Ver detalhes"><i class=\'bx bx-detail\'></i></button>' +
                '</td>';
            tb.appendChild(tr);
        });
    }

    function atualizarPaginacaoLogs(d) {
        auditTotalPages = d.total_pages || 1;
        const info = document.getElementById('auditLogInfo');
        if (info) {
            info.textContent = 'Página ' + (d.page || 1) + ' de ' + auditTotalPages + ' — ' + (d.total || 0) + ' registro(s)';
        }
        const prev = document.getElementById('btnLogsPrev');
        const next = document.getElementById('btnLogsNext');
        if (prev) prev.disabled = (d.page || 1) <= 1;
        if (next) next.disabled = (d.page || 1) >= auditTotalPages;
    }

    function loadLogs(page) {
        if (!isSuperuser) return Promise.resolve();
        auditPage = page || 1;
        const params = new URLSearchParams();
        params.set('page', String(auditPage));
        params.set('page_size', '50');
        const ent = document.getElementById('filtLogEntidade');
        const ac = document.getElementById('filtLogAcao');
        const di = document.getElementById('filtLogDataInicio');
        const df = document.getElementById('filtLogDataFim');
        if (ent && ent.value) params.set('entidade', ent.value);
        if (ac && ac.value) params.set('acao', ac.value);
        if (di && di.value) params.set('data_inicio', di.value);
        if (df && df.value) params.set('data_fim', df.value);

        const tb = document.getElementById('tbodyLogs');
        if (tb) tb.innerHTML = '<tr class="loading-row"><td colspan="7"><i class=\'bx bx-loader-alt bx-spin d-block mb-2\'></i>Carregando...</td></tr>';

        return reqJson(base + 'logs/?' + params.toString(), { method: 'GET' }).then(function (d) {
            if (!d.ok) {
                showToast(d.erro || 'Erro ao carregar logs.', 'danger');
                cacheLogs = [];
                if (tb) tb.innerHTML = '<tr><td colspan="7" class="empty-state text-danger">' + esc(d.erro || 'Erro') + '</td></tr>';
                return;
            }
            cacheLogs = d.logs || [];
            renderLogs();
            atualizarPaginacaoLogs(d);
        });
    }

    function openLogDetalhe(idx) {
        const x = cacheLogs[idx];
        if (!x) return;
        document.getElementById('logDetalheResumo').textContent = x.resumo || '';
        document.getElementById('logDetalheAntes').textContent =
            x.dados_antes ? JSON.stringify(x.dados_antes, null, 2) : '—';
        document.getElementById('logDetalheDepois').textContent =
            x.dados_depois ? JSON.stringify(x.dados_depois, null, 2) : '—';
        new bootstrap.Modal(document.getElementById('modalLogDetalhe')).show();
    }

    if (isSuperuser) {
        const tabAudit = document.getElementById('tabBtnAuditoria');
        if (tabAudit) {
            tabAudit.addEventListener('shown.bs.tab', function () {
                loadLogs(1);
            });
        }
        const btnFiltrar = document.getElementById('btnFiltrarLogs');
        if (btnFiltrar) btnFiltrar.onclick = function () { loadLogs(1); };
        const btnLimpar = document.getElementById('btnLimparFiltrosLogs');
        if (btnLimpar) {
            btnLimpar.onclick = function () {
                ['filtLogEntidade', 'filtLogAcao', 'filtLogDataInicio', 'filtLogDataFim'].forEach(function (id) {
                    const el = document.getElementById(id);
                    if (el) el.value = '';
                });
                loadLogs(1);
            };
        }
        const btnPrev = document.getElementById('btnLogsPrev');
        if (btnPrev) btnPrev.onclick = function () {
            if (auditPage > 1) loadLogs(auditPage - 1);
        };
        const btnNext = document.getElementById('btnLogsNext');
        if (btnNext) btnNext.onclick = function () {
            if (auditPage < auditTotalPages) loadLogs(auditPage + 1);
        };
        const tbodyLogs = document.getElementById('tbodyLogs');
        if (tbodyLogs) {
            tbodyLogs.addEventListener('click', function (e) {
                const btn = e.target.closest('.btn-log-detalhe');
                if (!btn) return;
                const idx = parseInt(btn.getAttribute('data-idx'), 10);
                if (!isNaN(idx)) openLogDetalhe(idx);
            });
        }
    }

    /* ── Init ── */
    loadResumo();
})();
