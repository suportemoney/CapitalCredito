/**
 * Container operacional CX48 na consulta SIAPE.
 */
(function () {
    'use strict';

    var carteiraIdAtual = null;
    var modoAtual = 'todas';
    var ctxModal = {};

    function el(id) {
        return document.getElementById(id);
    }

    function getCookie(name) {
        var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    function escHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatCpf(cpf) {
        var d = String(cpf || '').replace(/\D/g, '');
        if (d.length !== 11) return cpf || '—';
        return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }

    function reparentContainer() {
        var box = el('siape-container-novo-contrato');
        if (!box) return;
        var fichaVisivel = el('detalhes-cliente-container') &&
            el('detalhes-cliente-container').style.display !== 'none';
        var mountSidebar = el('mount-container-nc-sidebar');
        var mountFilter = el('mount-container-nc-filter');
        var dest = fichaVisivel && mountSidebar ? mountSidebar : mountFilter;
        if (dest && box.parentNode !== dest) {
            dest.appendChild(box);
        }
    }

    function renderItens(itens, modo) {
        var lista = el('nc-itens-lista');
        var vazio = el('nc-itens-vazio');
        if (!lista) return;
        if (!itens || !itens.length) {
            lista.innerHTML = '';
            if (vazio) {
                vazio.classList.remove('d-none');
                vazio.textContent = modo === 'carteira'
                    ? 'Nenhuma proposta operacional sua nesta carteira.'
                    : 'Nenhuma proposta operacional em andamento.';
            }
            return;
        }
        if (vazio) vazio.classList.add('d-none');
        var html = '';
        itens.forEach(function (it) {
            var cpfLimpo = String(it.cliente_cpf || '').replace(/\D/g, '');
            var cpfAttr = cpfLimpo.length === 11
                ? ' data-cliente-cpf="' + escHtml(cpfLimpo) + '"'
                : '';
            var clsClick = cpfLimpo.length === 11 ? ' siape-container-nc__item--clicavel' : '';
            html += '<div class="siape-container-nc__item' + clsClick + '" data-proposta-id="' +
                escHtml(it.proposta_id) + '"' + cpfAttr +
                ' title="' + (cpfLimpo.length === 11 ? 'Clique para abrir a ficha do cliente' : '') + '">';
            if (modo === 'todas' && (it.cliente_nome || it.cliente_cpf)) {
                html += '<div class="siape-container-nc__item-cliente small fw-semibold">' +
                    escHtml(it.cliente_nome || '—') +
                    (it.cliente_cpf ? ' <span class="text-muted fw-normal">· ' + formatCpf(it.cliente_cpf) + '</span>' : '') +
                    '</div>';
            }
            html += '<div class="fw-semibold small">' + escHtml(it.proposta_codigo || 'Proposta') +
                (it.contrato_codigo ? ' · ' + escHtml(it.contrato_codigo) : '') + '</div>';
            html += '<div class="siape-container-nc__item-meta">' +
                escHtml(it.banco) + (it.produto ? ' · ' + escHtml(it.produto) : '') + '</div>';
            if (modo === 'todas' && it.carteira_status) {
                html += '<div class="siape-container-nc__item-meta">' + escHtml(it.carteira_status) + '</div>';
            }
            html += '<div class="siape-container-nc__item-meta">' + escHtml(it.status_linha) + '</div>';
            html += '<div class="siape-container-nc__item-btns">';
            if (it.link_formalizacao) {
                html += '<button type="button" class="btn btn-outline-secondary btn-sm btn-nc-copiar-link" data-link="' +
                    escHtml(it.link_formalizacao) + '"><i class="bx bx-copy"></i> Link</button>';
            }
            if (it.exibir_botao_fazer_checagem) {
                html += '<button type="button" class="btn btn-outline-primary btn-sm btn-nc-checagem" ' +
                    'data-contrato-id="' + escHtml(it.contrato_id) + '" data-acao="' +
                    escHtml(it.acao_evoluir_checagem) + '"><i class="bx bx-check"></i> Checagem</button>';
            }
            if (it.exibir_botao_formalizar_checado) {
                var nomeFormal = it.cliente_nome || (el('nc-cliente-nome') ? el('nc-cliente-nome').textContent : '');
                html += '<button type="button" class="btn btn-success btn-sm btn-nc-formalizar" ' +
                    'data-contrato-id="' + escHtml(it.contrato_id) + '" data-acao="' +
                    escHtml(it.acao_evoluir_formalizado) + '" data-link="' +
                    escHtml(it.link_formalizacao) + '" data-nome="' +
                    escHtml(nomeFormal) + '">' +
                    '<i class="bx bx-badge-check"></i> Formalizar</button>';
            }
            if (it.exibir_botao_enviar_video) {
                html += '<button type="button" class="btn btn-primary btn-sm btn-nc-video" ' +
                    'data-contrato-id="' + escHtml(it.contrato_id) + '"><i class="bx bx-video"></i> Vídeo</button>';
            }
            if (it.exibir_btn_arquivos) {
                html += '<button type="button" class="btn btn-outline-primary btn-sm btn-nc-arquivos" ' +
                    'data-contrato-id="' + escHtml(it.contrato_id || '') + '" data-solicitacao-id="' +
                    escHtml(it.solicitacao_digitacao_id || '') + '"><i class="bx bx-paperclip"></i> Arquivos</button>';
            }
            if (it.exibir_btn_sanar_pendencia) {
                html += '<button type="button" class="btn btn-warning btn-sm btn-nc-pendencia" ' +
                    'data-contrato-id="' + escHtml(it.contrato_id || '') + '" data-solicitacao-id="' +
                    escHtml(it.solicitacao_digitacao_id || '') + '"><i class="bx bx-error"></i> Sanear</button>';
            }
            html += '</div></div>';
        });
        lista.innerHTML = html;
    }

    function renderContainer(data) {
        var box = el('siape-container-novo-contrato');
        if (!box || !data || !data.ok) {
            if (box) box.style.display = 'none';
            return;
        }
        modoAtual = data.modo || (data.carteira_id ? 'carteira' : 'todas');
        if (modoAtual === 'todas') {
            if (el('nc-cliente-nome')) el('nc-cliente-nome').textContent = 'Minhas propostas';
            if (el('nc-cliente-cpf')) {
                var qtd = (data.itens || []).length;
                el('nc-cliente-cpf').textContent = qtd + (qtd === 1 ? ' proposta' : ' propostas');
            }
            if (el('nc-carteira-status')) {
                el('nc-carteira-status').textContent = 'Clique em uma proposta para abrir a ficha do cliente';
            }
        } else {
            if (el('nc-cliente-nome')) el('nc-cliente-nome').textContent = data.cliente_nome || '—';
            if (el('nc-cliente-cpf')) el('nc-cliente-cpf').textContent = formatCpf(data.cliente_cpf);
            var statusParts = [];
            if (data.tabulacao_operacional) statusParts.push(data.tabulacao_operacional);
            if (data.tag_status_operacional) statusParts.push(data.tag_status_operacional);
            if (data.status_comercial) statusParts.push(data.status_comercial);
            if (el('nc-carteira-status')) {
                el('nc-carteira-status').textContent = statusParts.length ? statusParts.join(' · ') : '—';
            }
        }
        renderItens(data.itens || [], modoAtual);
        reparentContainer();
        box.style.display = 'block';
    }

    function carregarContainer(carteiraId) {
        if (!window.podeNovoContrato) {
            var box = el('siape-container-novo-contrato');
            if (box) box.style.display = 'none';
            return Promise.resolve();
        }
        carteiraIdAtual = carteiraId || null;
        var url = '/api/consulta/container-novo-contrato/';
        if (carteiraId) {
            url += '?carteira_id=' + encodeURIComponent(carteiraId);
        }
        return fetch(url, {
            credentials: 'same-origin',
        })
            .then(function (r) { return r.json(); })
            .then(function (data) { renderContainer(data); })
            .catch(function () {
                var box = el('siape-container-novo-contrato');
                if (box) box.style.display = 'none';
                if (typeof console !== 'undefined') {
                    console.warn('Container operacional: falha ao carregar /api/consulta/container-novo-contrato/');
                }
            });
    }

    function postEvoluir(contratoId, acao, observacao) {
        return fetch('/contratos/api/v2/evoluir/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                tipo: 'contrato',
                id: contratoId,
                acao: acao,
                observacao: observacao || '',
            }),
        }).then(function (r) { return r.json(); });
    }

    function uploadVideo(contratoId, file) {
        var fd = new FormData();
        fd.append('video', file);
        return fetch('/contratos/api/v2/contrato/' + contratoId + '/upload-video/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: fd,
        }).then(function (r) { return r.json(); });
    }

    function carregarArquivosLista() {
        var lista = el('nc-arquivos-lista');
        if (!lista) return;
        lista.textContent = 'Carregando...';
        var url;
        if (ctxModal.contratoId) {
            url = '/contratos/api/v2/contrato/' + ctxModal.contratoId + '/midia-arquivos/';
        } else if (ctxModal.solicitacaoId) {
            url = '/contratos/api/v2/solicitacao-dig/' + ctxModal.solicitacaoId + '/midia-arquivos/';
        } else {
            lista.textContent = 'Referência inválida.';
            return;
        }
        fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.ok) {
                    lista.textContent = data.erro || 'Erro ao carregar.';
                    return;
                }
                var arqs = data.arquivos || data.itens || [];
                if (!arqs.length) {
                    lista.innerHTML = '<p class="text-muted mb-0">Nenhum arquivo.</p>';
                    return;
                }
                var h = '<ul class="list-unstyled mb-0">';
                arqs.forEach(function (a) {
                    h += '<li class="mb-1"><i class="bx bx-file me-1"></i>' + escHtml(a.titulo || a.nome || 'Arquivo') + '</li>';
                });
                h += '</ul>';
                lista.innerHTML = h;
            })
            .catch(function () { lista.textContent = 'Erro ao carregar arquivos.'; });
    }

    /** Tipo/id usados na ficha e no POST editar-dados do modal de pendência. */
    function getPendenciaRef() {
        if (ctxModal.contratoId) {
            return { tipo: 'contrato', id: ctxModal.contratoId };
        }
        if (ctxModal.solicitacaoId) {
            return { tipo: 'solicitacao_dig', id: ctxModal.solicitacaoId };
        }
        return null;
    }

    function limparAlertaPendencia(id) {
        var a = el(id);
        if (a) {
            a.classList.add('d-none');
            a.textContent = '';
        }
    }

    function mostrarAlertaPendencia(id, msg) {
        var a = el(id);
        if (!a) return;
        a.textContent = msg || 'Erro ao processar.';
        a.classList.remove('d-none');
    }

    function setNcEditField(path, valor) {
        var inp = document.querySelector('[data-nc-edit-field="' + path + '"]');
        if (!inp) return;
        if (valor === null || valor === undefined) {
            inp.value = '';
            return;
        }
        inp.value = String(valor);
    }

    function limparCamposPendencia() {
        document.querySelectorAll('#modalNcSanarPendencia [data-nc-edit-field]').forEach(function (inp) {
            inp.value = '';
        });
    }

    function preencherPendenciaFicha(d) {
        var dp = d.dados_pessoais || {};
        var prop = (Array.isArray(d.propostas) && d.propostas.length) ? d.propostas[0] : {};
        var contrato = d.contrato || {};
        var sol = d.solicitacao || {};
        setNcEditField('cliente.nome_completo', dp.nome_completo);
        setNcEditField('cliente.email', dp.email);
        setNcEditField('cliente.telefone', dp.telefone);
        setNcEditField('cliente.numero_rg', dp.numero_rg);
        setNcEditField('cliente.data_nascimento', dp.data_nascimento || '');
        setNcEditField('cliente.nome_mae', dp.nome_mae);
        setNcEditField('cliente.nome_pai', dp.nome_pai);
        setNcEditField('cliente.naturalidade', dp.naturalidade);
        setNcEditField('proposta.valor_parcela', prop.valor_parcela);
        setNcEditField('proposta.valor_af', prop.valor_af);
        setNcEditField('proposta.valor_liberado', prop.valor_liberado);
        setNcEditField('proposta.coeficiente', prop.coeficiente);
        setNcEditField('proposta.prazo', prop.prazo);
        setNcEditField('proposta.valor_tc', prop.valor_tc);
        if (contrato && contrato.id) {
            setNcEditField('contrato.numero_contrato', contrato.codigo || contrato.numero_contrato || '');
            setNcEditField('contrato.link_formalizacao', contrato.link_formalizacao || '');
        } else {
            setNcEditField('contrato.numero_contrato', sol.numero_contrato_banco_pre || '');
            setNcEditField('contrato.link_formalizacao', sol.link_formalizacao_pre || '');
        }
        var obsBox = el('nc-pendencia-obs-operador');
        if (obsBox) {
            var obs = '';
            if (contrato && contrato.id) {
                obs = (contrato.observacao_entrada_pendencias || '').trim();
            } else {
                obs = (sol.observacao_pendencia_operacional || sol.observacoes || '').trim();
            }
            if (obs) {
                obsBox.innerHTML = '<strong>Observação do operacional:</strong> ' + escHtml(obs);
                obsBox.classList.remove('d-none');
            } else {
                obsBox.classList.add('d-none');
                obsBox.innerHTML = '';
            }
        }
    }

    function aplicarVisibilidadePendencia(tiposAbertos) {
        var blocoCliente = el('nc-pend-bloco-cliente');
        var blocoProposta = el('nc-pend-bloco-proposta');
        var blocoContrato = el('nc-pend-bloco-contrato');
        var tabArqBtn = el('nc-pend-tab-arq-btn');
        var ref = getPendenciaRef();
        var ehSolicitacao = ref && ref.tipo === 'solicitacao_dig';
        var tipos = tiposAbertos || [];
        var mostrarCliente = ehSolicitacao || !tipos.length || tipos.indexOf('DADOS_CLIENTE') >= 0;
        var mostrarProposta = ehSolicitacao || !tipos.length || tipos.indexOf('DADOS_PROPOSTA') >= 0;
        var mostrarArquivo = ehSolicitacao || !tipos.length || tipos.indexOf('FALTA_ARQUIVO') >= 0;
        if (blocoCliente) blocoCliente.classList.toggle('d-none', !mostrarCliente);
        if (blocoProposta) blocoProposta.classList.toggle('d-none', !mostrarProposta);
        if (blocoContrato) blocoContrato.classList.toggle('d-none', ehSolicitacao);
        if (tabArqBtn) {
            tabArqBtn.classList.toggle('d-none', !mostrarArquivo);
            if (mostrarArquivo && typeof bootstrap !== 'undefined') {
                bootstrap.Tab.getOrCreateInstance(tabArqBtn);
            }
        }
    }

    function renderPendenciasLista(pendencias) {
        var pl = el('nc-pendencias-lista');
        if (!pl) return [];
        var abertas = (pendencias || []).filter(function (p) { return !p.resolvido; });
        if (!abertas.length) {
            pl.innerHTML = '<p class="text-muted mb-0">Nenhuma pendência tipada listada. Corrija conforme a observação do operacional.</p>';
            return [];
        }
        var h = '<ul class="list-unstyled mb-0">';
        var tipos = [];
        abertas.forEach(function (p) {
            var label = p.tipo_label || p.tipo || 'Pendência';
            var obs = (p.observacao || '').trim();
            if (p.tipo && tipos.indexOf(p.tipo) < 0) tipos.push(p.tipo);
            h += '<li class="mb-2"><i class="bx bx-error-circle me-1 text-warning"></i><strong>' +
                escHtml(label) + '</strong>';
            if (obs) h += '<div class="text-muted ms-3">' + escHtml(obs) + '</div>';
            h += '</li>';
        });
        h += '</ul>';
        pl.innerHTML = h;
        return tipos;
    }

    function carregarPendenciaLista() {
        var pl = el('nc-pendencias-lista');
        if (pl) pl.textContent = 'Carregando...';
        if (!ctxModal.contratoId) {
            renderPendenciasLista([]);
            aplicarVisibilidadePendencia([]);
            return Promise.resolve([]);
        }
        return fetch('/contratos/api/v2/pendencias/?contrato_id=' + encodeURIComponent(ctxModal.contratoId), {
            credentials: 'same-origin',
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.ok) {
                    if (pl) pl.textContent = data.erro || 'Erro ao carregar pendências.';
                    aplicarVisibilidadePendencia([]);
                    return [];
                }
                var tipos = renderPendenciasLista(data.pendencias || []);
                aplicarVisibilidadePendencia(tipos);
                return tipos;
            })
            .catch(function () {
                if (pl) pl.textContent = 'Erro ao carregar pendências.';
                aplicarVisibilidadePendencia([]);
                return [];
            });
    }

    function carregarPendenciaFicha() {
        var ref = getPendenciaRef();
        if (!ref) return Promise.resolve();
        limparCamposPendencia();
        limparAlertaPendencia('nc-pend-dados-alerta');
        limparAlertaPendencia('nc-pend-arq-alerta');
        var url = '/contratos/api/v2/ficha/?tipo=' + encodeURIComponent(ref.tipo) +
            '&id=' + encodeURIComponent(ref.id) + '&with_historico=0';
        return fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) throw new Error(d.erro || 'Erro ao carregar ficha.');
                ctxModal.pendenciaTipo = ref.tipo;
                ctxModal.pendenciaId = ref.id;
                preencherPendenciaFicha(d);
            });
    }

    function carregarPendenciaArquivos() {
        var ul = el('nc-pend-arq-lista');
        var vazio = el('nc-pend-arq-vazio');
        if (!ul) return Promise.resolve();
        ul.innerHTML = '<li class="list-group-item text-muted">Carregando...</li>';
        if (vazio) vazio.classList.add('d-none');
        var url;
        if (ctxModal.contratoId) {
            url = '/contratos/api/v2/contrato/' + ctxModal.contratoId + '/midia-arquivos/';
        } else if (ctxModal.solicitacaoId) {
            url = '/contratos/api/v2/solicitacao-dig/' + ctxModal.solicitacaoId + '/midia-arquivos/';
        } else {
            ul.innerHTML = '';
            return Promise.resolve();
        }
        return fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                ul.innerHTML = '';
                if (!data.ok) {
                    ul.innerHTML = '<li class="list-group-item text-danger">' + escHtml(data.erro || 'Erro ao carregar.') + '</li>';
                    return;
                }
                var arqs = data.arquivos || [];
                if (!arqs.length) {
                    if (vazio) vazio.classList.remove('d-none');
                    return;
                }
                if (vazio) vazio.classList.add('d-none');
                arqs.forEach(function (a) {
                    var tit = escHtml(a.titulo || a.nome || 'Arquivo');
                    ul.innerHTML += '<li class="list-group-item"><i class="bx bx-file me-1"></i>' + tit + '</li>';
                });
            })
            .catch(function () {
                ul.innerHTML = '<li class="list-group-item text-danger">Erro ao carregar arquivos.</li>';
            });
    }

    function abrirModalPendencia(ctx) {
        ctxModal = ctx || {};
        ctxModal.pendenciaTipo = null;
        ctxModal.pendenciaId = null;
        limparAlertaPendencia('nc-pend-dados-alerta');
        limparAlertaPendencia('nc-pend-arq-alerta');
        if (el('nc-pend-arq-titulo')) el('nc-pend-arq-titulo').value = '';
        if (el('nc-pend-arq-file')) el('nc-pend-arq-file').value = '';
        var tabDados = el('nc-pend-tab-dados-btn');
        if (tabDados && typeof bootstrap !== 'undefined') {
            bootstrap.Tab.getOrCreateInstance(tabDados).show();
        }
        var mp = el('modalNcSanarPendencia');
        if (mp && typeof bootstrap !== 'undefined') {
            bootstrap.Modal.getOrCreateInstance(mp).show();
        }
        Promise.all([
            carregarPendenciaFicha(),
            carregarPendenciaLista(),
            carregarPendenciaArquivos(),
        ]).catch(function (err) {
            mostrarAlertaPendencia('nc-pend-dados-alerta', err.message || 'Erro ao abrir pendência.');
        });
    }

    function salvarPendenciaEdicao() {
        var ref = getPendenciaRef();
        if (!ref) {
            alert('Referência inválida.');
            return Promise.resolve();
        }
        limparAlertaPendencia('nc-pend-dados-alerta');
        var payload = { cliente: {}, proposta: {}, contrato: {} };
        if (ref.tipo === 'solicitacao_dig') {
            payload.solicitacao_digitacao_id = parseInt(ref.id, 10);
        } else {
            payload.contrato_id = parseInt(ref.id, 10);
        }
        document.querySelectorAll('#modalNcSanarPendencia [data-nc-edit-field]').forEach(function (inp) {
            var bloco = inp.closest('#nc-pend-bloco-cliente, #nc-pend-bloco-proposta, #nc-pend-bloco-contrato');
            if (bloco && bloco.classList.contains('d-none')) return;
            var caminho = inp.getAttribute('data-nc-edit-field').split('.');
            var bucket = caminho[0];
            var chave = caminho[1];
            var valor = (inp.value || '').trim();
            if (!payload[bucket]) payload[bucket] = {};
            payload[bucket][chave] = valor === '' ? null : valor;
        });
        return fetch('/contratos/api/v2/contrato/editar-dados/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(payload),
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.ok) {
                    var erros = (res.campos_invalidos || []).join('; ');
                    throw new Error((res.erro || 'Falha ao salvar') + (erros ? ' — ' + erros : ''));
                }
                return carregarPendenciaFicha();
            });
    }

    function anexarPendenciaArquivo() {
        limparAlertaPendencia('nc-pend-arq-alerta');
        var fileInput = el('nc-pend-arq-file');
        if (!fileInput || !fileInput.files || !fileInput.files[0]) {
            mostrarAlertaPendencia('nc-pend-arq-alerta', 'Selecione um arquivo.');
            return Promise.resolve();
        }
        var titulo = el('nc-pend-arq-titulo') ? el('nc-pend-arq-titulo').value.trim() : '';
        var fd = new FormData();
        fd.append('titulo', titulo || fileInput.files[0].name);
        fd.append('arquivo', fileInput.files[0]);
        var url;
        if (ctxModal.contratoId) {
            url = '/contratos/api/v2/contrato/' + ctxModal.contratoId + '/cliente-arquivo/';
        } else if (ctxModal.solicitacaoId) {
            url = '/contratos/api/v2/solicitacao-dig/' + ctxModal.solicitacaoId + '/cliente-arquivo/';
        } else {
            mostrarAlertaPendencia('nc-pend-arq-alerta', 'Referência inválida.');
            return Promise.resolve();
        }
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: fd,
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.ok) throw new Error(res.erro || 'Erro ao anexar arquivo.');
                fileInput.value = '';
                if (el('nc-pend-arq-titulo')) el('nc-pend-arq-titulo').value = '';
                return carregarPendenciaArquivos();
            });
    }

    window.carregarContainerNovoContrato = carregarContainer;
    window.refreshContainerNovoContrato = function () {
        var cid = carteiraIdAtual || window.__carteiraIdAtual;
        return carregarContainer(cid || null);
    };
    window.esconderContainerNovoContrato = function () {
        carteiraIdAtual = null;
        window.__carteiraIdAtual = null;
        return carregarContainer(null);
    };

    document.addEventListener('DOMContentLoaded', function () {
        if (!window.podeNovoContrato) return;

        var btnRefresh = el('btn-nc-refresh');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', function () {
                window.refreshContainerNovoContrato();
            });
        }

        document.addEventListener('click', function (e) {
            var t = e.target.closest('.btn-nc-copiar-link');
            if (t) {
                var link = t.getAttribute('data-link') || '';
                if (link && navigator.clipboard) {
                    navigator.clipboard.writeText(link).then(function () {
                        alert('Link copiado.');
                    });
                }
                return;
            }

            t = e.target.closest('.btn-nc-checagem');
            if (t) {
                var cid = t.getAttribute('data-contrato-id');
                var acao = t.getAttribute('data-acao');
                if (!cid || !acao) return;
                if (!confirm('Confirmar checagem do link de formalização?')) return;
                postEvoluir(cid, acao, '').then(function (res) {
                    if (res.ok) {
                        window.refreshContainerNovoContrato();
                    } else {
                        alert(res.erro || res.message || 'Erro na checagem.');
                    }
                });
                return;
            }

            t = e.target.closest('.btn-nc-formalizar');
            if (t) {
                ctxModal = {
                    contratoId: t.getAttribute('data-contrato-id'),
                    acao: t.getAttribute('data-acao'),
                    link: t.getAttribute('data-link') || '',
                };
                if (el('nc-formalizar-nome')) el('nc-formalizar-nome').textContent = t.getAttribute('data-nome') || '';
                if (el('nc-formalizar-link')) el('nc-formalizar-link').textContent = ctxModal.link || '—';
                if (el('nc-formalizar-obs')) el('nc-formalizar-obs').value = '';
                if (el('nc-formalizar-video')) el('nc-formalizar-video').value = '';
                var m = el('modalNcFormalizar');
                if (m && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(m).show();
                return;
            }

            t = e.target.closest('.btn-nc-video');
            if (t) {
                ctxModal = { contratoId: t.getAttribute('data-contrato-id') };
                if (el('nc-video-nome')) el('nc-video-nome').textContent = el('nc-cliente-nome') ? el('nc-cliente-nome').textContent : '';
                if (el('nc-video-arquivo')) el('nc-video-arquivo').value = '';
                var mv = el('modalNcEnviarVideo');
                if (mv && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(mv).show();
                return;
            }

            t = e.target.closest('.btn-nc-arquivos');
            if (t) {
                ctxModal = {
                    contratoId: t.getAttribute('data-contrato-id') || null,
                    solicitacaoId: t.getAttribute('data-solicitacao-id') || null,
                };
                if (el('nc-arquivo-titulo')) el('nc-arquivo-titulo').value = '';
                if (el('nc-arquivo-file')) el('nc-arquivo-file').value = '';
                carregarArquivosLista();
                var ma = el('modalNcArquivos');
                if (ma && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(ma).show();
                return;
            }

            t = e.target.closest('.btn-nc-pendencia');
            if (t) {
                abrirModalPendencia({
                    contratoId: t.getAttribute('data-contrato-id') || null,
                    solicitacaoId: t.getAttribute('data-solicitacao-id') || null,
                });
                return;
            }

            var itemProposta = e.target.closest('.siape-container-nc__item--clicavel');
            if (itemProposta && !e.target.closest('button')) {
                var cpfItem = itemProposta.getAttribute('data-cliente-cpf') || '';
                if (cpfItem && typeof window.consultaBuscarPorCpf === 'function') {
                    window.consultaBuscarPorCpf(cpfItem);
                }
            }
        });

        var btnFormal = el('nc-btn-confirmar-formalizacao');
        if (btnFormal) {
            btnFormal.addEventListener('click', function () {
                if (!ctxModal.contratoId || !ctxModal.acao) return;
                btnFormal.disabled = true;
                var obs = el('nc-formalizar-obs') ? el('nc-formalizar-obs').value.trim() : '';
                var videoInput = el('nc-formalizar-video');
                var videoFile = videoInput && videoInput.files && videoInput.files[0] ? videoInput.files[0] : null;
                postEvoluir(ctxModal.contratoId, ctxModal.acao, obs)
                    .then(function (res) {
                        if (!res.ok) throw new Error(res.erro || res.message || 'Erro ao formalizar.');
                        if (videoFile) return uploadVideo(ctxModal.contratoId, videoFile);
                        return { ok: true };
                    })
                    .then(function () {
                        var m = el('modalNcFormalizar');
                        if (m && typeof bootstrap !== 'undefined') bootstrap.Modal.getInstance(m)?.hide();
                        window.refreshContainerNovoContrato();
                    })
                    .catch(function (err) {
                        alert(err.message || 'Erro ao formalizar.');
                    })
                    .finally(function () { btnFormal.disabled = false; });
            });
        }

        var btnVideo = el('nc-btn-enviar-video');
        if (btnVideo) {
            btnVideo.addEventListener('click', function () {
                if (!ctxModal.contratoId) return;
                var f = el('nc-video-arquivo');
                if (!f || !f.files || !f.files[0]) {
                    alert('Selecione um vídeo.');
                    return;
                }
                btnVideo.disabled = true;
                uploadVideo(ctxModal.contratoId, f.files[0])
                    .then(function (res) {
                        if (!res.ok) throw new Error(res.erro || 'Erro ao enviar vídeo.');
                        var m = el('modalNcEnviarVideo');
                        if (m && typeof bootstrap !== 'undefined') bootstrap.Modal.getInstance(m)?.hide();
                        window.refreshContainerNovoContrato();
                    })
                    .catch(function (err) { alert(err.message || 'Erro.'); })
                    .finally(function () { btnVideo.disabled = false; });
            });
        }

        var btnArquivo = el('nc-btn-enviar-arquivo');
        if (btnArquivo) {
            btnArquivo.addEventListener('click', function () {
                var titulo = el('nc-arquivo-titulo') ? el('nc-arquivo-titulo').value.trim() : '';
                var fileInput = el('nc-arquivo-file');
                if (!fileInput || !fileInput.files || !fileInput.files[0]) {
                    alert('Selecione um arquivo.');
                    return;
                }
                var fd = new FormData();
                fd.append('titulo', titulo || fileInput.files[0].name);
                fd.append('arquivo', fileInput.files[0]);
                var url;
                if (ctxModal.contratoId) {
                    url = '/contratos/api/v2/contrato/' + ctxModal.contratoId + '/cliente-arquivo/';
                } else if (ctxModal.solicitacaoId) {
                    url = '/contratos/api/v2/solicitacao-dig/' + ctxModal.solicitacaoId + '/cliente-arquivo/';
                } else {
                    alert('Referência inválida.');
                    return;
                }
                btnArquivo.disabled = true;
                fetch(url, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                    body: fd,
                })
                    .then(function (r) { return r.json(); })
                    .then(function (res) {
                        if (!res.ok) throw new Error(res.erro || 'Erro ao enviar.');
                        if (fileInput) fileInput.value = '';
                        carregarArquivosLista();
                        window.refreshContainerNovoContrato();
                    })
                    .catch(function (err) { alert(err.message || 'Erro.'); })
                    .finally(function () { btnArquivo.disabled = false; });
            });
        }

        var btnSalvarPend = el('nc-btn-salvar-pendencia');
        if (btnSalvarPend) {
            btnSalvarPend.addEventListener('click', function () {
                btnSalvarPend.disabled = true;
                salvarPendenciaEdicao()
                    .then(function () {
                        alert('Alterações salvas.');
                    })
                    .catch(function (err) {
                        mostrarAlertaPendencia('nc-pend-dados-alerta', err.message || 'Erro ao salvar.');
                    })
                    .finally(function () { btnSalvarPend.disabled = false; });
            });
        }

        var btnAnexarPend = el('nc-btn-pend-anexar-arquivo');
        if (btnAnexarPend) {
            btnAnexarPend.addEventListener('click', function () {
                btnAnexarPend.disabled = true;
                anexarPendenciaArquivo()
                    .catch(function (err) {
                        mostrarAlertaPendencia('nc-pend-arq-alerta', err.message || 'Erro ao anexar.');
                    })
                    .finally(function () { btnAnexarPend.disabled = false; });
            });
        }

        var btnSanar = el('nc-btn-sanar-pendencia');
        if (btnSanar) {
            btnSanar.addEventListener('click', function () {
                if (!confirm('Confirmar que a pendência foi corrigida e devolver ao operacional?')) return;
                btnSanar.disabled = true;
                var prom;
                if (ctxModal.contratoId) {
                    prom = fetch('/contratos/api/v2/pendencia/sanar/', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken'),
                        },
                        body: JSON.stringify({ contrato_id: parseInt(ctxModal.contratoId, 10) }),
                    }).then(function (r) { return r.json(); });
                } else if (ctxModal.solicitacaoId) {
                    prom = fetch('/contratos/api/v2/solicitacao-dig/' + ctxModal.solicitacaoId + '/correcao-concluida/', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken'),
                        },
                        body: JSON.stringify({}),
                    }).then(function (r) { return r.json(); });
                } else {
                    alert('Referência inválida.');
                    btnSanar.disabled = false;
                    return;
                }
                prom
                    .then(function (res) {
                        if (!res.ok) throw new Error(res.erro || res.message || 'Erro ao sanear.');
                        var m = el('modalNcSanarPendencia');
                        if (m && typeof bootstrap !== 'undefined') bootstrap.Modal.getInstance(m)?.hide();
                        window.refreshContainerNovoContrato();
                    })
                    .catch(function (err) { alert(err.message || 'Erro.'); })
                    .finally(function () { btnSanar.disabled = false; });
            });
        }

        window.addEventListener('resize', reparentContainer);

        // Carrega todas as propostas do vendedor ao abrir a consulta (sem CPF)
        carregarContainer(null);
    });
})();
