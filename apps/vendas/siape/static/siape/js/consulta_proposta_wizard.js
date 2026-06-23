/**
 * Wizard 3 passos — Enviar Propostas na consulta SIAPE.
 */
(function () {
    'use strict';

    let passoAtual = 1;
    let arquivosSelecionados = null;

    function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    function el(id) {
        return document.getElementById(id);
    }

    function normCpf(v) {
        return String(v || '').replace(/\D/g, '');
    }

    /** Lê decimal não negativo de um input; retorna null se vazio/inválido. */
    function lerNumInput(id) {
        var field = el(id);
        if (!field) return null;
        var raw = String(field.value || '').trim();
        if (raw === '') return null;
        var n = parseFloat(raw.replace(/\./g, '').replace(',', '.'));
        if (isNaN(n) || n < 0) return null;
        return n;
    }

    /** Escreve decimal formatado sem disparar loop desnecessário. */
    function escreverNumInput(id, valor, casas) {
        if (valor === null || typeof valor === 'undefined' || isNaN(valor)) return;
        var dec = (typeof casas === 'number') ? casas : 2;
        var txt = (Math.round(valor * Math.pow(10, dec)) / Math.pow(10, dec)).toFixed(dec);
        var field = el(id);
        if (field && field.value !== txt) {
            field.value = txt.replace('.', ',');
        }
    }

    /** Recalcula AF / Coef / Liberado conforme campo editado (espelho MoneyConsig). */
    function recalcularFinanceiroProposta(fonte) {
        var parcela = lerNumInput('prop_valor_parcela');
        var coef = lerNumInput('prop_coeficiente');
        var af = lerNumInput('prop_valor_af');
        var tc = lerNumInput('prop_valor_tc');

        function seguro(n) {
            return typeof n === 'number' && isFinite(n) && n > 0;
        }

        if (fonte === 'coeficiente') {
            if (seguro(parcela) && seguro(coef)) {
                af = parcela / coef;
                escreverNumInput('prop_valor_af', af, 2);
            }
        } else if (fonte === 'af') {
            if (seguro(parcela) && seguro(af)) {
                coef = parcela / af;
                escreverNumInput('prop_coeficiente', coef, 6);
            }
        } else if (fonte === 'parcela') {
            if (seguro(parcela) && seguro(coef)) {
                af = parcela / coef;
                escreverNumInput('prop_valor_af', af, 2);
            } else if (seguro(parcela) && seguro(af)) {
                coef = parcela / af;
                escreverNumInput('prop_coeficiente', coef, 6);
            }
        }

        af = lerNumInput('prop_valor_af');
        tc = lerNumInput('prop_valor_tc');
        if (typeof af === 'number' && af >= 0 && isFinite(af)) {
            var tcEff = (typeof tc === 'number' && tc > 0) ? tc : 0;
            var liberado = af - tcEff;
            if (liberado < 0) liberado = 0;
            escreverNumInput('prop_valor_liberado', liberado, 2);
        } else if (el('prop_valor_liberado')) {
            el('prop_valor_liberado').value = '';
        }
    }

    function formatarCpfExibicao(cpf) {
        const d = normCpf(cpf);
        if (d.length === 11) {
            return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        }
        return cpf || '';
    }

    function cloneTemplate(tplId) {
        const tpl = el(tplId);
        if (!tpl || !tpl.content) return null;
        return tpl.content.firstElementChild.cloneNode(true);
    }

    function bindRemoveRow(row) {
        const btn = row.querySelector('.prop-btn-remove-row');
        if (btn) {
            btn.addEventListener('click', function () {
                row.remove();
            });
        }
    }

    function addEmailRow(valor) {
        const row = cloneTemplate('tpl-prop-email');
        if (!row) return;
        const inp = row.querySelector('.prop-dyn-email');
        if (inp && valor) inp.value = valor;
        bindRemoveRow(row);
        el('prop-lista-emails').appendChild(row);
    }

    function addContatoRow(tipo, valor) {
        const row = cloneTemplate('tpl-prop-contato');
        if (!row) return;
        const sel = row.querySelector('.prop-dyn-contato-tipo');
        const inp = row.querySelector('.prop-dyn-contato-valor');
        if (sel && tipo) sel.value = tipo;
        if (inp && valor) inp.value = valor;
        bindRemoveRow(row);
        el('prop-lista-contatos').appendChild(row);
    }

    function addEnderecoRow(data) {
        const row = cloneTemplate('tpl-prop-endereco');
        if (!row) return;
        const d = data || {};
        const cep = row.querySelector('.prop-dyn-end-cep');
        const log = row.querySelector('.prop-dyn-end-logradouro');
        const princ = row.querySelector('.prop-dyn-end-principal');
        if (cep) cep.value = d.cep || '';
        if (log) log.value = d.logradouro || '';
        if (princ && d.principal) princ.checked = true;
        bindRemoveRow(row);
        el('prop-lista-enderecos').appendChild(row);
    }

    function addRepresentanteRow(data) {
        const row = cloneTemplate('tpl-prop-representante');
        if (!row) return;
        const d = data || {};
        const nome = row.querySelector('.prop-dyn-rep-nome');
        const cpf = row.querySelector('.prop-dyn-rep-cpf');
        if (nome) nome.value = d.nome_representante || '';
        if (cpf) cpf.value = d.cpf_representante || '';
        bindRemoveRow(row);
        el('prop-lista-representantes').appendChild(row);
    }

    function limparListasDinamicas() {
        ['prop-lista-emails', 'prop-lista-contatos', 'prop-lista-enderecos', 'prop-lista-representantes'].forEach(function (id) {
            const c = el(id);
            if (c) c.innerHTML = '';
        });
    }

    function initListasPadrao() {
        limparListasDinamicas();
        addEmailRow('');
        addContatoRow('CELULAR', '');
        addEnderecoRow({ principal: true });
    }

    function preencherBancario(ban) {
        const b = ban || {};
        const map = {
            prop_banco_nome: b.banco,
            prop_agencia: b.agencia,
            prop_dv_agencia: b.dv_agencia,
            prop_conta: b.conta,
            prop_dv_conta: b.dv_conta,
            prop_tipo_conta: b.tipo_conta,
            prop_tipo_pagamento: b.tipo_pagamento,
            prop_bancario_matricula: b.matricula,
            prop_bancario_senha: '',
        };
        Object.keys(map).forEach(function (id) {
            const field = el(id);
            if (field && map[id]) field.value = map[id];
        });
    }

    function preencherDadosPessoais(dados, dadosSiape, nomeFallback) {
        const d = dados || {};
        const siape = dadosSiape || {};
        if (el('prop_cpf')) {
            el('prop_cpf').value = formatarCpfExibicao(d.cpf || siape.cpf || window.__clienteCpfAtual);
        }
        if (el('prop_nome_completo')) {
            el('prop_nome_completo').value = d.nome_completo || siape.nome_completo || nomeFallback || '';
        }
        if (el('prop_data_nascimento')) el('prop_data_nascimento').value = d.data_nascimento || siape.data_nascimento || '';
        if (el('prop_sexo')) el('prop_sexo').value = d.sexo || '';
        if (el('prop_naturalidade')) el('prop_naturalidade').value = d.naturalidade || '';
        if (el('prop_pais_origem')) el('prop_pais_origem').value = d.pais_origem || 'Brasil';
        if (el('prop_numero_rg')) el('prop_numero_rg').value = d.numero_rg || '';
        if (el('prop_orgao_emissor_rg')) el('prop_orgao_emissor_rg').value = d.orgao_emissor_rg || '';
        if (el('prop_uf_emissao_rg')) el('prop_uf_emissao_rg').value = d.uf_emissao_rg || '';
        if (el('prop_data_emissao_rg')) el('prop_data_emissao_rg').value = d.data_emissao_rg || '';
        if (el('prop_nome_pai')) el('prop_nome_pai').value = d.nome_pai || '';
        if (el('prop_nome_mae')) el('prop_nome_mae').value = d.nome_mae || '';

        if (d.id && el('prop_cliente_dados_pessoais_id')) {
            el('prop_cliente_dados_pessoais_id').value = d.id;
            window.__clienteDadosPessoaisId = d.id;
        }
    }

    function preencherContatosDinamicos(contatos) {
        limparListasDinamicas();
        const lista = contatos || [];
        const emails = lista.filter(function (c) {
            return String(c.tipo || '').toUpperCase() === 'EMAIL';
        });
        const fones = lista.filter(function (c) {
            return String(c.tipo || '').toUpperCase() !== 'EMAIL';
        });

        if (emails.length) {
            emails.forEach(function (c) { addEmailRow(c.valor || ''); });
        } else {
            addEmailRow('');
        }

        if (fones.length) {
            fones.forEach(function (c) {
                addContatoRow(c.tipo || 'CELULAR', c.valor || '');
            });
        } else {
            let cel = '';
            if (typeof clienteSelecionado !== 'undefined' && clienteSelecionado && clienteSelecionado.dados_pessoais) {
                cel = clienteSelecionado.dados_pessoais.celular || '';
            }
            addContatoRow('CELULAR', cel);
        }
    }

    function preencherEnderecos(enderecos) {
        const container = el('prop-lista-enderecos');
        if (!container) return;
        container.innerHTML = '';
        const lista = enderecos || [];
        if (lista.length) {
            lista.forEach(function (en) { addEnderecoRow(en); });
        } else {
            addEnderecoRow({ principal: true });
        }
    }

    function preencherRepresentantes(reps) {
        const container = el('prop-lista-representantes');
        if (!container) return;
        container.innerHTML = '';
        const lista = reps || [];
        if (lista.length) {
            lista.forEach(function (r) { addRepresentanteRow(r); });
        }
    }

    window.propWizardCarregarFicha = function (cpf, carteiraId, nomeFallback) {
        const cpfNorm = normCpf(cpf);
        initListasPadrao();
        preencherDadosPessoais({}, {}, nomeFallback);
        if (el('prop_cpf')) el('prop_cpf').value = formatarCpfExibicao(cpfNorm);

        if (typeof matriculaSelecionada !== 'undefined' && matriculaSelecionada && el('prop_bancario_matricula')) {
            el('prop_bancario_matricula').value = matriculaSelecionada.matricula || '';
        }

        const url = '/contratos/api/v2/cliente-dados-pessoais/lookup/?cpf=' +
            encodeURIComponent(cpfNorm) +
            '&carteira_id=' + encodeURIComponent(carteiraId || '');

        return fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.ok) return;
                const siape = data.dados_siape || {};
                if (data.encontrado && data.dados) {
                    preencherDadosPessoais(data.dados, siape, nomeFallback);
                    preencherContatosDinamicos(data.dados.contatos_dinamicos);
                    preencherEnderecos(data.dados.enderecos_dinamicos);
                    preencherRepresentantes(data.dados.representantes_dinamicos);
                    if (data.dados.bancario) preencherBancario(data.dados.bancario);
                } else {
                    preencherDadosPessoais({}, siape, nomeFallback);
                    preencherContatosDinamicos(
                        (data.dados && data.dados.contatos_dinamicos) ? data.dados.contatos_dinamicos : []
                    );
                    preencherEnderecos([]);
                    preencherRepresentantes([]);
                }
            })
            .catch(function () {
                preencherDadosPessoais({}, {}, nomeFallback);
            });
    };

    function atualizarUiPasso() {
        for (let i = 1; i <= 3; i++) {
            const painel = el('prop-wizard-passo-' + i);
            if (painel) painel.classList.toggle('d-none', i !== passoAtual);
        }
        const badge = el('prop-wizard-passo-label');
        if (badge) badge.textContent = 'Passo ' + passoAtual + ' de 3';

        const btnVoltar = el('prop-wizard-btn-voltar');
        const btnProximo = el('prop-wizard-btn-proximo');
        const btnEnviar = el('prop_btn_enviar');
        const btnCancelar = el('prop-wizard-btn-cancelar');

        if (btnVoltar) btnVoltar.classList.toggle('d-none', passoAtual === 1);
        if (btnProximo) btnProximo.classList.toggle('d-none', passoAtual === 3);
        if (btnEnviar) btnEnviar.classList.toggle('d-none', passoAtual !== 3);
        if (btnCancelar) btnCancelar.classList.toggle('d-none', passoAtual > 1);
    }

    window.propWizardReset = function () {
        passoAtual = 1;
        arquivosSelecionados = null;
        atualizarUiPasso();
        initListasPadrao();
        if (el('prop_cliente_dados_pessoais_id')) el('prop_cliente_dados_pessoais_id').value = '';
        if (el('prop_arquivos')) el('prop_arquivos').value = '';
        if (el('prop-lista-arquivos-preview')) el('prop-lista-arquivos-preview').innerHTML = '';
        if (el('prop_observacao')) el('prop_observacao').value = '';
        ['prop_valor_af', 'prop_valor_tc', 'prop_valor_parcela', 'prop_coeficiente', 'prop_valor_liberado', 'prop_prazo'].forEach(function (id) {
            const f = el(id);
            if (f) f.value = '';
        });
        return Promise.resolve();
    };

    function validarEmail(val) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(val || '').trim());
    }

    function coletarEmails() {
        const emails = [];
        document.querySelectorAll('#prop-lista-emails .prop-dyn-email').forEach(function (inp) {
            const v = (inp.value || '').trim();
            if (v) emails.push(v);
        });
        return emails;
    }

    function coletarContatosDinamicos() {
        const contatos = [];
        coletarEmails().forEach(function (email) {
            contatos.push({ tipo: 'EMAIL', valor: email });
        });
        document.querySelectorAll('#prop-lista-contatos .prop-dyn-row').forEach(function (row) {
            const tipo = (row.querySelector('.prop-dyn-contato-tipo') || {}).value || 'CELULAR';
            const valor = (row.querySelector('.prop-dyn-contato-valor') || {}).value || '';
            if (String(valor).trim()) {
                contatos.push({ tipo: tipo, valor: String(valor).trim() });
            }
        });
        return contatos;
    }

    function montarPayloadSalvar() {
        const cpf = normCpf(el('prop_cpf') && el('prop_cpf').value);
        return {
            cpf: cpf,
            nome_completo: (el('prop_nome_completo') && el('prop_nome_completo').value || '').trim(),
            sexo: el('prop_sexo') ? el('prop_sexo').value : '',
            data_nascimento: el('prop_data_nascimento') ? el('prop_data_nascimento').value : '',
            naturalidade: el('prop_naturalidade') ? el('prop_naturalidade').value : '',
            pais_origem: el('prop_pais_origem') ? el('prop_pais_origem').value : '',
            numero_rg: el('prop_numero_rg') ? el('prop_numero_rg').value : '',
            orgao_emissor_rg: el('prop_orgao_emissor_rg') ? el('prop_orgao_emissor_rg').value : '',
            uf_emissao_rg: el('prop_uf_emissao_rg') ? el('prop_uf_emissao_rg').value : '',
            data_emissao_rg: el('prop_data_emissao_rg') ? el('prop_data_emissao_rg').value : '',
            nome_pai: el('prop_nome_pai') ? el('prop_nome_pai').value : '',
            nome_mae: el('prop_nome_mae') ? el('prop_nome_mae').value : '',
            contatos_dinamicos: coletarContatosDinamicos(),
            enderecos_dinamicos: [],
            representantes_dinamicos: [],
            bancario: {
                banco: el('prop_banco_nome') ? el('prop_banco_nome').value : '',
                agencia: el('prop_agencia') ? el('prop_agencia').value : '',
                dv_agencia: el('prop_dv_agencia') ? el('prop_dv_agencia').value : '',
                conta: el('prop_conta') ? el('prop_conta').value : '',
                dv_conta: el('prop_dv_conta') ? el('prop_dv_conta').value : '',
                tipo_conta: el('prop_tipo_conta') ? el('prop_tipo_conta').value : '',
                tipo_pagamento: el('prop_tipo_pagamento') ? el('prop_tipo_pagamento').value : '',
                matricula: el('prop_bancario_matricula') ? el('prop_bancario_matricula').value : '',
                senha: el('prop_bancario_senha') ? el('prop_bancario_senha').value : '',
            },
        };
    }

    function coletarEnderecos() {
        const enderecos = [];
        document.querySelectorAll('#prop-lista-enderecos .prop-dyn-row').forEach(function (row) {
            const cep = (row.querySelector('.prop-dyn-end-cep') || {}).value || '';
            const log = (row.querySelector('.prop-dyn-end-logradouro') || {}).value || '';
            const princ = (row.querySelector('.prop-dyn-end-principal') || {}).checked;
            if (String(cep).trim() || String(log).trim()) {
                enderecos.push({
                    cep: String(cep).trim(),
                    logradouro: String(log).trim(),
                    principal: princ,
                });
            }
        });
        return enderecos;
    }

    function coletarRepresentantes() {
        const reps = [];
        document.querySelectorAll('#prop-lista-representantes .prop-dyn-row').forEach(function (row) {
            const nome = (row.querySelector('.prop-dyn-rep-nome') || {}).value || '';
            const cpf = (row.querySelector('.prop-dyn-rep-cpf') || {}).value || '';
            if (String(nome).trim() || String(cpf).trim()) {
                reps.push({
                    nome_representante: String(nome).trim(),
                    cpf_representante: normCpf(cpf),
                });
            }
        });
        return reps;
    }

    function validarPasso1() {
        const nome = (el('prop_nome_completo') && el('prop_nome_completo').value || '').trim();
        if (!nome) {
            alert('Informe o nome completo.');
            return false;
        }
        const cpf = normCpf(el('prop_cpf') && el('prop_cpf').value);
        if (cpf.length !== 11) {
            alert('CPF inválido.');
            return false;
        }
        const emails = coletarEmails();
        if (!emails.length) {
            alert('Informe ao menos um e-mail válido.');
            return false;
        }
        for (let i = 0; i < emails.length; i++) {
            if (!validarEmail(emails[i])) {
                alert('E-mail inválido: ' + emails[i]);
                return false;
            }
        }
        const ban = montarPayloadSalvar().bancario;
        if (!(ban.banco || '').trim() || !(ban.agencia || '').trim() || !(ban.conta || '').trim()) {
            alert('Preencha banco, agência e conta (dados bancários).');
            return false;
        }
        if (!(ban.tipo_conta || '').trim() || !(ban.tipo_pagamento || '').trim()) {
            alert('Selecione tipo de conta e tipo de pagamento.');
            return false;
        }
        return true;
    }

    function salvarPasso1() {
        const payload = montarPayloadSalvar();
        payload.enderecos_dinamicos = coletarEnderecos();
        payload.representantes_dinamicos = coletarRepresentantes();

        return fetch('/contratos/api/v2/cliente-dados-pessoais/salvar/', {
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
                    alert(res.message || res.erro || 'Erro ao salvar ficha do cliente.');
                    return false;
                }
                const id = res.cliente_id;
                if (el('prop_cliente_dados_pessoais_id')) el('prop_cliente_dados_pessoais_id').value = id;
                window.__clienteDadosPessoaisId = id;
                return true;
            });
    }

    function validarPasso3() {
        const banco = el('prop_banco_id') && el('prop_banco_id').value;
        const conv = el('prop_convenio_id') && el('prop_convenio_id').value;
        const prod = el('prop_produto_id') && el('prop_produto_id').value;
        if (!banco || !conv || !prod) {
            alert('Selecione banco, convênio e produto.');
            return false;
        }
        const tcmEl = el('prop_tabela_cms_id');
        const tcm = tcmEl && tcmEl.value;
        if (tcmEl && tcmEl.disabled) {
            alert(
                'Nenhuma tabela CMS disponível para a combinação selecionada. ' +
                'Cadastre uma tabela antes de enviar a proposta.'
            );
            return false;
        }
        if (!tcm) {
            alert('Selecione a Tabela CMS.');
            return false;
        }
        return true;
    }

    function atualizarPreviewArquivos() {
        const ul = el('prop-lista-arquivos-preview');
        const input = el('prop_arquivos');
        if (!ul) return;
        ul.innerHTML = '';
        const files = arquivosSelecionados || (input && input.files);
        if (!files || !files.length) return;
        for (let i = 0; i < files.length; i++) {
            const f = files[i];
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = f.name + ' (' + Math.round(f.size / 1024) + ' KB)';
            ul.appendChild(li);
        }
    }

    function enviarPropostas() {
        if (!validarPasso3()) return;

        const dpId = el('prop_cliente_dados_pessoais_id') && el('prop_cliente_dados_pessoais_id').value;
        const carteiraId = el('prop_carteira_id') && el('prop_carteira_id').value;
        if (!dpId || !carteiraId) {
            alert('Dados incompletos. Volte ao passo 1.');
            return;
        }

        const proposta = {
            banco_id: el('prop_banco_id').value,
            convenio_id: el('prop_convenio_id').value,
            produto_id: el('prop_produto_id').value,
            valor_af: el('prop_valor_af').value,
            valor_tc: el('prop_valor_tc').value,
            valor_parcela: el('prop_valor_parcela').value,
            coeficiente: el('prop_coeficiente').value,
            valor_liberado: el('prop_valor_liberado').value,
            prazo: el('prop_prazo').value,
            tabela_cms_id: el('prop_tabela_cms_id').value || null,
        };

        const fd = new FormData();
        fd.append('carteira_id', carteiraId);
        fd.append('cliente_dados_pessoais_id', dpId);
        fd.append('observacao', (el('prop_observacao') && el('prop_observacao').value) || '');
        fd.append('propostas', JSON.stringify([proposta]));

        const files = arquivosSelecionados || (el('prop_arquivos') && el('prop_arquivos').files);
        if (files) {
            for (let i = 0; i < files.length; i++) {
                fd.append('arquivos', files[i]);
            }
        }

        const btn = el('prop_btn_enviar');
        if (btn) btn.disabled = true;

        fetch('/contratos/api/v2/solicitar-propostas/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: fd,
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (res.ok) {
                    alert(res.message || 'Propostas enviadas.');
                    window.__statusComercialAtual = 'OPERACIONAL';
                    if (typeof window.consultaOperacionalAtualizarStatus === 'function') {
                        window.consultaOperacionalAtualizarStatus('OPERACIONAL');
                    }
                    if (typeof window.carregarContainerNovoContrato === 'function' && window.__carteiraIdAtual) {
                        window.carregarContainerNovoContrato(window.__carteiraIdAtual);
                    }
                    const m = el('modalEnviarPropostas');
                    if (m && typeof bootstrap !== 'undefined') {
                        bootstrap.Modal.getInstance(m)?.hide();
                    }
                } else {
                    alert(res.message || res.erro || 'Erro ao enviar propostas.');
                }
            })
            .catch(function () {
                alert('Erro de comunicação ao enviar propostas.');
            })
            .finally(function () {
                if (btn) btn.disabled = false;
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.prop-btn-add-row').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const tipo = btn.getAttribute('data-add');
                if (tipo === 'email') addEmailRow('');
                else if (tipo === 'contato') addContatoRow('CELULAR', '');
                else if (tipo === 'endereco') addEnderecoRow({});
                else if (tipo === 'representante') addRepresentanteRow({});
            });
        });

        const btnProximo = el('prop-wizard-btn-proximo');
        if (btnProximo) {
            btnProximo.addEventListener('click', function () {
                if (passoAtual === 1) {
                    if (!validarPasso1()) return;
                    btnProximo.disabled = true;
                    salvarPasso1().then(function (ok) {
                        btnProximo.disabled = false;
                        if (!ok) return;
                        passoAtual = 2;
                        atualizarUiPasso();
                    });
                } else if (passoAtual === 2) {
                    const input = el('prop_arquivos');
                    arquivosSelecionados = input && input.files && input.files.length ? input.files : null;
                    atualizarPreviewArquivos();
                    passoAtual = 3;
                    atualizarUiPasso();
                }
            });
        }

        const btnVoltar = el('prop-wizard-btn-voltar');
        if (btnVoltar) {
            btnVoltar.addEventListener('click', function () {
                if (passoAtual > 1) {
                    passoAtual -= 1;
                    atualizarUiPasso();
                }
            });
        }

        const inputArq = el('prop_arquivos');
        if (inputArq) {
            inputArq.addEventListener('change', function () {
                arquivosSelecionados = inputArq.files && inputArq.files.length ? inputArq.files : null;
                atualizarPreviewArquivos();
            });
        }

        const btnEnviar = el('prop_btn_enviar');
        if (btnEnviar) {
            btnEnviar.addEventListener('click', enviarPropostas);
        }

        var mapCalc = {
            prop_valor_parcela: 'parcela',
            prop_coeficiente: 'coeficiente',
            prop_valor_af: 'af',
            prop_valor_tc: 'tc',
        };
        Object.keys(mapCalc).forEach(function (id) {
            var inp = el(id);
            if (inp) {
                inp.addEventListener('input', function () {
                    recalcularFinanceiroProposta(mapCalc[id]);
                });
            }
        });

        const modal = el('modalEnviarPropostas');
        if (modal) {
            modal.addEventListener('hidden.bs.modal', function () {
                if (typeof window.propWizardReset === 'function') {
                    window.propWizardReset();
                }
            });
        }
    });
})();
