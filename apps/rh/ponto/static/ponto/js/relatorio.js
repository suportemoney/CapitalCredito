let dadosRelatorio = null;
let dadosAjustePendente = null;

$(document).ready(function() {
    const hoje = new Date();
    const primeiroDiaMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    const ultimoDiaMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
    $('#filtroDataInicio').val(primeiroDiaMes.toISOString().split('T')[0]);
    $('#filtroDataFim').val(ultimoDiaMes.toISOString().split('T')[0]);
});

function gerarRelatorio() {
    const dataInicio = $('#filtroDataInicio').val();
    const dataFim = $('#filtroDataFim').val();
    const funcionarioId = $('#filtroFuncionario').val();
    if (!dataInicio) {
        mostrarMensagem('error', 'Data início é obrigatória');
        return;
    }
    if (!dataFim) {
        mostrarMensagem('error', 'Data fim é obrigatória');
        return;
    }
    const params = {
        data_inicio: dataInicio,
        data_fim: dataFim
    };
    if (funcionarioId) {
        params.funcionario_id = funcionarioId;
    }
    $.ajax({
        url: '/rh/ponto/api/relatorio/presenca/',
        method: 'GET',
        data: params,
        success: function(response) {
            if (response.success) {
                dadosRelatorio = response.data;
                exibirRelatorio(response.data);
                $('#areaRelatorio').show();
                $('#mensagemVazio').hide();
                $('#btnImprimir').show();
            } else {
                mostrarMensagem('error', response.message);
            }
        },
        error: function(xhr) {
            let mensagem = 'Erro ao gerar relatório';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                mensagem = xhr.responseJSON.message;
            }
            mostrarMensagem('error', mensagem);
        }
    });
}

function exibirRelatorio(dados) {
    const tbody = $('#tbodyRelatorio');
    const thead = $('#theadRelatorio');
    const dadosFuncDiv = $('#dadosFuncionarioRelatorio');
    tbody.empty();
    dadosFuncDiv.hide().empty();
    if (dados && dados.length > 0) {
        const funcionarioId = $('#filtroFuncionario').val();
        const funcionariosUnicos = [...new Set(dados.map(item => item.funcionario_id))];
        const isApenasUmFuncionario = (funcionarioId && funcionarioId !== '') || funcionariosUnicos.length === 1;
        const podeEditar = (typeof IS_SUPERUSER !== 'undefined' && IS_SUPERUSER === true) && isApenasUmFuncionario;
        if (isApenasUmFuncionario) {
            const primeiro = dados[0];
            dadosFuncDiv.html(`<strong>Funcionário:</strong> ${primeiro.funcionario_nome} | <strong>CPF:</strong> ${primeiro.funcionario_cpf || '-'} | <strong>Chave PIX:</strong> ${primeiro.chave_pix || '-'}`).show();
            thead.html('<th>Data</th><th>Entrada 1</th><th>Saída 1</th><th>Entrada 2</th><th>Saída 2</th><th>Horário Total</th><th>Horário Faltando</th>');
        } else {
            thead.html('<th>Data</th><th>Funcionário</th><th>Entrada 1</th><th>Saída 1</th><th>Entrada 2</th><th>Saída 2</th><th>Horário Total</th><th>Horário Faltando</th>');
        }
        dados.forEach(function(item) {
            const entrada1 = (item.entrada1 && item.entrada1 !== '-') ? item.entrada1 : '';
            const saida1 = (item.saida1 && item.saida1 !== '-') ? item.saida1 : '';
            const entrada2 = (item.entrada2 && item.entrada2 !== '-') ? item.entrada2 : '';
            const saida2 = (item.saida2 && item.saida2 !== '-') ? item.saida2 : '';
            const horarioTotal = item.horario_total || '-';
            let horarioFaltando = item.horario_faltando || '-';
            if (horarioFaltando.startsWith('-')) {
                horarioFaltando = `<span class="text-danger">${horarioFaltando}</span>`;
            } else if (horarioFaltando.startsWith('+')) {
                horarioFaltando = `<span class="text-success">${horarioFaltando}</span>`;
            }
            let entrada1Cell = entrada1 || '-';
            let saida1Cell = saida1 || '-';
            let entrada2Cell = entrada2 || '-';
            let saida2Cell = saida2 || '-';
            if (podeEditar) {
                entrada1Cell = `<input type="time" class="form-control form-control-sm input-horario-editavel" data-campo="entrada1" data-funcionario-id="${item.funcionario_id}" data-data="${item.data}" value="${entrada1}" style="min-width: 80px;">`;
                saida1Cell = `<input type="time" class="form-control form-control-sm input-horario-editavel" data-campo="saida1" data-funcionario-id="${item.funcionario_id}" data-data="${item.data}" value="${saida1}" style="min-width: 80px;">`;
                entrada2Cell = `<input type="time" class="form-control form-control-sm input-horario-editavel" data-campo="entrada2" data-funcionario-id="${item.funcionario_id}" data-data="${item.data}" value="${entrada2}" style="min-width: 80px;">`;
                saida2Cell = `<input type="time" class="form-control form-control-sm input-horario-editavel" data-campo="saida2" data-funcionario-id="${item.funcionario_id}" data-data="${item.data}" value="${saida2}" style="min-width: 80px;">`;
            }
            const colFunc = isApenasUmFuncionario ? '' : `<td>${item.funcionario_nome}</td>`;
            const linha = `
                <tr>
                    <td>${item.data}</td>
                    ${colFunc}
                    <td>${entrada1Cell}</td>
                    <td>${saida1Cell}</td>
                    <td>${entrada2Cell}</td>
                    <td>${saida2Cell}</td>
                    <td>${horarioTotal}</td>
                    <td>${horarioFaltando}</td>
                </tr>
            `;
            tbody.append(linha);
        });
        if (podeEditar) {
            $('.input-horario-editavel').on('blur', function() {
                const $input = $(this);
                const funcionarioId = $input.data('funcionario-id');
                const data = $input.data('data');
                const campo = $input.data('campo');
                const valor = $input.val() || '';
                const valorOriginal = $input.data('valor-original') || '';
                if (valor !== valorOriginal) {
                    $input.data('valor-original', valor);
                    salvarAjusteHorario(funcionarioId, data, campo, valor);
                }
            });
            $('.input-horario-editavel').each(function() {
                const valorAtual = $(this).val() || '';
                $(this).data('valor-original', valorAtual);
            });
        }
    } else {
        thead.html('<th>Data</th><th>Funcionário</th><th>Entrada 1</th><th>Saída 1</th><th>Entrada 2</th><th>Saída 2</th><th>Horário Total</th><th>Horário Faltando</th>');
        tbody.append('<tr><td colspan="8" class="text-center text-muted">Nenhum dado encontrado para o período selecionado</td></tr>');
    }
}

