/**
 * Integração operacional na consulta SIAPE — apenas envio de propostas (sem simulação).
 */
(function () {
    'use strict';

    window.__carteiraIdAtual = null;
    window.__statusComercialAtual = null;
    window.__clienteCpfAtual = null;
    window.__clienteDadosPessoaisId = null;

    /** Status que impedem novo envio de proposta; demais status liberam o botão. */
    const STATUS_BLOQUEIA_PROPOSTA = [
        'FINALIZADA',
        'SEM_INTERESSE',
        'DESISTENCIA',
        'NAO_E_O_CLIENTE',
    ];

    function setBotaoProposta() {
        if (!window.podeNovoContrato) return;

        const btnProp = document.getElementById('btn-proposta-consulta');
        if (!btnProp) return;

        const temCarteira = !!window.__carteiraIdAtual;
        const st = (window.__statusComercialAtual || '').toUpperCase();
        const temPropostas = !!window.__carteiraTemPropostas;

        btnProp.style.display = 'none';
        btnProp.disabled = true;

        if (!temCarteira) return;

        if (temPropostas || !STATUS_BLOQUEIA_PROPOSTA.includes(st)) {
            btnProp.style.display = 'inline-block';
            btnProp.disabled = false;
        }
    }

    window.atualizarBotaoPropostaConsulta = setBotaoProposta;

    window.initConsultaOperacional = function (carteiraId, statusComercial, cpf, nome) {
        window.__carteiraIdAtual = carteiraId;
        window.__statusComercialAtual = statusComercial || 'EM_NEGOCIACAO';
        window.__clienteCpfAtual = cpf || '';
        window.__clienteNomeAtual = nome || '';
        window.__carteiraTemPropostas = false;
        setBotaoProposta();

        const propCart = document.getElementById('prop_carteira_id');
        if (propCart) propCart.value = carteiraId || '';
    };

    function carregarCatalogos() {
        return fetch('/contratos/api/v2/catalogos/', { credentials: 'same-origin' })
            .then((r) => r.json())
            .then((data) => {
                if (!data.ok) return;
                const banco = document.getElementById('prop_banco_id');
                const conv = document.getElementById('prop_convenio_id');
                const prod = document.getElementById('prop_produto_id');
                if (banco) {
                    banco.innerHTML = '<option value="">Selecione...</option>';
                    (data.bancos || []).forEach((b) => {
                        banco.innerHTML += '<option value="' + b.id + '">' + (b.titulo || '') + '</option>';
                    });
                }
                if (conv) {
                    conv.innerHTML = '<option value="">Selecione...</option>';
                    (data.convenios || []).forEach((c) => {
                        conv.innerHTML += '<option value="' + c.id + '">' + (c.titulo || '') + '</option>';
                    });
                }
                if (prod) {
                    prod.innerHTML = '<option value="">Selecione...</option>';
                    (data.produtos || []).forEach((p) => {
                        prod.innerHTML += '<option value="' + p.id + '">' + (p.titulo || '') + '</option>';
                    });
                }
            });
    }

    function atualizarTabelasCms() {
        const b = document.getElementById('prop_banco_id');
        const c = document.getElementById('prop_convenio_id');
        const p = document.getElementById('prop_produto_id');
        const tcm = document.getElementById('prop_tabela_cms_id');
        if (!b || !c || !p || !tcm) return;

        if (!b.value || !c.value || !p.value) {
            tcm.disabled = true;
            tcm.innerHTML = '<option value="">Selecione Banco + Convênio + Produto...</option>';
            return;
        }

        tcm.disabled = true;
        tcm.innerHTML = '<option value="">Carregando tabelas...</option>';

        const q = '?banco_id=' + encodeURIComponent(b.value) +
            '&convenio_id=' + encodeURIComponent(c.value) +
            '&produto_id=' + encodeURIComponent(p.value);
        fetch('/contratos/api/v2/tabelas-cms-filtradas/' + q, { credentials: 'same-origin' })
            .then((r) => r.json())
            .then((data) => {
                const tabelas = (data.ok && data.tabelas) ? data.tabelas : [];
                if (!tabelas.length) {
                    tcm.innerHTML = '<option value="" disabled selected>---nenhuma tabela disponível---</option>';
                    tcm.disabled = true;
                    return;
                }
                const labelClassif = { M1: ' [M1 - 100%]', M2: ' [M2 - 50%]', M3: ' [M3 - 0%]' };
                let html = '<option value="">Selecione a Tabela CMS...</option>';
                tabelas.forEach((t) => {
                    const cls = String(t.classificador_banco || '').toUpperCase();
                    const sufixo = labelClassif[cls] || '';
                    html += '<option value="' + t.id + '">' + (t.titulo || '') + sufixo + '</option>';
                });
                tcm.innerHTML = html;
                tcm.disabled = false;
            })
            .catch(function () {
                tcm.innerHTML = '<option value="" disabled selected>---nenhuma tabela disponível---</option>';
                tcm.disabled = true;
            });
    }

    function extrairPrazoTituloCms(titulo) {
        const m = String(titulo || '').match(/(\d{1,3})\s*[xX]\b/);
        if (m) return parseInt(m[1], 10);
        return null;
    }

    function carregarPropostasExistentes(carteiraId, clienteDpId) {
        if (!carteiraId) {
            window.__propostasExistentesCliente = [];
            return Promise.resolve();
        }
        var url = '/api/consulta/operacional/?carteira_id=' + encodeURIComponent(carteiraId);
        if (clienteDpId) {
            url += '&cliente_dados_pessoais_id=' + encodeURIComponent(clienteDpId);
        }
        return fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                window.__propostasExistentesCliente =
                    (data.status === 'sucesso' && data.itens) ? data.itens : [];
            })
            .catch(function () {
                window.__propostasExistentesCliente = [];
            });
    }

    window.abrirModalPropostas = function () {
        if (!window.podeNovoContrato) return;
        if (!window.__carteiraIdAtual) {
            alert('Carteira não encontrada. Busque o cliente novamente.');
            return;
        }

        const propCart = document.getElementById('prop_carteira_id');
        if (propCart) propCart.value = window.__carteiraIdAtual;

        const nome = window.__clienteNomeAtual || '';
        const cpf = window.__clienteCpfAtual || '';

        Promise.all([
            carregarCatalogos(),
            typeof window.propWizardReset === 'function'
                ? window.propWizardReset()
                : Promise.resolve(),
        ]).then(function () {
            if (typeof window.propWizardCarregarFicha === 'function') {
                return window.propWizardCarregarFicha(cpf, window.__carteiraIdAtual, nome);
            }
        }).then(function () {
            var dpId = document.getElementById('prop_cliente_dados_pessoais_id');
            return carregarPropostasExistentes(
                window.__carteiraIdAtual,
                dpId && dpId.value ? dpId.value : null
            );
        }).then(function () {
            const modal = document.getElementById('modalEnviarPropostas');
            if (modal && typeof bootstrap !== 'undefined') {
                bootstrap.Modal.getOrCreateInstance(modal).show();
            }
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        ['prop_banco_id', 'prop_convenio_id', 'prop_produto_id'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', atualizarTabelasCms);
        });

        const tcm = document.getElementById('prop_tabela_cms_id');
        if (tcm) {
            tcm.addEventListener('change', function () {
                const opt = tcm.options[tcm.selectedIndex];
                if (!opt || !opt.value) return;
                const prazo = extrairPrazoTituloCms(opt.textContent);
                const prazoInp = document.getElementById('prop_prazo');
                if (prazo && prazoInp && !prazoInp.value) {
                    prazoInp.value = String(prazo);
                }
            });
        }
    });

    window.consultaOperacionalAtualizarStatus = function (status, opts) {
        window.__statusComercialAtual = status;
        setBotaoProposta();
        var skipRefresh = opts && opts.refreshContainer === false;
        if (!skipRefresh && typeof window.refreshContainerNovoContrato === 'function') {
            window.refreshContainerNovoContrato();
        }
    };
})();
