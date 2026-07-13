/* Pagamento TC — financeiro_vendas (SCT52) */
(function () {
    'use strict';

    const API = '/vendas/financeiro/api/pagamento-tc/';
    let _listaItens = [];
    let _pagoTcModal = null;
    let _linhaAtual = null;
    let _tcCompSomaServidor = 0;
    let _tcCompValorTc = 0;

    function esc(s) {
        if (s === null || s === undefined) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function showToast(msg, type) {
        type = type || 'info';
        if (typeof window.showToast === 'function') {
            window.showToast(msg, type);
            return;
        }
        alert(msg);
    }

    function getJson(url) {
        return fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } }).then(function (r) {
            return r.json();
        });
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
                'X-CSRFToken': getCsrf(),
            },
            body: JSON.stringify(body || {}),
        }).then(function (r) {
            return r.json();
        });
    }

    function postMultipart(url, fd) {
        fd.append('csrfmiddlewaretoken', getCsrf());
        return fetch(url, { method: 'POST', credentials: 'same-origin', body: fd }).then(function (r) {
            return r.json();
        });
    }

    function getCsrf() {
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    function _parseNumFlex(v) {
        if (v === null || v === undefined) return NaN;
        let t = String(v).trim();
        if (!t) return NaN;
        if (t.indexOf(',') >= 0) {
            t = t.replace(/\./g, '').replace(',', '.');
        } else {
            t = t.replace(',', '.');
        }
        const n = parseFloat(t);
        return isFinite(n) ? n : NaN;
    }

    function _formatarBRL(v) {
        const n = Number(v);
        if (!isFinite(n)) return 'R$ 0,00';
        return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function _formatarValorComprovanteDigitos(digitsRaw) {
        const d = String(digitsRaw || '').replace(/\D/g, '');
        if (!d) return '';
        let cent = parseInt(d, 10);
        if (!isFinite(cent) || cent < 0) return '';
        return (cent / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function _parseValorComprovanteCampo(raw) {
        const d = String(raw || '').replace(/\D/g, '');
        if (!d) return 0;
        const cent = parseInt(d, 10);
        return isFinite(cent) && cent >= 0 ? cent / 100 : 0;
    }

    function _contratoIdModal() {
        const el = document.getElementById('pctcContratoId');
        return el && el.value ? String(el.value) : '';
    }

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

    function _buildRegistermoneyJson(opts) {
        opts = opts || {};
        const gv = function (id) {
            const el = document.getElementById(id);
            return el ? String(el.value || '').trim() : '';
        };
        const m = _pagoTcModal || {};
        const snapCms = function (k) {
            const v = m[k];
            return v === undefined || v === null ? '' : String(v).trim();
        };
        const selC = document.getElementById('evoluirPctcClassificador');
        const fc = document.getElementById('evoluirPctcFlagCms');
        const fm3 = document.getElementById('evoluirPctcForcarM3');
        let veNum = _parseNumFlex(gv('evoluirPctcValorEst'));
        if ((!isFinite(veNum) || veNum <= 0) && opts.permitirFallbackTc !== false) {
            veNum = Number(_tcCompValorTc) || 0;
        }
        const veNorm = isFinite(veNum) && veNum > 0 ? String(veNum) : gv('evoluirPctcValorEst');
        const afEl = document.getElementById('evoluirPctcAf');
        const afNorm = afEl && afEl.value ? afEl.value : snapCms('af') || m.af || '';
        const lp = _pctcPayloadLojaRm();
        return {
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
    }

    function _buildPayloadSalvar() {
        const rm = _buildRegistermoneyJson({ permitirFallbackTc: false });
        const obs = document.getElementById('pctcObservacao');
        return Object.assign(
            {
                contrato_id: parseInt(_contratoIdModal(), 10) || 0,
                observacao: obs ? String(obs.value || '').trim() : '',
            },
            rm
        );
    }

    function _validarDadosModal(permiteSemTc) {
        const ve = _parseNumFlex((document.getElementById('evoluirPctcValorEst') || {}).value);
        const semTc = !isFinite(ve) || ve <= 0;
        if (semTc && !permiteSemTc) {
            return 'Informe o Valor TC maior que zero.';
        }
        const cl = document.getElementById('evoluirPctcClassificador');
        if (!cl || !cl.value) return 'Selecione o classificador.';
        const lp = _pctcPayloadLojaRm();
        const lojas = (_pagoTcModal || {}).lojas_elegiveis || [];
        if (lp.venda_associada_loja && lojas.length === 0) {
            return 'Marque “Não” em venda associada a loja ou cadastre lojas nos funcionários.';
        }
        if (lp.venda_associada_loja && !lp.loja_id) return 'Selecione a loja da venda.';
        return null;
    }

    function _preencherRepasse(m) {
        const tem = !!m.tem_repasse;
        const badge = document.getElementById('evoluirPctcRepasseBadge');
        if (badge) {
            badge.textContent = tem ? 'Repasse: Sim' : 'Repasse: Não';
            badge.className = 'badge rounded-pill ' + (tem ? 'bg-warning text-dark' : 'bg-secondary');
        }
        const set = function (id, v) {
            const el = document.getElementById(id);
            if (el) el.textContent = v || '—';
        };
        set('evoluirPctcRepasseSolicitante', m.nome_responsavel);
        set('evoluirPctcRepasseOrigem', tem ? m.nome_repasse : '—');
        const ow = document.getElementById('evoluirPctcRepasseOrigemWrap');
        if (ow) ow.classList.toggle('d-none', !tem);
        const criador =
            (m.destinatarios || []).find(function (d) {
                return d.papel === 'vendedor';
            })?.nome || m.nome_responsavel;
        set('evoluirPctcRepasseCriador', criador);
        const resumo = document.getElementById('evoluirPctcRepasseResumo');
        if (resumo) {
            resumo.textContent = tem
                ? 'TC dividido 50% entre ' + (m.nome_responsavel || '—') + ' e ' + (m.nome_repasse || '—') + '.'
                : 'RegisterMoney integral para o responsável.';
        }
    }

    function _preencherModalPagoTc() {
        const m = _pagoTcModal || {};
        function setv(id, v) {
            const el = document.getElementById(id);
            if (el) el.value = v !== undefined && v !== null && v !== '' ? String(v) : '';
        }
        setv('evoluirPctcValorEst', m.valor_est_tc);
        setv('evoluirPctcAf', m.af);
        setv('evoluirPctcAf', m.af);
        const selCl = document.getElementById('evoluirPctcClassificador');
        if (selCl) {
            selCl.innerHTML = '<option value="">Selecione...</option>';
            (m.classificadores || m.classificacoes || []).forEach(function (c) {
                const o = document.createElement('option');
                o.value = String(c.id);
                o.textContent = (c.titulo || '') + (c.percentual ? ' (' + c.percentual + '%)' : '');
                selCl.appendChild(o);
            });
            if (m.classificacao_default_id) selCl.value = String(m.classificacao_default_id);
        }
        _preencherRepasse(m);
        const lojas = m.lojas_elegiveis || [];
        const selLj = document.getElementById('evoluirPctcLojaId');
        if (selLj) {
            selLj.innerHTML = '<option value="">Selecione...</option>';
            lojas.forEach(function (L) {
                const o = document.createElement('option');
                o.value = String(L.id);
                o.textContent = L.nome || 'Loja #' + L.id;
                selLj.appendChild(o);
            });
        }
        const hint = document.getElementById('evoluirPagoTcHint');
        if (hint) {
            hint.textContent = m.tabela_cms_titulo
                ? 'Tabela (snapshot): ' + m.tabela_cms_titulo
                : 'Informe TC, classificador e comprovantes.';
        }
        const vTcIni = Number(m.valor_est_tc);
        _tcCompValorTc = isFinite(vTcIni) ? vTcIni : 0;
        _tcCompSomaServidor = 0;
        _atualizarBadgeTc(0, _tcCompValorTc);
        const btnConf = document.getElementById('btnConfirmarPagoTc');
        if (btnConf) {
            const semTc = !isFinite(vTcIni) || vTcIni <= 0;
            btnConf.classList.toggle('d-none', !semTc);
        }
        _carregarComprovantesModal();
    }

    function _atualizarUiLoja() {
        const m = _pagoTcModal || {};
        const lojas = m.lojas_elegiveis || [];
        const rSim = document.getElementById('evoluirPctcAssocLojaSim');
        const wrapSel = document.getElementById('evoluirPctcLojaSelectWrap');
        const altSem = document.getElementById('evoluirPctcLojaSemOpcoes');
        const sim = !!(rSim && rSim.checked);
        if (altSem) altSem.classList.toggle('d-none', !(sim && lojas.length === 0));
        if (wrapSel) wrapSel.classList.toggle('d-none', !(sim && lojas.length > 0));
    }

    function _atualizarBadgeTc(soma, valorTc) {
        const s = Number(soma || 0);
        const t = Number(valorTc || 0);
        const ids = ['evoluirTcBadgeStatus', 'compParcialBadgeStatus'];
        ids.forEach(function (bid) {
            const badge = document.getElementById(bid);
            if (!badge) return;
            if (t <= 0) {
                badge.textContent = 'Sem TC';
                badge.className = 'badge rounded-pill bg-secondary';
            } else if (s <= 0) {
                badge.textContent = 'Aguardando';
                badge.className = 'badge rounded-pill bg-secondary';
            } else if (s < t) {
                badge.textContent = 'Pago TC Parcial';
                badge.className = 'badge rounded-pill bg-warning text-dark';
            } else {
                badge.textContent = 'Pago TC Total';
                badge.className = 'badge rounded-pill bg-success';
            }
        });
        const map = {
            evoluirTcSomaAcumulada: s,
            evoluirTcValorTc: t,
            evoluirTcSaldo: Math.max(0, t - s),
            compParcialTcPago: s,
            compParcialTcMeta: t,
            compParcialSaldo: Math.max(0, t - s),
        };
        Object.keys(map).forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.textContent = _formatarBRL(map[id]);
        });
    }

    function _renderComprovantes(lista, tbodyId) {
        const tbody = document.getElementById(tbodyId || 'evoluirTcCompLista');
        if (!tbody) return;
        if (!lista || !lista.length) {
            tbody.innerHTML =
                '<tr><td colspan="5" class="text-muted small text-center py-2">Nenhum comprovante registrado.</td></tr>';
            return;
        }
        tbody.innerHTML = lista
            .map(function (c) {
                const dt = c.criado_em ? new Date(c.criado_em).toLocaleString('pt-BR') : '—';
                const arq = c.arquivo_url
                    ? '<a href="' + esc(c.arquivo_url) + '" target="_blank" rel="noopener">Ver</a>'
                    : '—';
                return (
                    '<tr><td class="small">' +
                    esc(dt) +
                    '</td><td class="small">' +
                    _formatarBRL(c.valor) +
                    '</td><td class="small">' +
                    esc(c.criado_por) +
                    '</td><td class="small">' +
                    arq +
                    '</td><td class="text-end"><button type="button" class="btn btn-link btn-sm text-danger p-0 js-excluir-comp" data-id="' +
                    esc(String(c.id)) +
                    '"><i class="bx bx-trash"></i></button></td></tr>'
                );
            })
            .join('');
    }

    function _carregarComprovantesModal() {
        const cid = _contratoIdModal();
        if (!cid) return;
        getJson(API + 'comprovantes/?contrato_id=' + encodeURIComponent(cid)).then(function (d) {
            if (!d || !d.ok) return;
            _renderComprovantes(d.comprovantes);
            const soma = Number(d.soma);
            const vtc = Number(d.valor_tc);
            _tcCompSomaServidor = isFinite(soma) ? soma : 0;
            _tcCompValorTc = isFinite(vtc) ? vtc : 0;
            _atualizarBadgeTc(_tcCompSomaServidor, _tcCompValorTc);
        });
    }

    function _carregarComprovantesParcial() {
        const cid = (document.getElementById('compParcialContratoId') || {}).value;
        if (!cid) return;
        getJson(API + 'comprovantes/?contrato_id=' + encodeURIComponent(cid)).then(function (d) {
            if (!d || !d.ok) return;
            _renderComprovantes(d.comprovantes, 'compParcialLista');
            const soma = Number(d.soma);
            const vtc = Number(d.valor_tc);
            _atualizarBadgeTc(isFinite(soma) ? soma : 0, isFinite(vtc) ? vtc : 0);
        });
    }

    function _fmtMoedaCol(v) {
        const n = _parseNumFlex(v);
        return isFinite(n) ? _formatarBRL(n) : esc(v || '—');
    }

    function _renderTabela(tbodyId, itens, comAcoes) {
        const tbody = document.getElementById(tbodyId);
        if (!tbody) return;
        if (!itens.length) {
            const cols = comAcoes ? 10 : 9;
            tbody.innerHTML =
                '<tr><td colspan="' + cols + '" class="text-center text-muted py-3">Nenhum contrato nesta aba.</td></tr>';
            return;
        }
        tbody.innerHTML = itens
            .map(function (r) {
                let acoes = '';
                if (comAcoes) {
                    if (r.pode_pagar_tc) {
                        acoes +=
                            '<button type="button" class="btn btn-sm btn-primary js-pagar-tc" data-id="' +
                            r.contrato_id +
                            '">Pagar TC</button>';
                    } else if (r.pode_comprovante) {
                        acoes +=
                            '<button type="button" class="btn btn-sm btn-warning js-add-comp" data-id="' +
                            r.contrato_id +
                            '">Adicionar comprovante</button>';
                    }
                }
                return (
                    '<tr>' +
                    '<td>' +
                    esc(r.cliente_nome) +
                    '</td><td>' +
                    esc(r.cpf) +
                    '</td><td>' +
                    esc(r.vendedor) +
                    '</td><td>' +
                    esc(r.produto) +
                    '</td><td>' +
                    esc(r.banco) +
                    '</td><td class="text-end">' +
                    _fmtMoedaCol(r.valor_af) +
                    '</td><td class="text-end">' +
                    _fmtMoedaCol(r.valor_tc) +
                    '</td><td class="text-end">' +
                    _fmtMoedaCol(r.tc_pago_acumulado) +
                    '</td><td><span class="badge bg-light text-dark border">' +
                    esc(r.sub_label) +
                    '</span></td>' +
                    (comAcoes ? '<td class="text-end">' + acoes + '</td>' : '') +
                    '</tr>'
                );
            })
            .join('');
    }

    function _atualizarListas() {
        const ag = _listaItens.filter(function (i) {
            return i.aba === 'aguardando';
        });
        const par = _listaItens.filter(function (i) {
            return i.aba === 'parcial';
        });
        const con = _listaItens.filter(function (i) {
            return i.aba === 'concluidos';
        });
        _renderTabela('tbodyAguardando', ag, true);
        _renderTabela('tbodyParcial', par, true);
        _renderTabela('tbodyConcluidos', con, false);
        const ba = document.getElementById('badgeAguardando');
        const bp = document.getElementById('badgeParcial');
        const bc = document.getElementById('badgeConcluidos');
        if (ba) ba.textContent = String(ag.length);
        if (bp) bp.textContent = String(par.length);
        if (bc) bc.textContent = String(con.length);
    }

    function carregarLista() {
        getJson(API + 'listar/')
            .then(function (d) {
                if (!d || !d.ok) {
                    showToast((d && d.erro) || 'Erro ao carregar lista.', 'danger');
                    return;
                }
                _listaItens = d.itens || [];
                _atualizarListas();
            })
            .catch(function () {
                showToast('Erro de comunicação ao carregar lista.', 'danger');
            });
    }

    function abrirModalPagoTc(contratoId) {
        _linhaAtual = _listaItens.find(function (i) {
            return String(i.contrato_id) === String(contratoId);
        });
        document.getElementById('pctcContratoId').value = String(contratoId);
        if (_linhaAtual) {
            document.getElementById('pctcResumoCliente').textContent = _linhaAtual.cliente_nome;
            document.getElementById('pctcResumoCpf').textContent = _linhaAtual.cpf;
            document.getElementById('pctcResumoVendedor').textContent = _linhaAtual.vendedor;
            document.getElementById('pctcResumoProduto').textContent = _linhaAtual.produto;
        }
        getJson(API + 'modal-defaults/?contrato_id=' + encodeURIComponent(contratoId))
            .then(function (d) {
                if (!d || !d.ok) {
                    showToast((d && d.erro) || 'Erro ao carregar modal.', 'danger');
                    return;
                }
                _pagoTcModal = d.pago_tc_modal || {};
                _pagoTcModal.contrato_id = contratoId;
                _preencherModalPagoTc();
                bootstrap.Modal.getOrCreateInstance(document.getElementById('modalPagoTc')).show();
            })
            .catch(function () {
                showToast('Erro de comunicação.', 'danger');
            });
    }

    function abrirModalParcial(contratoId) {
        _linhaAtual = _listaItens.find(function (i) {
            return String(i.contrato_id) === String(contratoId);
        });
        document.getElementById('compParcialContratoId').value = String(contratoId);
        if (_linhaAtual) {
            document.getElementById('compParcialCliente').textContent = _linhaAtual.cliente_nome;
            document.getElementById('compParcialCpf').textContent = _linhaAtual.cpf;
            document.getElementById('compParcialTcMeta').textContent = _formatarBRL(_linhaAtual.valor_tc);
            document.getElementById('compParcialTcPago').textContent = _formatarBRL(_linhaAtual.tc_pago_acumulado);
            const meta = _parseNumFlex(_linhaAtual.valor_tc);
            const pago = _parseNumFlex(_linhaAtual.tc_pago_acumulado);
            document.getElementById('compParcialSaldo').textContent = _formatarBRL(
                isFinite(meta) && isFinite(pago) ? Math.max(0, meta - pago) : 0
            );
        }
        document.getElementById('compParcialValor').value = '';
        document.getElementById('compParcialArquivo').value = '';
        _carregarComprovantesParcial();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalCompParcial')).show();
    }

    function salvarDadosModal() {
        const err = _validarDadosModal(false);
        if (err) {
            showToast(err, 'warning');
            return;
        }
        const btn = document.getElementById('evoluirPctcSalvarDados');
        if (btn) btn.disabled = true;
        postJson(API + 'salvar-dados/', _buildPayloadSalvar())
            .then(function (r) {
                if (btn) btn.disabled = false;
                if (!r || !r.ok) {
                    showToast((r && r.erro) || 'Erro ao salvar.', 'danger');
                    return;
                }
                const vTc = parseFloat(String(r.valor_tc || '').replace(',', '.'));
                if (isFinite(vTc)) _tcCompValorTc = vTc;
                _carregarComprovantesModal();
                showToast('Dados salvos.', 'success');
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                showToast('Erro de comunicação.', 'danger');
            });
    }

    function enviarComprovanteModal() {
        const cid = _contratoIdModal();
        const alerta = document.getElementById('evoluirTcCompAlerta');
        const valor = _parseValorComprovanteCampo((document.getElementById('evoluirTcCompValor') || {}).value);
        const arq = document.getElementById('evoluirTcCompArquivo');
        if (!cid) return;
        if (!valor || valor <= 0) {
            if (alerta) {
                alerta.textContent = 'Informe valor válido.';
                alerta.classList.remove('d-none');
            }
            return;
        }
        if (!arq || !arq.files || !arq.files[0]) {
            if (alerta) {
                alerta.textContent = 'Anexe o arquivo.';
                alerta.classList.remove('d-none');
            }
            return;
        }
        const cl = document.getElementById('evoluirPctcClassificador');
        if (!cl || !cl.value) {
            if (alerta) {
                alerta.textContent = 'Selecione o classificador antes do comprovante.';
                alerta.classList.remove('d-none');
            }
            return;
        }
        if (alerta) alerta.classList.add('d-none');
        const fd = new FormData();
        fd.append('contrato_id', cid);
        fd.append('valor', String(valor));
        fd.append('arquivo', arq.files[0]);
        fd.append('registermoney', JSON.stringify(_buildRegistermoneyJson()));
        const btn = document.getElementById('evoluirTcCompEnviar');
        if (btn) btn.disabled = true;
        postMultipart(API + 'comprovante/', fd)
            .then(function (j) {
                if (btn) btn.disabled = false;
                if (!j || !j.ok) {
                    showToast((j && j.erro) || 'Falha no upload.', 'danger');
                    return;
                }
                arq.value = '';
                document.getElementById('evoluirTcCompValor').value = '';
                _tcCompSomaServidor = Number(j.soma_acumulada) || 0;
                _tcCompValorTc = Number(j.valor_tc) || _tcCompValorTc;
                _carregarComprovantesModal();
                carregarLista();
                showToast(j.total_atingido ? 'Pago TC Total.' : 'Comprovante registrado.', 'success');
                if (j.sub_status && j.sub_status !== 'PG_PAGO_CLIENTE') {
                    bootstrap.Modal.getInstance(document.getElementById('modalPagoTc')).hide();
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                showToast('Erro de comunicação.', 'danger');
            });
    }

    function enviarComprovanteParcial() {
        const cid = (document.getElementById('compParcialContratoId') || {}).value;
        const valor = _parseValorComprovanteCampo((document.getElementById('compParcialValor') || {}).value);
        const arq = document.getElementById('compParcialArquivo');
        if (!cid || !valor || valor <= 0 || !arq || !arq.files[0]) {
            showToast('Informe valor e arquivo.', 'warning');
            return;
        }
        const fd = new FormData();
        fd.append('contrato_id', cid);
        fd.append('valor', String(valor));
        fd.append('arquivo', arq.files[0]);
        const btn = document.getElementById('compParcialEnviar');
        if (btn) btn.disabled = true;
        postMultipart(API + 'comprovante/', fd)
            .then(function (j) {
                if (btn) btn.disabled = false;
                if (!j || !j.ok) {
                    showToast((j && j.erro) || 'Falha no upload.', 'danger');
                    return;
                }
                arq.value = '';
                document.getElementById('compParcialValor').value = '';
                _carregarComprovantesParcial();
                carregarLista();
                showToast(j.total_atingido ? 'Pago TC Total concluído.' : 'Comprovante adicionado.', 'success');
                if (j.total_atingido) {
                    bootstrap.Modal.getInstance(document.getElementById('modalCompParcial')).hide();
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                showToast('Erro de comunicação.', 'danger');
            });
    }

    function excluirComprovante(compId, modoParcial) {
        const cid = modoParcial
            ? (document.getElementById('compParcialContratoId') || {}).value
            : _contratoIdModal();
        if (!cid || !compId || !window.confirm('Excluir este comprovante?')) return;
        postJson(API + 'comprovante/excluir/', {
            contrato_id: parseInt(cid, 10),
            comprovante_id: parseInt(compId, 10),
        })
            .then(function (j) {
                if (!j || !j.ok) {
                    showToast((j && j.erro) || 'Falha ao excluir.', 'danger');
                    return;
                }
                if (modoParcial) {
                    _carregarComprovantesParcial();
                } else {
                    _carregarComprovantesModal();
                }
                carregarLista();
                showToast('Comprovante excluído.', 'success');
            })
            .catch(function () {
                showToast('Erro de comunicação.', 'danger');
            });
    }

    function confirmarPagoTc() {
        const ve = _parseNumFlex((document.getElementById('evoluirPctcValorEst') || {}).value);
        const semTc = !isFinite(ve) || ve <= 0;
        if (!semTc) {
            showToast('Com TC > 0, registre o pagamento pelos comprovantes.', 'info');
            return;
        }
        const err = _validarDadosModal(true);
        if (err) {
            showToast(err, 'warning');
            return;
        }
        const payload = _buildPayloadSalvar();
        const btn = document.getElementById('btnConfirmarPagoTc');
        if (btn) btn.disabled = true;
        postJson(API + 'confirmar/', payload)
            .then(function (r) {
                if (btn) btn.disabled = false;
                if (!r || !r.ok) {
                    showToast((r && r.erro) || 'Erro ao confirmar.', 'danger');
                    return;
                }
                bootstrap.Modal.getInstance(document.getElementById('modalPagoTc')).hide();
                carregarLista();
                showToast('Pago TC confirmado.', 'success');
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                showToast('Erro de comunicação.', 'danger');
            });
    }

    function bindEvents() {
        document.getElementById('btnRecarregarLista').addEventListener('click', carregarLista);

        document.getElementById('tbodyAguardando').addEventListener('click', function (e) {
            const btn = e.target.closest('.js-pagar-tc');
            if (btn) abrirModalPagoTc(btn.getAttribute('data-id'));
        });
        document.getElementById('tbodyParcial').addEventListener('click', function (e) {
            const btn = e.target.closest('.js-add-comp');
            if (btn) abrirModalParcial(btn.getAttribute('data-id'));
        });

        document.getElementById('evoluirPctcSalvarDados').addEventListener('click', salvarDadosModal);
        document.getElementById('evoluirTcCompEnviar').addEventListener('click', enviarComprovanteModal);
        document.getElementById('btnConfirmarPagoTc').addEventListener('click', confirmarPagoTc);
        document.getElementById('compParcialEnviar').addEventListener('click', enviarComprovanteParcial);

        document.getElementById('evoluirTcCompLista').addEventListener('click', function (e) {
            const btn = e.target.closest('.js-excluir-comp');
            if (btn) excluirComprovante(btn.getAttribute('data-id'), false);
        });
        document.getElementById('compParcialLista').addEventListener('click', function (e) {
            const btn = e.target.closest('.js-excluir-comp');
            if (btn) excluirComprovante(btn.getAttribute('data-id'), true);
        });

        const wrapLoja = document.getElementById('evoluirPctcLojaWrap');
        if (wrapLoja) {
            wrapLoja.addEventListener('change', function (e) {
                if (
                    e.target &&
                    (e.target.id === 'evoluirPctcAssocLojaSim' ||
                        e.target.id === 'evoluirPctcAssocLojaNao' ||
                        e.target.id === 'evoluirPctcLojaId')
                ) {
                    _atualizarUiLoja();
                }
            });
        }

        ['evoluirTcCompValor', 'compParcialValor'].forEach(function (id) {
            const inp = document.getElementById(id);
            if (inp) {
                inp.addEventListener('input', function () {
                    const fmt = _formatarValorComprovanteDigitos(inp.value);
                    if (fmt !== inp.value) inp.value = fmt;
                });
            }
        });

        const ve = document.getElementById('evoluirPctcValorEst');
        if (ve) {
            ve.addEventListener('input', function () {
                const v = _parseNumFlex(ve.value);
                if (isFinite(v) && v > 0) {
                    _tcCompValorTc = v;
                    _atualizarBadgeTc(_tcCompSomaServidor, _tcCompValorTc);
                }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        bindEvents();
        carregarLista();
    });
})();