function imprimirRelatorio() {
    if (!dadosRelatorio || dadosRelatorio.length === 0) {
        mostrarMensagem('error', 'Não há dados para imprimir');
        return;
    }
    const dataInicio = $('#filtroDataInicio').val();
    const dataFim = $('#filtroDataFim').val();
    const funcionariosIds = [...new Set(dadosRelatorio.map(i => i.funcionario_id))];
    const agrupadoPorFunc = {};
    funcionariosIds.forEach(id => { agrupadoPorFunc[id] = dadosRelatorio.filter(i => i.funcionario_id === id); });
    const multiplosFuncionarios = funcionariosIds.length > 1;
    let htmlBody = `
        <html>
            <head>
                <title>Relatório de Presença - CapitalCredito</title>
                <style>
                    @page { size: A4; margin: 12mm; }
                    * { box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; font-size: 9px; margin: 0; padding: 8px; max-width: 210mm; }
                    h1 { font-size: 14px; text-align: center; margin: 0 0 6px 0; }
                    .info-relatorio { font-size: 9px; margin-bottom: 6px; }
                    .dados-funcionario { font-size: 9px; margin: 8px 0 4px 0; padding: 4px; background: #f0f0f0; }
                    .bloco-funcionario { margin-bottom: 16px; page-break-inside: avoid; }
                    .bloco-funcionario.nova-pagina { page-break-before: always; }
                    .resumo-totais { font-size: 10px; font-weight: bold; margin: 8px 0; padding: 4px; background: #f5f5f5; }
                    table { width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 8px; }
                    th, td { border: 1px solid #333; padding: 2px 4px; text-align: center; line-height: 1.2; }
                    th { background-color: #e0e0e0; font-weight: bold; font-size: 8px; }
                    tr { height: 18px; }
                    .text-left { text-align: left; }
                    .titulo-justificativas { margin-top: 8px; margin-bottom: 4px; font-size: 10px; }
                    .lista-justificativas { margin: 0; padding-left: 18px; font-size: 8px; }
                </style>
            </head>
            <body>
    `;
    funcionariosIds.forEach((funcId, idx) => {
        const linhas = agrupadoPorFunc[funcId];
        const primeiro = linhas[0];
        const diasTrabalhados = linhas.filter(i => i.bateu_ponto).length;
        const diasJustificativa = linhas.filter(i => i.tem_justificativa).length;
        const justificativasLista = linhas.filter(i => i.tem_justificativa).map(i => `${i.data} - ${i.motivo_justificativa || i.tipo_justificativa || '-'}`);
        const htmlJustificativas = justificativasLista.length > 0 ? `<p class="titulo-justificativas"><strong>Justificativas:</strong></p><ul class="lista-justificativas">${justificativasLista.map(j => `<li>${j}</li>`).join('')}</ul>` : '';
        const classeNovaPagina = (multiplosFuncionarios && idx > 0) ? 'bloco-funcionario nova-pagina' : 'bloco-funcionario';
        const cabecalhoPagina = multiplosFuncionarios ? `<h1>Relatório de Presença - CapitalCredito</h1><p class="info-relatorio"><strong>Período:</strong> ${dataInicio} a ${dataFim}</p>` : '';
        if (idx === 0 && !multiplosFuncionarios) {
            htmlBody += `<h1>Relatório de Presença - CapitalCredito</h1><p class="info-relatorio"><strong>Período:</strong> ${dataInicio} a ${dataFim}</p>`;
        }
        htmlBody += `
                <div class="${classeNovaPagina}">
                    ${cabecalhoPagina}
                    <p class="dados-funcionario"><strong>Funcionário:</strong> ${primeiro.funcionario_nome} | <strong>CPF:</strong> ${primeiro.funcionario_cpf || '-'} | <strong>Chave PIX:</strong> ${primeiro.chave_pix || '-'}</p>
                    <p class="resumo-totais">Total: ${diasTrabalhados} dia(s) com presença registrada | ${diasJustificativa} dia(s) com justificativa</p>
                    <table>
                        <thead><tr><th>Data</th><th>Entr.1</th><th>Sai.1</th><th>Entr.2</th><th>Sai.2</th><th>Total</th><th>Faltando</th></tr></thead>
                        <tbody>
        `;
        linhas.forEach(function(item) {
            htmlBody += `<tr><td>${item.data}</td><td>${item.entrada1 || '-'}</td><td>${item.saida1 || '-'}</td><td>${item.entrada2 || '-'}</td><td>${item.saida2 || '-'}</td><td>${item.horario_total || '-'}</td><td>${item.horario_faltando || '-'}</td></tr>`;
        });
        htmlBody += `</tbody></table>${htmlJustificativas}</div>`;
    });
    htmlBody += '</body></html>';
    const printWindow = window.open('', '_blank');
    printWindow.document.write(htmlBody);
    printWindow.document.close();
    printWindow.print();
}

