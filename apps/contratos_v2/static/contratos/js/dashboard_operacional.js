(function () {
    'use strict';

    const base = window.DASH_API_BASE || '/contratos/api/v2/dashboard/';
    const tabCarregada = {};
    let catalogos = null;

    function qs(sel) { return document.querySelector(sel); }

    function getFiltrosQuery() {
        const p = new URLSearchParams();
        const periodo = qs('#filtroPeriodo')?.value;
        const banco = qs('#filtroBanco')?.value;
        const convenio = qs('#filtroConvenio')?.value;
        const produto = qs('#filtroProduto')?.value;
        const solicitante = qs('#filtroSolicitante')?.value;
        if (periodo) p.set('periodo', periodo);
        if (banco) p.set('banco_id', banco);
        if (convenio) p.set('convenio_id', convenio);
        if (produto) p.set('produto_id', produto);
        if (solicitante) p.set('solicitante_id', solicitante);
        const s = p.toString();
        return s ? '?' + s : '';
    }

    function getJson(url) {
        return fetch(url, { credentials: 'same-origin' }).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    function showAlert(msg, tipo) {
        const el = qs('#dashAlert');
        if (!el) return;
        el.textContent = msg;
        el.className = 'alert alert-' + (tipo || 'danger');
        el.classList.remove('d-none');
    }

    function hideAlert() {
        const el = qs('#dashAlert');
        if (el) el.classList.add('d-none');
    }

    function renderBarras(containerId, itens, labelKey, valueKey, warn) {
        const el = qs(containerId);
        if (!el) return;
        if (!itens || !itens.length) {
            el.innerHTML = '<div class="dash-empty-chart">Nenhum dado no período selecionado.</div>';
            return;
        }
        const max = Math.max.apply(null, itens.map(function (i) { return i[valueKey] || 0; })) || 1;
        let html = '';
        itens.forEach(function (item) {
            const label = item[labelKey] || '—';
            const val = item[valueKey] || 0;
            const pct = Math.round((val / max) * 100);
            html += '<div class="dash-bar-row">' +
                '<span class="dash-bar-label">' + escapeHtml(label) + '</span>' +
                '<div class="dash-bar-track"><div class="dash-bar-fill' + (warn ? ' dash-bar-fill--warn' : '') +
                '" style="width:' + pct + '%"></div></div>' +
                '<span class="dash-bar-val">' + val + '</span></div>';
        });
        el.innerHTML = html;
    }

    function escapeHtml(t) {
        if (!t) return '';
        return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function preencherSelect(id, opcoes, labelCampo) {
        const sel = qs(id);
        if (!sel) return;
        const atual = sel.value;
        sel.innerHTML = '<option value="">Todos</option>';
        (opcoes || []).forEach(function (o) {
            const opt = document.createElement('option');
            opt.value = o.id;
            opt.textContent = o[labelCampo] || o.nome || o.titulo || o.id;
            sel.appendChild(opt);
        });
        if (atual) sel.value = atual;
    }

    function loadCatalogos() {
        if (catalogos) return Promise.resolve(catalogos);
        return getJson(window.DASH_CATALOGOS || '/contratos/api/v2/catalogos/').then(function (d) {
            catalogos = d;
            preencherSelect('#filtroBanco', d.bancos, 'titulo');
            preencherSelect('#filtroConvenio', d.convenios, 'titulo');
            preencherSelect('#filtroProduto', d.produtos, 'titulo');
            return d;
        });
    }

    function loadVisaoGeral() {
        return getJson(base + 'visao-geral/' + getFiltrosQuery()).then(function (d) {
            if (!d.ok) throw new Error(d.erro || 'Erro ao carregar visão geral');
            const k = d.kpis || {};
            qs('#kpiEmAndamento').textContent = (k.em_andamento && k.em_andamento.total) || 0;
            qs('#kpiPendencias').textContent = (k.pendencias && k.pendencias.total) || 0;
            qs('#kpiFormalizacao').textContent = (k.formalizacao && k.formalizacao.total) || 0;
            qs('#kpiPagamentos').textContent = (k.pagamentos && k.pagamentos.total) || 0;
            qs('#kpiEventosHist').textContent = d.eventos_historico_periodo || 0;
            if (d.solicitantes) preencherSelect('#filtroSolicitante', d.solicitantes, 'nome');
        });
    }

    function loadEsteira() {
        return getJson(base + 'esteira/' + getFiltrosQuery()).then(function (d) {
            if (!d.ok) throw new Error(d.erro || 'Erro ao carregar esteira');
            const el = qs('#dashEsteiraConteudo');
            if (!el) return;
            const itens = d.por_etapa || [];
            if (!itens.length) {
                el.innerHTML = '<p class="text-muted mb-0">Nenhum item na esteira para os filtros selecionados.</p>';
                return;
            }
            let html = '<p class="small text-muted">Total: ' + (d.total || 0) + '</p>';
            itens.forEach(function (row) {
                html += '<div class="dash-bar-row"><span class="dash-bar-label">' + escapeHtml(row.etapa) +
                    '</span><div class="dash-bar-track"><div class="dash-bar-fill" style="width:' +
                    Math.min(100, Math.round((row.total / (d.total || 1)) * 100)) + '%"></div></div>' +
                    '<span class="dash-bar-val">' + row.total + '</span></div>';
            });
            el.innerHTML = html;
        });
    }

    function loadProducao() {
        return getJson(base + 'producao/' + getFiltrosQuery()).then(function (d) {
            if (!d.ok) throw new Error(d.erro || 'Erro ao carregar produção');
            qs('#prodSimulacoes').textContent = d.simulacoes || 0;
            qs('#prodPropostas').textContent = d.propostas || 0;
            qs('#prodContratos').textContent = d.contratos || 0;
            const fonteEl = qs('#prodFonte');
            if (fonteEl) {
                fonteEl.textContent = d.fonte_dados === 'historico'
                    ? 'Fonte: histórico técnico'
                    : 'Fonte: dados atuais (sem histórico no período)';
            }
        });
    }

    function loadPendencias() {
        hideAlert();
        return getJson(base + 'pendencias/' + getFiltrosQuery()).then(function (d) {
            const vazioEl = qs('#dashPendenciasVazio');
            if (!d.ok) {
                showAlert(d.erro || 'Erro ao carregar aba Pendências.', 'danger');
                renderBarras('#chartPendenciasTipo', [], 'tipo', 'total');
                renderBarras('#chartPendenciasAging', [], 'faixa', 'total', true);
                return;
            }
            if (d.sem_pendencias) {
                if (vazioEl) {
                    vazioEl.textContent = d.mensagem || 'Nenhuma pendência aberta no momento.';
                    vazioEl.classList.remove('d-none');
                }
            } else if (vazioEl) {
                vazioEl.classList.add('d-none');
            }
            renderBarras('#chartPendenciasTipo', d.por_tipo || [], 'tipo', 'total');
            renderBarras('#chartPendenciasAging', d.aging || [], 'faixa', 'total', true);
        }).catch(function () {
            showAlert('Erro ao carregar aba Pendências.', 'danger');
            renderBarras('#chartPendenciasTipo', [], 'tipo', 'total');
            renderBarras('#chartPendenciasAging', [], 'faixa', 'total', true);
        });
    }

    function carregarTab(tab) {
        hideAlert();
        const loaders = {
            visao_geral: loadVisaoGeral,
            esteira: loadEsteira,
            producao: loadProducao,
            pendencias: loadPendencias,
        };
        const fn = loaders[tab];
        if (!fn) return Promise.resolve();
        return fn().catch(function (err) {
            showAlert('Erro ao carregar aba ' + tab + ': ' + (err.message || err), 'danger');
        });
    }

    function recarregarTudo() {
        tabCarregada.visao_geral = false;
        tabCarregada.esteira = false;
        tabCarregada.producao = false;
        tabCarregada.pendencias = false;
        const ativa = document.querySelector('#dashTabs .nav-link.active');
        const tab = ativa ? ativa.getAttribute('data-tab') : 'visao_geral';
        tabCarregada[tab] = true;
        return carregarTab(tab);
    }

    document.addEventListener('DOMContentLoaded', function () {
        loadCatalogos().then(function () {
            return loadVisaoGeral();
        }).then(function () {
            tabCarregada.visao_geral = true;
        }).catch(function () {
            showAlert('Erro ao inicializar dashboard.', 'danger');
        });

        document.querySelectorAll('#dashTabs [data-tab]').forEach(function (btn) {
            btn.addEventListener('shown.bs.tab', function (ev) {
                const tab = ev.target.getAttribute('data-tab');
                if (tabCarregada[tab]) return;
                tabCarregada[tab] = true;
                carregarTab(tab);
            });
        });

        qs('#btnAplicarFiltros')?.addEventListener('click', recarregarTudo);
        qs('#btnLimparFiltros')?.addEventListener('click', function () {
            ['#filtroBanco', '#filtroConvenio', '#filtroProduto', '#filtroSolicitante'].forEach(function (id) {
                const el = qs(id);
                if (el) el.value = '';
            });
            qs('#filtroPeriodo').value = 'mes_atual';
            recarregarTudo();
        });
    });
})();
