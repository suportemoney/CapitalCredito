$(document).ready(function() {
    carregarJustificativas();
});

function criarJustificativa(tipo) {
    let formId, tituloId, tipoId, funcionarioId, funcionariosIds, dataInicioId, dataFimId, observacoesId, arquivosId;
    if (tipo === 'funcionario') {
        formId = '#formJustificativaFuncionario';
        tituloId = '#tituloFuncionario';
        tipoId = '#tipoFuncionario';
        funcionarioId = '#funcionarioId';
        dataInicioId = '#dataInicioFuncionario';
        dataFimId = '#dataFimFuncionario';
        observacoesId = '#observacoesFuncionario';
        arquivosId = '#arquivosFuncionario';
    } else {
        formId = '#formJustificativaLote';
        tituloId = '#tituloLote';
        tipoId = '#tipoLote';
        funcionariosIds = '#funcionariosIds';
        dataInicioId = '#dataInicioLote';
        dataFimId = '#dataFimLote';
        observacoesId = '#observacoesLote';
        arquivosId = '#arquivosLote';
    }
    const titulo = $(tituloId).val().trim();
    const tipoJust = $(tipoId).val();
    const dataInicio = $(dataInicioId).val();
    const dataFim = $(dataFimId).val();
    const observacoes = $(observacoesId).val().trim();
    if (!titulo) {
        mostrarMensagem('error', 'Título é obrigatório');
        return;
    }
    if (!tipoJust) {
        mostrarMensagem('error', 'Tipo é obrigatório');
        return;
    }
    if (!dataInicio) {
        mostrarMensagem('error', 'Data início é obrigatória');
        return;
    }
    if (!dataFim) {
        mostrarMensagem('error', 'Data fim é obrigatória');
        return;
    }
    if (tipo === 'funcionario') {
        const funcionarioIdVal = $(funcionarioId).val();
        if (!funcionarioIdVal) {
            mostrarMensagem('error', 'Funcionário é obrigatório');
            return;
        }
    } else {
        const funcionariosSelecionados = $(funcionariosIds).val();
        if (!funcionariosSelecionados || funcionariosSelecionados.length === 0) {
            mostrarMensagem('error', 'Selecione pelo menos um funcionário');
            return;
        }
    }
    const formData = new FormData();
    formData.append('titulo', titulo);
    formData.append('tipo', tipoJust);
    formData.append('data_inicio', dataInicio);
    formData.append('data_fim', dataFim);
    formData.append('observacoes', observacoes);
    if (tipo === 'funcionario') {
        formData.append('funcionario_id', $(funcionarioId).val());
    } else {
        $(funcionariosIds).val().forEach(function(id) {
            formData.append('funcionarios_ids[]', id);
        });
    }
    const arquivos = $(arquivosId)[0].files;
    for (let i = 0; i < arquivos.length; i++) {
        formData.append('arquivos[]', arquivos[i]);
    }
    $.ajax({
        url: '/rh/ponto/api/justificativas/criar/',
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
                $(formId)[0].reset();
                carregarJustificativas();
            } else {
                mostrarMensagem('error', response.message);
            }
        },
        error: function(xhr) {
            let mensagem = 'Erro ao criar justificativa';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                mensagem = xhr.responseJSON.message;
            }
            mostrarMensagem('error', mensagem);
        }
    });
}

function carregarJustificativas() {
    $.ajax({
        url: '/rh/ponto/api/justificativas/listar/',
        method: 'GET',
        success: function(response) {
            const tbody = $('#tbodyJustificativas');
            tbody.empty();
            if (response.success && response.data.length > 0) {
                response.data.forEach(function(just) {
                    const linha = `
                        <tr>
                            <td>${just.titulo}</td>
                            <td>${just.tipo}</td>
                            <td>${just.funcionario}</td>
                            <td>${just.data_inicio} a ${just.data_fim}</td>
                            <td>${just.criado_por || '-'}</td>
                            <td>${just.data_criacao}</td>
                        </tr>
                    `;
                    tbody.append(linha);
                });
            } else {
                tbody.append('<tr><td colspan="6" class="text-center text-muted">Nenhuma justificativa encontrada</td></tr>');
            }
        },
        error: function() {
            $('#tbodyJustificativas').html('<tr><td colspan="6" class="text-center text-danger">Erro ao carregar justificativas</td></tr>');
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