function salvarAjusteHorario(funcionarioId, data, campo, valor) {
    const linha = $(`input[data-funcionario-id="${funcionarioId}"][data-data="${data}"]`).closest('tr');
    const entrada1 = linha.find('input[data-campo="entrada1"]').val() || '';
    const saida1 = linha.find('input[data-campo="saida1"]').val() || '';
    const entrada2 = linha.find('input[data-campo="entrada2"]').val() || '';
    const saida2 = linha.find('input[data-campo="saida2"]').val() || '';
    const dataParts = data.split('/');
    const dataISO = `${dataParts[2]}-${dataParts[1]}-${dataParts[0]}`;
    dadosAjustePendente = {
        funcionario_id: funcionarioId,
        data: dataISO,
        entrada1: entrada1,
        saida1: saida1,
        entrada2: entrada2,
        saida2: saida2
    };
    const modal = new bootstrap.Modal(document.getElementById('modalJustificativa'));
    $('#justificativaFuncionarioId').val(funcionarioId);
    $('#justificativaData').val(dataISO);
    $('#justificativaTexto').val('');
    $('#justificativaArquivos').val('');
    modal.show();
}

function salvarJustificativa() {
    const justificativaTexto = $('#justificativaTexto').val().trim();
    if (!justificativaTexto) {
        mostrarMensagem('error', 'Justificativa é obrigatória');
        return;
    }
    if (!dadosAjustePendente) {
        mostrarMensagem('error', 'Erro: dados do ajuste não encontrados');
        return;
    }
    const formData = new FormData();
    formData.append('funcionario_id', dadosAjustePendente.funcionario_id);
    formData.append('data', dadosAjustePendente.data);
    if (dadosAjustePendente.entrada1 !== undefined) {
        formData.append('entrada1', dadosAjustePendente.entrada1 || '');
    }
    if (dadosAjustePendente.saida1 !== undefined) {
        formData.append('saida1', dadosAjustePendente.saida1 || '');
    }
    if (dadosAjustePendente.entrada2 !== undefined) {
        formData.append('entrada2', dadosAjustePendente.entrada2 || '');
    }
    if (dadosAjustePendente.saida2 !== undefined) {
        formData.append('saida2', dadosAjustePendente.saida2 || '');
    }
    formData.append('justificativa', justificativaTexto);
    const arquivos = $('#justificativaArquivos')[0].files;
    for (let i = 0; i < arquivos.length; i++) {
        formData.append('arquivos', arquivos[i]);
    }
    $.ajax({
        url: '/rh/ponto/api/registro/ajustar-horario/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val() || $('meta[name=csrf-token]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                mostrarMensagem('success', response.message);
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalJustificativa'));
                modal.hide();
                dadosAjustePendente = null;
                gerarRelatorio();
            } else {
                mostrarMensagem('error', response.message);
            }
        },
        error: function(xhr) {
            let mensagem = 'Erro ao salvar ajuste de horário';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                mensagem = xhr.responseJSON.message;
            }
            mostrarMensagem('error', mensagem);
        }
    });
}

function mostrarMensagem(tipo, mensagem) {
    const alertClass = tipo === 'success' ? 'alert-success' : 'alert-danger';
    const alert = $(`
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    $('.container-fluid').first().prepend(alert);
    setTimeout(function() {
        alert.fadeOut(function() {
            $(this).remove();
        });
    }, 5000);
}
