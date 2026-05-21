(function() {
    var base = (window.FINANCEIRO_GERAL_BASE || '').replace(/\/?$/, '') + '/';
    var urlNotif = base + 'api/notificacoes/contas/';
    var urlCount = base + 'api/notificacoes/count/';
    var urlSse = base + 'sse/notificacoes/contas/';
    var urlBonif = base + 'api/notificacoes/bonificacoes-usuario/';
    var urlContasAPagar = base + 'contas-a-pagar/';
    function formatarMoeda(v) {
        return 'R$ ' + (typeof v === 'number' ? v.toFixed(2) : parseFloat(v || 0).toFixed(2)).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
    function atualizarBadge(count) {
        var n = typeof count === 'number' ? count : (parseInt(count, 10) || 0);
        var $badges = $('.badge-notif-contas');
        if (!$badges.length) return;
        var txt = n > 0 ? (n > 99 ? '99' : n) : '';
        $badges.text(txt);
        if (n > 0) $badges.show(); else $badges.hide();
    }
    function renderizar(hoje, atrasadas) {
        var html = '';
        function linhaItem(c, isAtrasada) {
            var statusCls = (c.status || '') === 'Pago' ? 'text-success' : 'text-warning';
            var vencl = isAtrasada ? ' text-danger' : '';
            var go = urlContasAPagar + '?tipo=' + encodeURIComponent(c.tipo || '') + '&id=' + (c.id || '');
            return '<li class="list-group-item list-group-item-action notif-contas-linha" data-id="' + (c.id || '') + '" data-tipo="' + (c.tipo || '') + '" role="button">' +
                '<div class="d-flex justify-content-between align-items-start"><strong>' + (c.descricao || '-') + '</strong><span class="badge bg-secondary">' + (c.tipo_display || '') + '</span></div>' +
                '<div class="small mt-1">Valor: ' + formatarMoeda(c.valor) + ' | Vencimento: <span class="' + vencl + '">' + (c.data_vencimento || '') + '</span> | Status: <span class="' + statusCls + '">' + (c.status || 'Pendente') + '</span></div>' +
                '</li>';
        }
        if (hoje.length) {
            html += '<h6 class="mb-2">Vencendo hoje</h6><ul class="list-group mb-3">';
            hoje.forEach(function(c) { html += linhaItem(c, false); });
            html += '</ul>';
        }
        if (atrasadas.length) {
            html += '<h6 class="mb-2">Atrasadas</h6><ul class="list-group">';
            atrasadas.forEach(function(c) { html += linhaItem(c, true); });
            html += '</ul>';
        }
        if (!hoje.length && !atrasadas.length) {
            html = '<p class="text-muted mb-0">Nenhuma conta a pagar no dia ou atrasada.</p>';
        }
        return html;
    }
    function renderizarBonificacoes(mesReferente, itens) {
        if (!itens || !itens.length) return '';
        var html = '<h6 class="mb-2 mt-3">Bonificações (' + (mesReferente || '') + ')</h6><ul class="list-group mb-3">';
        itens.forEach(function(b) {
            var statusTexto = b.status_pagamento ? 'Paga' : 'A pagar';
            var statusCls = b.status_pagamento ? 'text-success' : 'text-warning';
            html += '<li class="list-group-item list-group-item-action notif-bonif-linha" data-id="' + (b.id || '') + '" role="button">' +
                '<div class="d-flex justify-content-between align-items-start"><strong>Bonificação</strong><span class="badge bg-secondary">' + (mesReferente || '') + '</span></div>' +
                '<div class="small mt-1">Valor: ' + formatarMoeda(b.valor_bonificacao) + ' | Status: <span class="' + statusCls + '">' + statusTexto + '</span></div></li>';
        });
        html += '</ul>';
        return html;
    }
    function atualizarBonificacaoHeader(mesReferente, itens) {
        var $el = $('#bonif-header-info');
        if (!$el.length) return;
        if (!itens || !itens.length) {
            $el.hide().text('');
            return;
        }
        var total = 0;
        var temPendente = false;
        itens.forEach(function(b) {
            var v = parseFloat(b.valor_bonificacao || 0);
            if (!isNaN(v)) total += v;
            if (!b.status_pagamento) temPendente = true;
        });
        if (!total) {
            $el.hide().text('');
            return;
        }
        var statusTexto = temPendente ? 'A pagar' : 'Paga';
        var texto = 'Bonificação ' + (mesReferente || '') + ' • ' + formatarMoeda(total) + ' • ' + statusTexto;
        $el.text(texto).show();
    }
    function irParaContasPagar(tipo, id) {
        var q = '?tipo=' + encodeURIComponent(tipo || 'CONTA') + (id ? '&id=' + encodeURIComponent(id) : '');
        window.location = urlContasAPagar + q;
    }
    function carregarNotificacoes() {
        var $body = $('#notificacoes-contas-body');
        if (!$body.length) return;
        $body.html('<p class="text-muted">Carregando...</p>');
        $.get(urlNotif).done(function(rContas) {
            var htmlContas = '';
            if (rContas.success && rContas.result) {
                htmlContas = renderizar(rContas.result.hoje || [], rContas.result.atrasadas || []);
                var total = (rContas.result.hoje || []).length + (rContas.result.atrasadas || []).length;
                atualizarBadge(total);
            } else {
                htmlContas = '<p class="text-muted mb-0">Nenhuma conta a pagar no dia ou atrasada.</p>';
            }
            $.get(urlBonif).done(function(rBonif) {
                var htmlBonif = '';
                var temBonif = rBonif.success && rBonif.result && rBonif.result.itens && rBonif.result.itens.length > 0;
                if (temBonif) {
                    htmlBonif = renderizarBonificacoes(rBonif.result.mes_referente || '', rBonif.result.itens);
                    atualizarBonificacaoHeader(rBonif.result.mes_referente || '', rBonif.result.itens);
                } else {
                    atualizarBonificacaoHeader('', []);
                }
                $body.html(htmlContas + htmlBonif);
                $body.off('click', '.notif-contas-linha').on('click', '.notif-contas-linha', function() {
                    var tipo = $(this).data('tipo');
                    var id = $(this).data('id');
                    irParaContasPagar(tipo, id);
                });
                $body.off('click', '.notif-bonif-linha').on('click', '.notif-bonif-linha', function() {
                    irParaContasPagar('BONIFICACAO', $(this).data('id'));
                });
            }).fail(function() {
                $body.html(htmlContas);
                $body.off('click', '.notif-contas-linha').on('click', '.notif-contas-linha', function() {
                    var tipo = $(this).data('tipo');
                    var id = $(this).data('id');
                    irParaContasPagar(tipo, id);
                });
            });
        }).fail(function() {
            $body.html('<p class="text-danger">Erro ao carregar.</p>');
        });
    }
    $(document).ready(function() {
        $.get(urlCount).done(function(r) {
            if (r.success && r.result && typeof r.result.count !== 'undefined') {
                atualizarBadge(r.result.count);
            }
        });
        $.get(urlBonif).done(function(r) {
            var itens = (r && r.success && r.result && r.result.itens) ? r.result.itens : [];
            var mesRef = (r && r.success && r.result && r.result.mes_referente) ? r.result.mes_referente : '';
            atualizarBonificacaoHeader(mesRef, itens);
        }).fail(function() {
            atualizarBonificacaoHeader('', []);
        });
        try {
            var evtSource = new EventSource(urlSse);
            evtSource.onmessage = function(e) {
                try {
                    var data = JSON.parse(e.data);
                    if (typeof data.count !== 'undefined') atualizarBadge(data.count);
                } catch (err) {}
            };
            evtSource.onerror = function() {
                evtSource.close();
            };
        } catch (err) {}
        var el = document.getElementById('modalNotificacoesContas');
        if (el) {
            el.addEventListener('show.bs.modal', function() {
                carregarNotificacoes();
            });
        }
    });
})();
