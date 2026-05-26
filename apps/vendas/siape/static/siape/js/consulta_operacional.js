/**
 * Simulação e Proposta operacional na consulta SIAPE (integração /contratos/api/v2).
 */
(function () {
    'use strict';

    function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    window.__carteiraIdAtual = null;
    window.__statusComercialAtual = null;
    window.__clienteCpfAtual = null;
    window.__clienteDadosPessoaisId = null;

    function setBotoesSimulacaoProposta() {
        const btnSim = document.getElementById('btn-simulacao-consulta');
        const btnProp = document.getElementById('btn-proposta-consulta');
        if (!btnSim || !btnProp) return;

        const st = (window.__statusComercialAtual || '').toUpperCase();
        const temCarteira = !!window.__carteiraIdAtual;

        btnSim.style.display = 'none';
        btnProp.style.display = 'none';
        btnSim.disabled = true;
        btnProp.disabled = true;

        if (!temCarteira) return;

        const mostraAmbos = ['EM_NEGOCIACAO', 'NEGOCIO_FECHADO', 'SIMULACAO', 'SOLICITACAO_PROPOSTAS', 'PROPOSTAS'].includes(st);
        const soProposta = st === 'OPERACIONAL' || mostraAmbos;

        if (mostraAmbos && st !== 'OPERACIONAL') {
            btnSim.style.display = 'inline-block';
            btnSim.disabled = false;
        }
        if (soProposta) {
            btnProp.style.display = 'inline-block';
            btnProp.disabled = false;
        }
    }

    window.initConsultaOperacional = function (carteiraId, statusComercial, cpf, nome) {
        window.__carteiraIdAtual = carteiraId;
        window.__statusComercialAtual = statusComercial || 'EM_NEGOCIACAO';
        window.__clienteCpfAtual = cpf || '';
        setBotoesSimulacaoProposta();

        const simCpf = document.getElementById('sim_cpf');
        const simNome = document.getElementById('sim_nome_completo');
        const simCart = document.getElementById('sim_carteira_id');
        if (simCpf) simCpf.value = cpf || '';
        if (simNome) simNome.value = nome || '';
        if (simCart) simCart.value = carteiraId || '';

        lookupClienteDadosPessoais(cpf);
    };

    function lookupClienteDadosPessoais(cpf) {
        if (!cpf) return;
        const digits = String(cpf).replace(/\D/g, '');
        fetch('/contratos/api/v2/cliente-dados-pessoais/lookup/?cpf=' + encodeURIComponent(digits), {
            credentials: 'same-origin',
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.ok && data.cliente) {
                    window.__clienteDadosPessoaisId = data.cliente.id;
                    const el = document.getElementById('sim_cliente_dados_pessoais_id');
                    if (el) el.value = data.cliente.id;
                    const propEl = document.getElementById('prop_cliente_dados_pessoais_id');
                    if (propEl) propEl.value = data.cliente.id;
                    const nome = document.getElementById('sim_nome_completo');
                    if (nome && !nome.value) nome.value = data.cliente.nome_completo || '';
                }
            })
            .catch(() => {});
    }

    function salvarClienteDadosPessoais() {
        const cpf = (document.getElementById('sim_cpf') || {}).value || window.__clienteCpfAtual;
        const nome = (document.getElementById('sim_nome_completo') || {}).value || '';
        const fd = new FormData();
        fd.append('cpf', String(cpf).replace(/\D/g, ''));
        fd.append('nome_completo', nome);
        return fetch('/contratos/api/v2/cliente-dados-pessoais/salvar/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: fd,
        }).then((r) => r.json());
    }

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

    window.abrirModalSimulacao = function () {
        if (!window.__carteiraIdAtual) {
            alert('Carteira não encontrada. Busque o cliente novamente.');
            return;
        }
        const modal = document.getElementById('modalSolicitacaoSimulacao');
        if (modal && typeof bootstrap !== 'undefined') {
            bootstrap.Modal.getOrCreateInstance(modal).show();
        }
    };

    window.abrirModalPropostas = function () {
        if (!window.__carteiraIdAtual) {
            alert('Carteira não encontrada. Busque o cliente novamente.');
            return;
        }
        carregarCatalogos().then(() => {
            const propCart = document.getElementById('prop_carteira_id');
            if (propCart) propCart.value = window.__carteiraIdAtual;
            const modal = document.getElementById('modalEnviarPropostas');
            if (modal && typeof bootstrap !== 'undefined') {
                bootstrap.Modal.getOrCreateInstance(modal).show();
            }
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        const btnSim = document.getElementById('sim_btn_enviar');
        if (btnSim) {
            btnSim.addEventListener('click', function () {
                salvarClienteDadosPessoais().then((saved) => {
                    if (!saved.ok) {
                        alert(saved.message || saved.erro || 'Erro ao salvar dados do cliente.');
                        return;
                    }
                    const dpId = saved.cliente_id || window.__clienteDadosPessoaisId;
                    const fd = new FormData();
                    fd.append('carteira_id', window.__carteiraIdAtual);
                    fd.append('cliente_dados_pessoais_id', dpId);
                    fd.append('observacao', (document.getElementById('sim_observacao') || {}).value || '');
                    const arq = document.getElementById('sim_arquivos');
                    if (arq && arq.files) {
                        for (let i = 0; i < arq.files.length; i++) {
                            fd.append('arquivos', arq.files[i]);
                        }
                    }
                    fetch('/contratos/api/v2/solicitar-simulacao/', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
                        body: fd,
                    })
                        .then((r) => r.json())
                        .then((res) => {
                            if (res.ok) {
                                alert(res.message || 'Simulação enviada.');
                                window.__statusComercialAtual = 'SIMULACAO';
                                setBotoesSimulacaoProposta();
                                const m = document.getElementById('modalSolicitacaoSimulacao');
                                if (m && bootstrap) bootstrap.Modal.getInstance(m)?.hide();
                            } else {
                                alert(res.message || 'Erro ao enviar simulação.');
                            }
                        });
                });
            });
        }

        const btnProp = document.getElementById('prop_btn_enviar');
        if (btnProp) {
            btnProp.addEventListener('click', function () {
                salvarClienteDadosPessoais().then((saved) => {
                    const dpId = saved.cliente_id || window.__clienteDadosPessoaisId;
                    const proposta = {
                        banco_id: document.getElementById('prop_banco_id').value,
                        convenio_id: document.getElementById('prop_convenio_id').value,
                        produto_id: document.getElementById('prop_produto_id').value,
                        valor_af: document.getElementById('prop_valor_af').value,
                        valor_tc: document.getElementById('prop_valor_tc').value,
                        valor_parcela: document.getElementById('prop_valor_parcela').value,
                        prazo: document.getElementById('prop_prazo').value,
                        tabela_cms_id: document.getElementById('prop_tabela_cms_id').value || null,
                    };
                    const fd = new FormData();
                    fd.append('carteira_id', window.__carteiraIdAtual);
                    fd.append('cliente_dados_pessoais_id', dpId);
                    fd.append('observacao', (document.getElementById('prop_observacao') || {}).value || '');
                    fd.append('propostas', JSON.stringify([proposta]));
                    const arq = document.getElementById('prop_arquivos');
                    if (arq && arq.files) {
                        for (let i = 0; i < arq.files.length; i++) {
                            fd.append('arquivos', arq.files[i]);
                        }
                    }
                    fetch('/contratos/api/v2/solicitar-propostas/', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
                        body: fd,
                    })
                        .then((r) => r.json())
                        .then((res) => {
                            if (res.ok) {
                                alert(res.message || 'Propostas enviadas.');
                                window.__statusComercialAtual = 'OPERACIONAL';
                                setBotoesSimulacaoProposta();
                                const m = document.getElementById('modalEnviarPropostas');
                                if (m && bootstrap) bootstrap.Modal.getInstance(m)?.hide();
                            } else {
                                alert(res.message || 'Erro ao enviar propostas.');
                            }
                        });
                });
            });
        }

        ['prop_banco_id', 'prop_convenio_id', 'prop_produto_id'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', atualizarTabelasCms);
        });
    });
})();
