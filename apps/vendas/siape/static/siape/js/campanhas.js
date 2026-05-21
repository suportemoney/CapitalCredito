/**
 * Campanhas SIAPE - JavaScript
 * Sistema de importação de CSV com SSE e feedback visual de etapas
 */

// URLs dinâmicas do Django (carregadas dos data-attributes)
let URLS = {
    listar: '',
    criar: '',
    importar: '',
    modelo: ''
};

// Estado da aplicação
let importacaoEmAndamento = false;
let etapaAtual = null;

// Ordem das etapas para controle visual
const ETAPAS_ORDEM = ['envio', 'leitura', 'validacao', 'processamento', 'salvamento', 'finalizacao'];

$(document).ready(function() {
    // Carregar URLs dos data-attributes
    const container = $('#campanhas-container');
    URLS.listar = container.data('url-listar');
    URLS.criar = container.data('url-criar');
    URLS.importar = container.data('url-importar');
    URLS.modelo = container.data('url-modelo');
    // Inicializar página
    carregarCampanhas();
    carregarCampanhasSelect();
});

function carregarCampanhas() {
    $.ajax({
        url: URLS.listar,
        method: 'GET',
        success: function(data) {
            const tbody = $('#campanhas-tbody');
            tbody.empty();
            if (data.length === 0) {
                tbody.append('<tr><td colspan="7" class="text-center">Nenhuma campanha cadastrada</td></tr>');
                return;
            }
            data.forEach(function(camp) {
                const statusBadge = camp.status ? 
                    '<span class="badge bg-success">Ativa</span>' : 
                    '<span class="badge bg-danger">Inativa</span>';
                tbody.append(`
                    <tr>
                        <td>${camp.id}</td>
                        <td>${escapeHtml(camp.titulo)}</td>
                        <td>${statusBadge}</td>
                        <td>${camp.total_matriculas.toLocaleString('pt-BR')}</td>
                        <td>${camp.total_contratos.toLocaleString('pt-BR')}</td>
                        <td>${camp.data_criacao}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="abrirModalEditarCampanha(${camp.id})" title="Editar">
                                <i class='bx bx-edit'></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deletarCampanha(${camp.id}, '${escapeHtml(camp.titulo)}')" title="Deletar">
                                <i class='bx bx-trash'></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        },
        error: function(xhr) {
            console.error('Erro ao carregar campanhas:', xhr);
            $('#campanhas-tbody').html('<tr><td colspan="7" class="text-center text-danger">Erro ao carregar campanhas</td></tr>');
        }
    });
}

function carregarCampanhasSelect() {
    $.ajax({
        url: URLS.listar,
        method: 'GET',
        success: function(data) {
            const select = $('#campanha_importacao');
            select.empty();
            select.append('<option value="">Selecione uma campanha...</option>');
            data.forEach(function(camp) {
                if (camp.status) {
                    select.append(`<option value="${camp.id}">${escapeHtml(camp.titulo)}</option>`);
                }
            });
        },
        error: function(xhr) {
            console.error('Erro ao carregar campanhas para select:', xhr);
        }
    });
}

function abrirModalCriarCampanha() {
    $('#modalCampanhaTitle').text('Nova Campanha');
    $('#formCampanha')[0].reset();
    $('#campanha_id').val('');
    $('#campanha_status').prop('checked', true);
    new bootstrap.Modal(document.getElementById('modalCampanha')).show();
}

function abrirModalEditarCampanha(id) {
    const urlEditar = URLS.listar.replace('listar/', `editar/${id}/`);
    $.ajax({
        url: urlEditar,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const camp = response.data;
                $('#modalCampanhaTitle').text('Editar Campanha');
                $('#campanha_id').val(camp.id);
                $('#campanha_titulo').val(camp.titulo);
                $('#campanha_status').prop('checked', camp.status);
                new bootstrap.Modal(document.getElementById('modalCampanha')).show();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao buscar campanha: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function salvarCampanha() {
    const campanhaId = $('#campanha_id').val();
    const titulo = $('#campanha_titulo').val().trim();
    const status = $('#campanha_status').prop('checked');
    if (!titulo) {
        alert('Título é obrigatório');
        return;
    }
    // Desabilitar botão durante salvamento
    const btnSalvar = $('#btn-salvar-campanha');
    btnSalvar.prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin"></i> Salvando...');
    const formData = new FormData();
    formData.append('titulo', titulo);
    formData.append('status', status ? 'on' : 'off');
    formData.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());
    const url = campanhaId ? 
        URLS.listar.replace('listar/', `editar/${campanhaId}/`) : 
        URLS.criar;
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            btnSalvar.prop('disabled', false).html('Salvar');
            if (response.success) {
                alert(response.message || 'Campanha salva com sucesso!');
                bootstrap.Modal.getInstance(document.getElementById('modalCampanha')).hide();
                carregarCampanhas();
                carregarCampanhasSelect();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            btnSalvar.prop('disabled', false).html('Salvar');
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar campanha: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function deletarCampanha(id, titulo) {
    if (!confirm(`Tem certeza que deseja deletar a campanha "${titulo}"?\n\nAtenção: Esta ação não pode ser desfeita!`)) {
        return;
    }
    const urlDeletar = URLS.listar.replace('listar/', `deletar/${id}/`);
    $.ajax({
        url: urlDeletar,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message || 'Campanha deletada com sucesso!');
                carregarCampanhas();
                carregarCampanhasSelect();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao deletar campanha: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function downloadModelo() {
    window.location.href = URLS.modelo;
}

function desabilitarFormulario(desabilitar) {
    $('#campanha_importacao').prop('disabled', desabilitar);
    $('#arquivo_csv').prop('disabled', desabilitar);
    $('#btn-download-modelo').prop('disabled', desabilitar);
    const btnImportar = $('#btn-iniciar-importacao');
    if (desabilitar) {
        btnImportar.prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin"></i> Importando...');
    } else {
        btnImportar.prop('disabled', false).html('<i class="bx bx-upload"></i> Iniciar Importação');
    }
}

function resetarEtapas() {
    ETAPAS_ORDEM.forEach(function(etapa) {
        const elemento = $(`#etapa-${etapa}`);
        elemento.removeClass('etapa-processando etapa-concluida etapa-erro');
        elemento.find('.etapa-status .badge')
            .removeClass('bg-primary bg-success bg-danger bg-warning')
            .addClass('bg-secondary')
            .text('Pendente');
        elemento.find('.etapa-icone i').removeClass('bx-spin');
    });
    etapaAtual = null;
}

function atualizarEtapa(etapa, status, mensagem) {
    const elemento = $(`#etapa-${etapa}`);
    if (!elemento.length) return;
    // Marcar etapas anteriores como concluídas
    const idxAtual = ETAPAS_ORDEM.indexOf(etapa);
    ETAPAS_ORDEM.forEach(function(e, idx) {
        if (idx < idxAtual) {
            const el = $(`#etapa-${e}`);
            el.removeClass('etapa-processando etapa-erro').addClass('etapa-concluida');
            el.find('.etapa-status .badge')
                .removeClass('bg-secondary bg-primary bg-danger bg-warning')
                .addClass('bg-success')
                .text('Concluído');
            el.find('.etapa-icone i').removeClass('bx-spin');
        }
    });
    // Atualizar etapa atual
    elemento.removeClass('etapa-processando etapa-concluida etapa-erro');
    const badge = elemento.find('.etapa-status .badge');
    const icone = elemento.find('.etapa-icone i');
    badge.removeClass('bg-secondary bg-primary bg-success bg-danger bg-warning');
    icone.removeClass('bx-spin');
    switch(status) {
        case 'processando':
            elemento.addClass('etapa-processando');
            badge.addClass('bg-primary').text('Processando');
            icone.addClass('bx-spin');
            break;
        case 'concluido':
            elemento.addClass('etapa-concluida');
            badge.addClass('bg-success').text('Concluído');
            break;
        case 'erro':
            elemento.addClass('etapa-erro');
            badge.addClass('bg-danger').text('Erro');
            break;
        default:
            badge.addClass('bg-secondary').text('Pendente');
    }
    // Atualizar descrição se fornecida
    if (mensagem) {
        elemento.find('.etapa-descricao').text(mensagem);
    }
    etapaAtual = etapa;
}

function atualizarProgresso(progresso, mensagem) {
    const barraProgresso = $('#barra-progresso');
    const porcentagem = $('#porcentagem-progresso');
    const detalhes = $('#detalhes-progresso');
    barraProgresso.css('width', progresso + '%');
    porcentagem.text(progresso.toFixed(1) + '%');
    if (mensagem) {
        detalhes.html(`<i class='bx bx-info-circle'></i> ${escapeHtml(mensagem)}`);
    }
}

function iniciarImportacao() {
    if (importacaoEmAndamento) {
        alert('Já existe uma importação em andamento!');
        return;
    }
    const campanhaId = $('#campanha_importacao').val();
    const arquivo = $('#arquivo_csv')[0].files[0];
    if (!campanhaId) {
        alert('Selecione uma campanha');
        return;
    }
    if (!arquivo) {
        alert('Selecione um arquivo CSV');
        return;
    }
    if (!arquivo.name.toLowerCase().endsWith('.csv')) {
        alert('Arquivo deve ser CSV');
        return;
    }
    // Verificar tamanho (50MB)
    if (arquivo.size > 50 * 1024 * 1024) {
        alert('Arquivo muito grande! Máximo de 50MB permitido.');
        return;
    }
    // Iniciar processo
    importacaoEmAndamento = true;
    desabilitarFormulario(true);
    resetarEtapas();
    $('#area-etapas').show();
    $('#area-resultado').hide();
    atualizarProgresso(0, 'Iniciando importação...');
    const formData = new FormData();
    formData.append('campanha_id', campanhaId);
    formData.append('arquivo_csv', arquivo);
    formData.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());
    fetch(URLS.importar, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': $('input[name="csrfmiddlewaretoken"]').val()
        }
    }).then(response => {
        if (!response.ok) {
            throw new Error('Erro ao iniciar importação');
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        function processarChunk() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    finalizarImportacao();
                    return;
                }
                buffer += decoder.decode(value, { stream: true });
                const linhas = buffer.split('\n');
                buffer = linhas.pop();
                linhas.forEach(linha => {
                    if (linha.startsWith('data: ')) {
                        try {
                            const dados = JSON.parse(linha.substring(6));
                            processarEventoSSE(dados);
                        } catch (e) {
                            console.error('Erro ao processar evento SSE:', e);
                        }
                    }
                });
                processarChunk();
            }).catch(err => {
                console.error('Erro ao ler stream:', err);
                atualizarEtapa(etapaAtual || 'envio', 'erro', 'Erro na conexão');
                $('#detalhes-progresso').html('<span class="text-danger"><i class="bx bx-error-circle"></i> Erro ao processar importação</span>');
                finalizarImportacao();
            });
        }
        processarChunk();
    }).catch(err => {
        console.error('Erro:', err);
        alert('Erro ao iniciar importação: ' + err.message);
        finalizarImportacao();
    });
}

