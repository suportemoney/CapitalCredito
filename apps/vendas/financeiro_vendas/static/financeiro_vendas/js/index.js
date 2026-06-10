let statusAtual = 'A_PAGAR';

function filtroDatasDisponivel() {
    return $('#filtroDataInicio').length > 0 && $('#filtroDataFim').length > 0;
}

function inicializarFiltroDatasMesAtual() {
    if (!filtroDatasDisponivel()) {
        return;
    }
    const hoje = new Date();
    const primeiroDiaMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    const ultimoDiaMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
    $('#filtroDataInicio').val(primeiroDiaMes.toISOString().split('T')[0]);
    $('#filtroDataFim').val(ultimoDiaMes.toISOString().split('T')[0]);
}

function getFiltroDatas() {
    if (!filtroDatasDisponivel()) {
        return null;
    }

    const dataInicio = $('#filtroDataInicio').val();
    const dataFim = $('#filtroDataFim').val();

    if (!dataInicio) {
        alert('Data início é obrigatória');
        return null;
    }
    if (!dataFim) {
        alert('Data fim é obrigatória');
        return null;
    }
    if (dataFim < dataInicio) {
        alert('Data fim não pode ser anterior à data início');
        return null;
    }

    return { data_inicio: dataInicio, data_fim: dataFim };
}

function aplicarFiltros() {
    const filtros = getFiltroDatas();
    if (filtroDatasDisponivel() && !filtros) {
        return;
    }
    if (filtros) {
        carregarResumo();
    }
    carregarTabela(statusAtual);
}

