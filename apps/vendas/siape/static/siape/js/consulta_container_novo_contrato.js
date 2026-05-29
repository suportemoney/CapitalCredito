/**
 * Container operacional CX48 na consulta SIAPE.
 */
(function () {
    'use strict';

    var carteiraIdAtual = null;
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

    function renderItens(itens) {
        var lista = el('nc-itens-lista');
        var vazio = el('nc-itens-vazio');
        if (!lista) return;
        if (!itens || !itens.length) {
            lista.innerHTML = '';
            if (vazio) vazio.classList.remove('d-none');
            return;
        }
        if (vazio) vazio.classList.add('d-none');
        var html = '';
        itens.forEach(function (it) {
            html += '<div class="siape-container-nc__item" data-proposta-id="' + escHtml(it.proposta_id) + '">';
            html += '<div class="fw-semibold small">' + escHtml(it.proposta_codigo || 'Proposta') +
                (it.contrato_codigo ? ' · ' + escHtml(it.contrato_codigo) : '') + '</div>';
            html += '<div class="siape-container-nc__item-meta">' +
                escHtml(it.banco) + (it.produto ? ' · ' + escHtml(it.produto) : '') + '</div>';
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
                html += '<button type="button" class="btn btn-success btn-sm btn-nc-formalizar" ' +
                    'data-contrato-id="' + escHtml(it.contrato_id) + '" data-acao="' +
                    escHtml(it.acao_evoluir_formalizado) + '" data-link="' +
                    escHtml(it.link_formalizacao) + '" data-nome="' +
                    escHtml(el('nc-cliente-nome') ? el('nc-cliente-nome').textContent : '') + '">' +
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
        if (el('nc-cliente-nome')) el('nc-cliente-nome').textContent = data.cliente_nome || '—';
        if (el('nc-cliente-cpf')) el('nc-cliente-cpf').textContent = formatCpf(data.cliente_cpf);
        var statusParts = [];
        if (data.tabulacao_operacional) statusParts.push(data.tabulacao_operacional);
        if (data.tag_status_operacional) statusParts.push(data.tag_status_operacional);
        if (data.status_comercial) statusParts.push(data.status_comercial);
        if (el('nc-carteira-status')) {
            el('nc-carteira-status').textContent = statusParts.length ? statusParts.join(' · ') : '—';
        }
        renderItens(data.itens || []);
        reparentContainer();
        box.style.display = 'block';
    }

    function carregarContainer(carteiraId) {
        if (!window.podeNovoContrato || !carteiraId) {
            var box = el('siape-container-novo-contrato');
            if (box) box.style.display = 'none';
            return Promise.resolve();
        }
        carteiraIdAtual = carteiraId;
        return fetch('/siape/api/consulta/container-novo-contrato/?carteira_id=' + encodeURIComponent(carteiraId), {
            credentials: 'same-origin',
        })
            .then(function (r) { return r.json(); })
            .then(function (data) { renderContainer(data); })
            .catch(function () {
                var box = el('siape-container-novo-contrato');
                if (box) box.style.display = 'none';
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

    window.carregarContainerNovoContrato = carregarContainer;
    window.refreshContainerNovoContrato = function () {
        if (carteiraIdAtual) return carregarContainer(carteiraIdAtual);
        return Promise.resolve();
    };
    window.esconderContainerNovoContrato = function () {
        carteiraIdAtual = null;
        var box = el('siape-container-novo-contrato');
        if (box) box.style.display = 'none';
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
                ctxModal = {
                    contratoId: t.getAttribute('data-contrato-id') || null,
                    solicitacaoId: t.getAttribute('data-solicitacao-id') || null,
                };
                var pl = el('nc-pendencias-lista');
                if (pl) pl.innerHTML = '';
                if (ctxModal.contratoId) {
                    fetch('/contratos/api/v2/pendencias/?contrato_id=' + encodeURIComponent(ctxModal.contratoId), {
                        credentials: 'same-origin',
                    })
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            if (!pl) return;
                            if (!data.ok || !(data.pendencias || []).length) {
                                pl.innerHTML = '<p class="text-muted mb-0">Nenhuma pendência listada.</p>';
                                return;
                            }
                            var h = '<ul class="list-unstyled mb-0">';
                            data.pendencias.forEach(function (p) {
                                if (!p.resolvido) {
                                    h += '<li><i class="bx bx-error-circle me-1"></i>' + escHtml(p.tipo || p.descricao || 'Pendência') + '</li>';
                                }
                            });
                            h += '</ul>';
                            pl.innerHTML = h;
                        });
                }
                var mp = el('modalNcSanarPendencia');
                if (mp && typeof bootstrap !== 'undefined') bootstrap.Modal.getOrCreateInstance(mp).show();
                return;
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

        var btnSanar = el('nc-btn-sanar-pendencia');
        if (btnSanar) {
            btnSanar.addEventListener('click', function () {
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
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
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
    });
})();