function finalizarImportacao() {
    importacaoEmAndamento = false;
    desabilitarFormulario(false);
    // Resetar input de arquivo
    $('#arquivo_csv').val('');
}

function processarEventoSSE(dados) {
    const etapa = dados.etapa;
    const progresso = dados.progresso || 0;
    const mensagem = dados.mensagem || '';
    switch(etapa) {
        case 'envio':
            atualizarEtapa('envio', 'processando', mensagem);
            atualizarProgresso(progresso, mensagem);
            break;
        case 'leitura':
            atualizarEtapa('leitura', 'processando', mensagem);
            atualizarProgresso(progresso, mensagem);
            if (dados.total_linhas) {
                $('#detalhes-progresso').html(`<i class='bx bx-file'></i> ${dados.total_linhas.toLocaleString('pt-BR')} linhas detectadas`);
            }
            break;
        case 'validacao':
            atualizarEtapa('validacao', 'processando', mensagem);
            atualizarProgresso(progresso, mensagem);
            break;
        case 'processamento':
            atualizarEtapa('processamento', 'processando', mensagem);
            atualizarProgresso(progresso, mensagem);
            if (dados.linha_atual && dados.total_linhas) {
                const detalhesHtml = `
                    <i class='bx bx-cog bx-spin'></i> 
                    Processando linha ${dados.linha_atual.toLocaleString('pt-BR')} de ${dados.total_linhas.toLocaleString('pt-BR')}
                    ${dados.batch_atual ? ` (Batch ${dados.batch_atual}/${dados.total_batches})` : ''}
                `;
                $('#detalhes-progresso').html(detalhesHtml);
            }
            break;
        case 'salvamento':
            atualizarEtapa('salvamento', 'processando', mensagem);
            atualizarProgresso(progresso, mensagem);
            break;
        case 'finalizacao':
            atualizarEtapa('finalizacao', 'concluido', mensagem);
            atualizarProgresso(100, 'Importação finalizada!');
            // Marcar todas as etapas como concluídas
            ETAPAS_ORDEM.forEach(e => atualizarEtapa(e, 'concluido'));
            // Remover animação da barra de progresso
            $('#barra-progresso').removeClass('progress-bar-animated').addClass('bg-success');
            // Mostrar resultado
            if (dados.resultado) {
                mostrarResultado(dados.resultado);
            }
            // Recarregar lista de campanhas
            carregarCampanhas();
            break;
        case 'erro':
            atualizarEtapa(etapaAtual || 'envio', 'erro', mensagem);
            $('#barra-progresso').removeClass('progress-bar-animated bg-primary').addClass('bg-danger');
            $('#area-resultado').show();
            $('#conteudo-resultado').html(`
                <div class="alert alert-danger">
                    <h6><i class='bx bx-error-circle'></i> Erro na Importação</h6>
                    <p class="mb-0">${escapeHtml(mensagem)}</p>
                </div>
            `);
            finalizarImportacao();
            break;
    }
}

