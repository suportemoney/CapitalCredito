/**
 * Integração operacional na consulta SIAPE — apenas envio de propostas (sem simulação).
 */
(function () {
    'use strict';

    window.__carteiraIdAtual = null;
    window.__statusComercialAtual = null;
    window.__clienteCpfAtual = null;
    window.__clienteDadosPessoaisId = null;

    const STATUS_COM_PROPOSTA = [
        'EM_NEGOCIACAO',
        'NEGOCIO_FECHADO',
        'SOLICITACAO_PROPOSTAS',
        'PROPOSTAS',
        'OPERACIONAL',
    ];

    function setBotaoProposta() {
        if (!window.podeNovoContrato) return;

        const btnProp = document.getElementById('btn-proposta-consulta');
        if (!btnProp) return;

        const temCarteira = !!window.__carteiraIdAtual;
        const st = (window.__statusComercialAtual || '').toUpperCase();

        btnProp.style.display = 'none';
        btnProp.disabled = true;

        if (!temCarteira) return;

        if (STATUS_COM_PROPOSTA.includes(st)) {
            btnProp.style.display = 'inline-block';
            btnProp.disabled = false;
        }
    }

    window.initConsultaOperacional = function (carteiraId, statusComercial, cpf, nome) {
        window.__carteiraIdAtual = carteiraId;
        window.__statusComercialAtual = statusComercial || 'EM_NEGOCIACAO';
        window.__clienteCpfAtual = cpf || '';
        window.__clienteNomeAtual = nome || '';
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
        const q = '?banco_id=' + encodeURIComponent(b.value) +
            '&convenio_id=' + encodeURIComponent(c.value) +
            '&produto_id=' + encodeURIComponent(p.value);
        fetch('/contratos/api/v2/tabelas-cms-filtradas/' + q, { credentials: 'same-origin' })
            .then((r) => r.json())
            .then((data) => {
                tcm.innerHTML = '<option value="">—</option>';
                if (data.ok && data.tabelas) {
                    data.tabelas.forEach((t) => {
                        tcm.innerHTML += '<option value="' + t.id + '">' + (t.titulo || '') + '</option>';
                    });
                }
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
    });

    window.consultaOperacionalAtualizarStatus = function (status) {
        window.__statusComercialAtual = status;
        setBotaoProposta();
    };
})();