function carregarResumo() {
    const filtros = getFiltroDatas();
    if (!filtros) {
        return;
    }

    $.ajax({
        url: '/vendas/financeiro/api/contratos/resumo/',
        method: 'GET',
        data: filtros,
        success: function(response) {
            if (response.success) {
                $('#resumo-total-af').text(formatarMoeda(response.data.total_af));
                $('#resumo-total-repasse').text(formatarMoeda(response.data.total_repasse));
                $('#resumo-total-contratos').text(response.data.total_contratos);
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao carregar resumo: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

$(document).ready(function() {
    inicializarFiltroDatasMesAtual();
    aplicarFiltros();
    
    $('#novo-status').on('change', function() {
        if ($(this).val() === 'PAGO') {
            $('#novo-data-pagamento').prop('required', true);
        } else {
            $('#novo-data-pagamento').prop('required', false);
        }
    });
    
    const hoje = new Date().toISOString().split('T')[0];
    $('#novo-data-contrato').val(hoje);

    $('#novo-valor-repasse').on('input blur', function() {
        if (!$('#novo-valor-tc').val()) {
            $('#novo-valor-tc').val($(this).val());
        }
    });
    $('#novo-valor-comprovante, #comp-valor').on('input', function() {
        const fmt = formatarValorComprovanteDigitos($(this).val());
        if (fmt !== $(this).val()) {
            $(this).val(fmt);
        }
    });
});

function carregarTabela(status) {
    statusAtual = status;

    const filtros = getFiltroDatas();
    if (filtroDatasDisponivel() && !filtros) {
        return;
    }

    const params = { status: status };
    if (filtros) {
        params.data_inicio = filtros.data_inicio;
        params.data_fim = filtros.data_fim;
    }
    
    $.ajax({
        url: '/vendas/financeiro/api/contratos/listar/',
        method: 'GET',
        data: params,
        success: function(response) {
            if (response.success) {
                exibirTabela(status, response.data);
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao carregar contratos: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function exibirTabela(status, contratos) {
    let tbodyId = '';
    let colunas = [];
    
    if (status === 'A_PAGAR') {
        tbodyId = 'tabela-a-pagar';
        colunas = ['funcionario', 'cliente', 'cpf', 'produto', 'banco', 'af', 'repasse', 'tc', 'tc_pago', 'ponta', 'classificador', 'comprovante', 'acoes'];
    } else if (status === 'PAGO') {
        tbodyId = 'tabela-pago';
        colunas = ['funcionario', 'cliente', 'cpf', 'produto', 'banco', 'af', 'repasse', 'tc', 'tc_pago', 'ponta', 'classificador', 'data_pagamento', 'comprovante', 'acoes'];
    } else if (status === 'NAO_PAGO') {
        tbodyId = 'tabela-nao-pago';
        colunas = ['funcionario', 'cliente', 'cpf', 'produto', 'banco', 'af', 'repasse', 'tc', 'tc_pago', 'ponta', 'classificador', 'comprovante', 'acoes'];
    }
    
    const tbody = $(`#${tbodyId}`);
    tbody.empty();
    
    if (contratos.length === 0) {
        const colspan = colunas.length;
        tbody.append(`<tr><td colspan="${colspan}" class="text-center">Nenhum contrato encontrado</td></tr>`);
        return;
    }
    
    contratos.forEach(function(contrato) {
        const row = gerarLinhaTabela(contrato, status);
        tbody.append(row);
    });
}

function gerarLinhaTabela(contrato, status) {
    const cpfFormatado = formatarCPF(contrato.cliente_cpf);
    const afFormatado = formatarMoeda(contrato.valor_af);
    const repasseFormatado = formatarMoeda(contrato.valor_repasse);
    const pontaChecked = contrato.flg_ponta ? 'checked' : '';
    
    let html = '<tr>';
    html += `<td>${escapeHtml(contrato.funcionario)}</td>`;
    html += `<td>${escapeHtml(contrato.cliente_nome)}</td>`;
    html += `<td>${cpfFormatado}</td>`;
    html += `<td>
        <select class="form-select form-select-sm campo-editavel" data-contrato-id="${contrato.id}" data-campo="produto_id" onchange="editarCampo(${contrato.id}, 'produto_id', this.value)">
            ${gerarOpcoesProdutos(contrato.produto_id)}
        </select>
    </td>`;
    html += `<td>
        <input type="text" class="form-control form-control-sm campo-editavel" value="${escapeHtml(contrato.banco)}" 
               data-contrato-id="${contrato.id}" data-campo="banco" 
               onblur="editarCampo(${contrato.id}, 'banco', this.value)">
    </td>`;
    html += `<td>
        <input type="number" class="form-control form-control-sm campo-editavel" value="${contrato.valor_af}" step="0.01" 
               data-contrato-id="${contrato.id}" data-campo="valor_af" 
               onblur="editarCampo(${contrato.id}, 'valor_af', this.value)">
        <small class="text-muted">${afFormatado}</small>
    </td>`;
    html += `<td>
        <input type="number" class="form-control form-control-sm campo-editavel" value="${contrato.valor_repasse}" step="0.01" 
               data-contrato-id="${contrato.id}" data-campo="valor_repasse" 
               onblur="editarCampo(${contrato.id}, 'valor_repasse', this.value)">
        <small class="text-muted">${repasseFormatado}</small>
    </td>`;
    html += `<td>
        <input type="number" class="form-control form-control-sm campo-editavel" value="${contrato.valor_tc || 0}" step="0.01" min="0"
               data-contrato-id="${contrato.id}" data-campo="valor_tc"
               onblur="editarCampo(${contrato.id}, 'valor_tc', this.value)">
    </td>`;
    html += `<td>
        <span class="badge ${badgeTcClasse(contrato)}">${formatarMoeda(contrato.valor_tc_acumulado || 0)} / ${formatarMoeda(contrato.valor_tc || 0)}</span>
    </td>`;
    html += `<td>
        <input type="checkbox" class="form-check-input campo-editavel" ${pontaChecked} 
               data-contrato-id="${contrato.id}" data-campo="flg_ponta" 
               onchange="editarCampo(${contrato.id}, 'flg_ponta', this.checked)">
    </td>`;
    html += `<td>
        <select class="form-select form-select-sm campo-editavel" data-contrato-id="${contrato.id}" data-campo="classificador_id" 
                onchange="editarCampo(${contrato.id}, 'classificador_id', this.value)">
            ${gerarOpcoesClassificadores(contrato.classificador_id)}
        </select>
    </td>`;
    
    if (status === 'PAGO') {
        html += `<td>${contrato.data_pagamento ? formatarData(contrato.data_pagamento) : '-'}</td>`;
    }

    const qtdComp = contrato.qtd_comprovantes || 0;
    html += `<td>
        <button type="button" class="btn btn-sm btn-outline-primary" onclick="abrirModalComprovantes(${contrato.id}, ${contrato.contrato_execucao_id || 'null'})" title="Comprovantes TC">
            <i class='bx bx-receipt'></i> ${qtdComp > 0 ? qtdComp : '+'}
        </button>
    </td>`;
    
    html += `<td>
        <button type="button" class="btn btn-sm btn-danger" onclick="inativarContrato(${contrato.id})" title="Inativar">
            <i class='bx bx-trash'></i>
        </button>
    </td>`;
    html += '</tr>';
    
    return html;
}

function gerarOpcoesProdutos(produtoIdSelecionado) {
    let html = '<option value="">Selecione...</option>';
    const produtos = window.produtos || [];
    
    if (produtos.length === 0) {
        console.warn('Nenhum produto disponível em window.produtos');
        return html;
    }
    
    const produtoIdSelecionadoNum = parseInt(produtoIdSelecionado);
    
    produtos.forEach(function(produto) {
        const produtoIdNum = parseInt(produto.id);
        const selected = produtoIdNum === produtoIdSelecionadoNum ? 'selected' : '';
        html += `<option value="${produto.id}" ${selected}>${escapeHtml(produto.nome)}</option>`;
    });
    return html;
}

function gerarOpcoesClassificadores(classificadorIdSelecionado) {
    let html = '<option value="">Selecione...</option>';
    const classificadores = window.classificadores || [];
    
    if (classificadores.length === 0) {
        console.warn('Nenhum classificador disponível em window.classificadores');
        return html;
    }
    
    const classificadorIdSelecionadoNum = parseInt(classificadorIdSelecionado);
    
    classificadores.forEach(function(classificador) {
        const classificadorIdNum = parseInt(classificador.id);
        const selected = classificadorIdNum === classificadorIdSelecionadoNum ? 'selected' : '';
        const percentual = parseFloat(classificador.percentual).toFixed(2);
        html += `<option value="${classificador.id}" ${selected}>${escapeHtml(classificador.titulo)} (${percentual}%)</option>`;
    });
    return html;
}

function abrirModalNovoContrato() {
    const modalElement = document.getElementById('modalNovoContrato');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
    
    limparFormNovoContrato();
}

function limparFormNovoContrato() {
    $('#formNovoContrato')[0].reset();
    const hoje = new Date().toISOString().split('T')[0];
    $('#novo-data-contrato').val(hoje);
    $('#novo-status').val('A_PAGAR');
    $('#novo-data-pagamento').prop('required', false);
    $('#novo-valor-comprovante').val('');
    $('#novo-arquivo-comprovante').val('');
}

function badgeTcClasse(contrato) {
    const acum = parseFloat(contrato.valor_tc_acumulado || 0);
    const meta = parseFloat(contrato.valor_tc || 0);
    if (meta > 0 && acum >= meta) return 'bg-success';
    if (acum > 0) return 'bg-warning text-dark';
    return 'bg-secondary';
}

function parseValorComprovanteCampo(raw) {
    const d = String(raw || '').replace(/\D/g, '');
    if (!d) return 0;
    return parseInt(d, 10) / 100;
}

function formatarValorComprovanteDigitos(digitsRaw) {
    const d = String(digitsRaw || '').replace(/\D/g, '');
    if (!d) return '';
    let cent = parseInt(d, 10);
    if (!isFinite(cent) || cent < 0) return '';
    const reais = cent / 100;
    return reais.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function carregarSetorFuncionario(userId) {
    if (!userId) {
        $('#novo-setor').val('');
        return;
    }
    
    $.ajax({
        url: `/vendas/financeiro/api/funcionario/get-setor/${userId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success && response.data.setor_id) {
                $('#novo-setor').val(response.data.setor_id);
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar setor:', xhr);
        }
    });
}

function buscarClientePorCPF() {
    const cpf = $('#novo-cpf').val().trim();
    
    if (!cpf) {
        alert('Digite um CPF');
        return;
    }
    
    $.ajax({
        url: '/vendas/financeiro/api/cliente/buscar-cpf/',
        method: 'GET',
        data: { cpf: cpf },
        success: function(response) {
            if (response.success) {
                $('#novo-cliente-nome').val(response.data.nome);
                $('#novo-cpf').val(formatarCPF(response.data.cpf));
            } else {
                alert('Cliente não encontrado. Você pode preencher o nome manualmente.');
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao buscar cliente: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function salvarNovoContrato() {
    const valorTc = $('#novo-valor-tc').val() || $('#novo-valor-repasse').val();
    const arquivoComp = document.getElementById('novo-arquivo-comprovante');
    const valorCompRaw = $('#novo-valor-comprovante').val();
    const valorComp = parseValorComprovanteCampo(valorCompRaw);

    const formData = new FormData();
    formData.append('user_id', $('#novo-user').val());
    formData.append('setor_id', $('#novo-setor').val());
    formData.append('cliente_cpf', $('#novo-cpf').val());
    formData.append('cliente_nome', $('#novo-cliente-nome').val());
    formData.append('produto_id', $('#novo-produto').val());
    formData.append('banco', $('#novo-banco').val());
    formData.append('valor_af', $('#novo-valor-af').val());
    formData.append('valor_repasse', $('#novo-valor-repasse').val());
    formData.append('valor_tc', valorTc);
    formData.append('flg_ponta', $('#novo-flg-ponta').is(':checked') ? 'true' : 'false');
    formData.append('classificador_id', $('#novo-classificador').val());
    formData.append('data_contrato', $('#novo-data-contrato').val());
    formData.append('status', $('#novo-status').val());
    formData.append('data_pagamento', $('#novo-data-pagamento').val() || '');
    formData.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());

    if (arquivoComp && arquivoComp.files && arquivoComp.files[0]) {
        if (!valorComp || valorComp <= 0) {
            alert('Informe o valor do comprovante');
            return;
        }
        formData.append('arquivo_comprovante', arquivoComp.files[0]);
        formData.append('valor_comprovante', valorComp);
    }

    if (!$('#novo-user').val() || !$('#novo-setor').val() || !$('#novo-cpf').val() || !$('#novo-cliente-nome').val() ||
        !$('#novo-produto').val() || !$('#novo-banco').val() || !$('#novo-valor-af').val() || !$('#novo-valor-repasse').val() ||
        !valorTc || !$('#novo-classificador').val() || !$('#novo-data-contrato').val() || !$('#novo-status').val()) {
        alert('Preencha todos os campos obrigatórios');
        return;
    }
    
    $.ajax({
        url: '/vendas/financeiro/api/contratos/criar/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                const modalElement = document.getElementById('modalNovoContrato');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
                aplicarFiltros();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao criar contrato: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function editarCampo(contratoId, campo, valor) {
    let valorEnviar = valor;
    if (campo === 'flg_ponta' && typeof valor === 'boolean') {
        valorEnviar = valor ? 'true' : 'false';
    }
    
    $.ajax({
        url: `/vendas/financeiro/api/contratos/editar-campo/${contratoId}/`,
        method: 'POST',
        data: {
            campo: campo,
            valor: valorEnviar,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                aplicarFiltros();
            } else {
                alert('Erro: ' + response.message);
                aplicarFiltros();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao editar campo: ' + (response.message || 'Erro desconhecido'));
            aplicarFiltros();
        }
    });
}

function inativarContrato(contratoId) {
    if (!confirm('Tem certeza que deseja inativar este contrato?')) {
        return;
    }
    
    $.ajax({
        url: `/vendas/financeiro/api/contratos/inativar/${contratoId}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                aplicarFiltros();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao inativar contrato: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function formatarCPF(cpf) {
    if (!cpf) return '-';
    cpf = cpf.replace(/\D/g, '');
    if (cpf.length === 11) {
        return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }
    return cpf;
}

function formatarMoeda(valor) {
    if (!valor || valor === 0) return 'R$ 0,00';
    return 'R$ ' + parseFloat(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatarData(data) {
    if (!data) return '-';
    const partes = data.split('-');
    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    return data;
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

let _compContratoExecucaoId = null;

function abrirModalComprovantes(contratoId, contratoExecucaoId) {
    _compContratoExecucaoId = contratoExecucaoId;
    $('#comp-contrato-id').val(contratoId);
    $('#comp-valor').val('');
    $('#comp-arquivo').val('');

    const modalElement = document.getElementById('modalComprovantesTc');
    if (modalElement && typeof bootstrap !== 'undefined') {
        bootstrap.Modal.getOrCreateInstance(modalElement).show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }

    const ehV2 = contratoExecucaoId && contratoExecucaoId !== 'null';
    if (ehV2) {
        $('#comp-alerta-v2').removeClass('d-none');
        $('#comp-form-upload').addClass('d-none');
    } else {
        $('#comp-alerta-v2').addClass('d-none');
        $('#comp-form-upload').removeClass('d-none');
    }

    carregarComprovantesTc(contratoId);
}

function carregarComprovantesTc(contratoId) {
    $.ajax({
        url: '/vendas/financeiro/api/comprovantes-tc/',
        method: 'GET',
        data: { contrato_pagamento_id: contratoId },
        success: function(response) {
            if (!response.success) {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
                return;
            }
            renderizarListaComprovantes(response.data);
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao carregar comprovantes: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function renderizarListaComprovantes(data) {
    const tbody = $('#comp-tabela-lista');
    tbody.empty();
    const acumulado = data.soma !== undefined ? data.soma : data.valor_tc_acumulado;
    $('#comp-resumo-tc').text(
        formatarMoeda(acumulado) + ' / ' + formatarMoeda(data.valor_tc)
    );

    const lista = data.comprovantes || [];
    if (!lista.length) {
        tbody.append('<tr><td colspan="5" class="text-center text-muted">Nenhum comprovante registrado</td></tr>');
        return;
    }

    lista.forEach(function(c) {
        const dataFmt = c.criado_em ? formatarDataHoraIso(c.criado_em) : '-';
        const link = c.arquivo_url
            ? `<a href="${escapeHtml(c.arquivo_url)}" target="_blank" rel="noopener">Abrir</a>`
            : '-';
        const btnExcluir = _compContratoExecucaoId
            ? ''
            : `<button type="button" class="btn btn-sm btn-outline-danger" onclick="excluirComprovanteTc(${c.id})" title="Excluir"><i class='bx bx-trash'></i></button>`;
        tbody.append(
            '<tr>' +
            `<td>${formatarMoeda(c.valor)}</td>` +
            `<td>${link}</td>` +
            `<td>${escapeHtml(c.criado_por)}</td>` +
            `<td>${dataFmt}</td>` +
            `<td>${btnExcluir}</td>` +
            '</tr>'
        );
    });
}

function enviarComprovanteTc() {
    const contratoId = $('#comp-contrato-id').val();
    const valor = parseValorComprovanteCampo($('#comp-valor').val());
    const arquivoInput = document.getElementById('comp-arquivo');

    if (!contratoId) {
        alert('Contrato não identificado');
        return;
    }
    if (!valor || valor <= 0) {
        alert('Informe o valor do comprovante');
        return;
    }
    if (!arquivoInput || !arquivoInput.files || !arquivoInput.files[0]) {
        alert('Anexe o arquivo do comprovante');
        return;
    }

    const fd = new FormData();
    fd.append('contrato_pagamento_id', contratoId);
    fd.append('valor', valor);
    fd.append('arquivo', arquivoInput.files[0]);
    fd.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());

    $.ajax({
        url: '/vendas/financeiro/api/comprovante-tc/',
        method: 'POST',
        data: fd,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                $('#comp-valor').val('');
                $('#comp-arquivo').val('');
                carregarComprovantesTc(contratoId);
                aplicarFiltros();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao enviar comprovante: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function excluirComprovanteTc(comprovanteId) {
    const contratoId = $('#comp-contrato-id').val();
    if (!confirm('Excluir este comprovante TC?')) return;

    $.ajax({
        url: '/vendas/financeiro/api/comprovante-tc/excluir/',
        method: 'POST',
        data: {
            contrato_pagamento_id: contratoId,
            comprovante_id: comprovanteId,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                carregarComprovantesTc(contratoId);
                aplicarFiltros();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao excluir comprovante: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function formatarDataHoraIso(iso) {
    if (!iso) return '-';
    try {
        const d = new Date(iso);
        return d.toLocaleString('pt-BR');
    } catch (e) {
        return iso;
    }
}