function mostrarResultado(resultado) {
    setTimeout(function() {
        $('#area-etapas').slideUp(300, function() {
            $('#area-resultado').show();
            const htmlResultado = `
                <div class="alert alert-success">
                    <h6><i class='bx bx-check-circle'></i> Importação Finalizada com Sucesso!</h6>
                    <div class="row mt-2">
                        <div class="col-md-4">
                            <small><strong>Tempo decorrido:</strong> ${resultado.tempo_decorrido}</small>
                        </div>
                        <div class="col-md-4">
                            <small><strong>Início:</strong> ${resultado.data_inicio}</small>
                        </div>
                        <div class="col-md-4">
                            <small><strong>Fim:</strong> ${resultado.data_fim}</small>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-3">
                        <div class="card text-center mb-3 border-success">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Sucessos</h6>
                                <p class="h3 text-success mb-0">${resultado.sucesso.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center mb-3 border-danger">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Falhas</h6>
                                <p class="h3 text-danger mb-0">${resultado.falhas.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center mb-3 border-primary">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Clientes Novos</h6>
                                <p class="h3 text-primary mb-0">${resultado.clientes_novos.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center mb-3 border-info">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Clientes Atualizados</h6>
                                <p class="h3 text-info mb-0">${resultado.clientes_atualizados.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-3">
                        <div class="card text-center mb-3">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Matrículas Novas</h6>
                                <p class="h4 mb-0">${resultado.matriculas_novas.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center mb-3">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Matrículas Atualizadas</h6>
                                <p class="h4 mb-0">${resultado.matriculas_atualizadas.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center mb-3">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Contratos Novos</h6>
                                <p class="h4 mb-0">${resultado.contratos_novos.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center mb-3">
                            <div class="card-body py-3">
                                <h6 class="card-subtitle mb-2 text-muted">Contratos Atualizados</h6>
                                <p class="h4 mb-0">${resultado.contratos_atualizados.toLocaleString('pt-BR')}</p>
                            </div>
                        </div>
                    </div>
                </div>
                ${resultado.total_erros > 0 ? `
                    <div class="alert alert-warning mt-3">
                        <h6><i class='bx bx-error'></i> Erros Encontrados (${resultado.total_erros.toLocaleString('pt-BR')})</h6>
                        <div style="max-height: 200px; overflow-y: auto;">
                            <ul class="mb-0 small">
                                ${resultado.erros.map(erro => `<li>${escapeHtml(erro)}</li>`).join('')}
                            </ul>
                            ${resultado.total_erros > 50 ? `<p class="mb-0 mt-2 text-muted"><em>Mostrando apenas os primeiros 50 erros...</em></p>` : ''}
                        </div>
                    </div>
                ` : ''}
                <div class="text-center mt-3">
                    <button class="btn btn-primary" onclick="novaImportacao()">
                        <i class='bx bx-plus'></i> Nova Importação
                    </button>
                </div>
            `;
            $('#conteudo-resultado').html(htmlResultado);
        });
    }, 500);
}

function novaImportacao() {
    $('#area-resultado').hide();
    $('#area-etapas').hide();
    resetarEtapas();
    $('#barra-progresso')
        .css('width', '0%')
        .removeClass('bg-success bg-danger')
        .addClass('bg-primary progress-bar-animated');
    $('#porcentagem-progresso').text('0%');
    $('#detalhes-progresso').html('<i class="bx bx-time"></i> Aguardando início...');
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


