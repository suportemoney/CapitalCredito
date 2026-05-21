// JavaScript para gerenciar bancos (Admin)
$(document).ready(function() {
    carregarBancos();
    
    // Evento do botão Confirmar e Ativar
    $('#btnConfirmarAtivacao').on('click', function() {
        confirmarAtivacao();
    });
});

let bancoSelecionadoId = null;
let convenioSelecionadoId = null;
let operacaoSelecionadaId = null;
let convenioOperacaoSelecionadoId = null;

function carregarBancos() {
    $.ajax({
        url: '/operacional/contratos/api/bancos/todos/',  // API para admin - mostra TODOS os bancos
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderizarBancos(response.data);
            } else {
                console.error('Erro ao carregar bancos:', response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar bancos:', xhr.responseText);
        }
    });
}

function renderizarBancos(bancos) {
    let html = '';
    
    if (bancos.length === 0) {
        html = '<p class="text-muted">Nenhum banco encontrado. Cadastre bancos na aba Administrativo.</p>';
    } else {
        bancos.forEach(function(banco) {
            const badgeConvenios = banco.convenios_ativos > 0 
                ? `<span class="badge bg-success">${banco.convenios_ativos} convênio(s) ativo(s)</span>`
                : '<span class="badge bg-secondary">Nenhum convênio ativo</span>';
            
            html += `
                <div class="banco-item mb-3 border rounded p-3" data-banco-id="${banco.id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="bx bx-building"></i> ${banco.nome}
                            ${banco.codigo ? `<span class="badge bg-info">${banco.codigo}</span>` : ''}
                            ${badgeConvenios}
                        </h5>
                        <button class="btn btn-sm btn-primary" onclick="carregarConveniosParaBanco(${banco.id}, this)">
                            <i class="bx bx-chevron-down"></i> Ver Convênios
                        </button>
                    </div>
                    <div class="convenios-list mt-3" style="display: none;" data-banco-id="${banco.id}">
                        <!-- Convênios serão carregados aqui -->
                    </div>
                </div>
            `;
        });
    }
    
    $('#bancos-list').html(html);
}

function carregarConveniosParaBanco(bancoId, button) {
    bancoSelecionadoId = bancoId;
    const conveniosList = $(`.convenios-list[data-banco-id="${bancoId}"]`);
    
    if (conveniosList.is(':visible')) {
        conveniosList.slideUp();
        $(button).html('<i class="bx bx-chevron-down"></i> Ver Convênios');
        return;
    }
    
    // Se já foi carregado, apenas mostrar
    if (conveniosList.data('loaded')) {
        conveniosList.slideDown();
        $(button).html('<i class="bx bx-chevron-up"></i> Ocultar Convênios');
        return;
    }
    
    $.ajax({
        url: '/operacional/contratos/api/convenios/por-banco-admin/',  // API para admin
        method: 'GET',
        data: { banco_id: bancoId },
        success: function(response) {
            if (response.success) {
                renderizarConveniosParaBanco(bancoId, response.data);
                conveniosList.data('loaded', true);
                conveniosList.slideDown();
                $(button).html('<i class="bx bx-chevron-up"></i> Ocultar Convênios');
            } else {
                alert('Erro ao carregar convênios: ' + response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar convênios:', xhr.responseText);
            alert('Erro ao carregar convênios');
        }
    });
}

function renderizarConveniosParaBanco(bancoId, convenios) {
    const conveniosList = $(`.convenios-list[data-banco-id="${bancoId}"]`);
    let html = '';
    
    if (convenios.length === 0) {
        html = '<p class="text-muted">Nenhum convênio com schemas encontrado. Importe schemas na aba Administrativo.</p>';
    } else {
        convenios.forEach(function(convenio) {
            const badgeOperacoes = convenio.operacoes_ativas > 0 
                ? `<span class="badge bg-success">${convenio.operacoes_ativas} operação(ões) ativa(s)</span>`
                : '<span class="badge bg-warning">Nenhuma operação ativa</span>';
            
            html += `
                <div class="convenio-item mb-2 border rounded p-2 ms-3" data-convenio-id="${convenio.id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="bx bx-check-shield"></i> ${convenio.nome}
                            ${convenio.codigo ? `<span class="badge bg-info">${convenio.codigo}</span>` : ''}
                            ${badgeOperacoes}
                        </h6>
                        <button class="btn btn-sm btn-success" onclick="carregarOperacoesParaBancoConvenio(${bancoId}, ${convenio.id}, this)">
                            <i class="bx bx-chevron-down"></i> Ver Operações
                        </button>
                    </div>
                    <div class="operacoes-list mt-2" style="display: none;" data-banco-id="${bancoId}" data-convenio-id="${convenio.id}">
                        <!-- Operações serão carregadas aqui -->
                    </div>
                </div>
            `;
        });
    }
    
    conveniosList.html(html);
}

function carregarOperacoesParaBancoConvenio(bancoId, convenioId, button) {
    convenioSelecionadoId = convenioId;
    const operacoesList = $(`.operacoes-list[data-banco-id="${bancoId}"][data-convenio-id="${convenioId}"]`);
    
    if (operacoesList.is(':visible')) {
        operacoesList.slideUp();
        $(button).html('<i class="bx bx-chevron-down"></i> Ver Operações');
        return;
    }
    
    // Se já foi carregado, apenas mostrar
    if (operacoesList.data('loaded')) {
        operacoesList.slideDown();
        $(button).html('<i class="bx bx-chevron-up"></i> Ocultar Operações');
        return;
    }
    
    $.ajax({
        url: '/operacional/contratos/api/operacoes/por-banco-convenio-admin/',  // API para admin
        method: 'GET',
        data: { banco_id: bancoId, convenio_id: convenioId },
        success: function(response) {
            if (response.success) {
                renderizarOperacoesParaBancoConvenio(bancoId, convenioId, response.data);
                operacoesList.data('loaded', true);
                operacoesList.slideDown();
                $(button).html('<i class="bx bx-chevron-up"></i> Ocultar Operações');
            } else {
                alert('Erro ao carregar operações: ' + response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar operações:', xhr.responseText);
            alert('Erro ao carregar operações');
        }
    });
}

function renderizarOperacoesParaBancoConvenio(bancoId, convenioId, operacoes) {
    const operacoesList = $(`.operacoes-list[data-banco-id="${bancoId}"][data-convenio-id="${convenioId}"]`);
    let html = '';
    
    if (operacoes.length === 0) {
        html = '<p class="text-muted small">Nenhuma operação com schema encontrada para este convênio. Importe schemas na aba Administrativo.</p>';
    } else {
        operacoes.forEach(function(operacao) {
            // Mostrar status de ativação para este banco
            let badgeStatus = '';
            if (operacao.ativo) {
                badgeStatus = `<span class="badge bg-success"><i class="bx bx-check"></i> ATIVO: ${operacao.schema_ativo_titulo || 'Schema Ativo'}</span>`;
            } else {
                badgeStatus = `<span class="badge bg-secondary">Não ativo para este banco</span>`;
            }
            
            html += `
                <div class="operacao-item mb-1 border rounded p-2 ms-3 ${operacao.ativo ? 'bg-success bg-opacity-10' : 'bg-light'}" data-operacao-id="${operacao.id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span>
                            <i class="bx bx-file"></i> ${operacao.nome}
                            ${operacao.codigo ? `<span class="badge bg-primary">${operacao.codigo}</span>` : ''}
                            ${badgeStatus}
                            <span class="badge bg-info">${operacao.schemas_disponiveis} schema(s) disponível(is)</span>
                        </span>
                        <button class="btn btn-sm btn-info" onclick="carregarSchemasParaOperacao(${bancoId}, ${convenioId}, ${operacao.id}, this)">
                            <i class="bx bx-chevron-down"></i> Ver Schemas
                        </button>
                    </div>
                    <div class="schemas-list mt-2" style="display: none;" data-banco-id="${bancoId}" data-convenio-id="${convenioId}" data-operacao-id="${operacao.id}">
                        <!-- Schemas serão carregados aqui -->
                    </div>
                </div>
            `;
        });
    }
    
    operacoesList.html(html);
}

function carregarSchemasParaOperacao(bancoId, convenioId, operacaoId, button) {
    operacaoSelecionadaId = operacaoId;
    const schemasList = $(`.schemas-list[data-banco-id="${bancoId}"][data-convenio-id="${convenioId}"][data-operacao-id="${operacaoId}"]`);
    
    if (schemasList.is(':visible')) {
        schemasList.slideUp();
        $(button).html('<i class="bx bx-chevron-down"></i> Ver Schemas');
        return;
    }
    
    // Se já foi carregado, apenas mostrar
    if (schemasList.data('loaded')) {
        schemasList.slideDown();
        $(button).html('<i class="bx bx-chevron-up"></i> Ocultar Schemas');
        return;
    }
    
    $.ajax({
        url: '/operacional/contratos/api/schemas/por-operacao-admin/',  // API para admin
        method: 'GET',
        data: { banco_id: bancoId, convenio_id: convenioId, operacao_id: operacaoId },
        success: function(response) {
            if (response.success) {
                renderizarSchemasParaOperacao(bancoId, convenioId, operacaoId, response.data);
                schemasList.data('loaded', true);
                schemasList.slideDown();
                $(button).html('<i class="bx bx-chevron-up"></i> Ocultar Schemas');
            } else {
                alert('Erro ao carregar schemas: ' + response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar schemas:', xhr.responseText);
            alert('Erro ao carregar schemas');
        }
    });
}

function renderizarSchemasParaOperacao(bancoId, convenioId, operacaoId, schemas) {
    const schemasList = $(`.schemas-list[data-banco-id="${bancoId}"][data-convenio-id="${convenioId}"][data-operacao-id="${operacaoId}"]`);
    let html = '';
    
    if (schemas.length === 0) {
        html = '<p class="text-muted small">Nenhum schema encontrado. Importe schemas na aba Administrativo.</p>';
    } else {
        schemas.forEach(function(schema) {
            // Mostrar se este schema está ativo para este banco
            const ativoParaBanco = schema.ativo_para_banco;
            const badgeAtivo = ativoParaBanco 
                ? '<span class="badge bg-success"><i class="bx bx-check"></i> ATIVO</span>'
                : '';
            
            const btnClass = ativoParaBanco ? 'btn-success' : 'btn-warning';
            const btnText = ativoParaBanco ? '<i class="bx bx-check"></i> Ativo' : '<i class="bx bx-show"></i> Visualizar/Ativar';
            
            html += `
                <div class="schema-item mb-1 border rounded p-2 ms-3 ${ativoParaBanco ? 'bg-success bg-opacity-10' : 'bg-white'}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span>
                            <i class="bx bx-file"></i> <strong>${schema.titulo}</strong>
                            <span class="badge bg-secondary">${schema.campos_count} campos</span>
                            ${badgeAtivo}
                        </span>
                        <div>
                            <button class="btn btn-sm btn-info me-1" onclick="visualizarSchema(${schema.id}, '${escapeHtml(schema.titulo)}', ${convenioId}, ${operacaoId})">
                                <i class="bx bx-show"></i> Preview
                            </button>
                            ${!ativoParaBanco ? `
                                <button class="btn btn-sm btn-success" onclick="ativarSchemaParaBanco(${bancoId}, ${schema.id}, '${escapeHtml(schema.titulo)}')">
                                    <i class="bx bx-power-off"></i> Ativar
                                </button>
                            ` : `
                                <button class="btn btn-sm btn-danger" onclick="desativarSchemaParaBanco(${bancoId}, ${schema.id})">
                                    <i class="bx bx-x"></i> Desativar
                                </button>
                            `}
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    schemasList.html(html);
}

// Função para escapar HTML em strings
function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;")
               .replace(/</g, "&lt;")
               .replace(/>/g, "&gt;")
               .replace(/"/g, "&quot;")
               .replace(/'/g, "&#039;");
}

function visualizarSchema(convenioOperacaoId, titulo, convenioId, operacaoId) {
    convenioOperacaoSelecionadoId = convenioOperacaoId;
    
    // Carregar campos do schema
    $.ajax({
        url: '/operacional/contratos/api/schema/campos/',
        method: 'GET',
        data: { convenio_operacao_id: convenioOperacaoId },
        success: function(response) {
            if (response.success) {
                abrirModalPreviewSchema(titulo, response.data, convenioId, operacaoId, convenioOperacaoId);
            } else {
                alert('Erro ao carregar campos do schema: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao carregar campos do schema');
        }
    });
}

function abrirModalPreviewSchema(titulo, campos, convenioId, operacaoId, convenioOperacaoId) {
    // Primeiro, agrupar campos por página
    const camposPorPagina = {};
    campos.forEach(function(campo) {
        const pagina = campo.pagina || 1;
        if (!camposPorPagina[pagina]) {
            camposPorPagina[pagina] = [];
        }
        camposPorPagina[pagina].push(campo);
    });
    
    // Ordenar páginas
    const paginas = Object.keys(camposPorPagina).map(Number).sort((a, b) => a - b);
    const totalPaginas = paginas.length;
    
    let htmlForm = '';
    
    // Mostrar indicador de páginas
    if (totalPaginas > 1) {
        htmlForm += `<div class="alert alert-warning mb-3">
            <i class="bx bx-file"></i> <strong>Este schema possui ${totalPaginas} página(s)</strong>
            - O consultor verá uma página por vez ao preencher o contrato.
        </div>`;
    }
    
    paginas.forEach(function(pagina) {
        const camposDaPagina = camposPorPagina[pagina];
        
        // Cabeçalho da página
        htmlForm += `<div class="page-preview mb-4 p-3 border rounded bg-light">`;
        htmlForm += `<h5 class="text-primary mb-3"><i class="bx bx-file"></i> Página ${pagina} de ${totalPaginas}</h5>`;
        
        // Agrupar campos desta página por categoria
        const camposPorCategoria = {};
        camposDaPagina.forEach(function(campo) {
            if (!camposPorCategoria[campo.category]) {
                camposPorCategoria[campo.category] = [];
            }
            camposPorCategoria[campo.category].push(campo);
        });
        
        // Ordenar categorias
        const categorias = Object.keys(camposPorCategoria).sort();
        
        categorias.forEach(function(categoria) {
            htmlForm += `<div class="mb-3"><h6 class="border-bottom pb-2 text-secondary">${categoria.replace(/_/g, ' ').toUpperCase()}</h6>`;
            // Ordenar campos por ordem dentro da categoria
            camposPorCategoria[categoria].sort((a, b) => (a.ordem || 0) - (b.ordem || 0));
            camposPorCategoria[categoria].forEach(function(campo) {
                htmlForm += renderizarCampoPreview(campo);
            });
            htmlForm += '</div>';
        });
        
        htmlForm += `</div>`;
    });
    
    $('#modalPreviewSchemaTitulo').text(titulo + (totalPaginas > 1 ? ` (${totalPaginas} páginas)` : ''));
    $('#modalPreviewSchemaForm').html(htmlForm);
    $('#modalPreviewSchema').data('convenio-id', convenioId);
    $('#modalPreviewSchema').data('operacao-id', operacaoId);
    $('#modalPreviewSchema').data('convenio-operacao-id', convenioOperacaoId);
    $('#modalPreviewSchema').modal('show');
}

function renderizarCampoPreview(campo) {
    const required = campo.required ? '<span class="text-danger">*</span>' : '';
    let html = `<div class="mb-3">`;
    html += `<label class="form-label">${campo.label} ${required}</label>`;
    
    const campoType = (campo.type || '').toUpperCase();
    
    switch(campoType) {
        case 'TEXT':
        case 'EMAIL':
        case 'TEL':
        case 'PASSWORD':
            html += `<input type="${campo.type.toLowerCase()}" class="form-control" placeholder="${campo.placeholder || ''}" disabled>`;
            break;
        case 'NUMBER':
        case 'DECIMAL':
            html += `<input type="number" class="form-control" placeholder="${campo.placeholder || ''}" disabled>`;
            break;
        case 'DATE':
            html += `<input type="date" class="form-control" disabled>`;
            break;
        case 'TEXTAREA':
            html += `<textarea class="form-control" rows="3" placeholder="${campo.placeholder || ''}" disabled></textarea>`;
            break;
        case 'SELECT':
            html += `<select class="form-select" disabled>`;
            html += `<option>${campo.placeholder || 'Selecione...'}</option>`;
            if (campo.choices && campo.choices.length > 0) {
                campo.choices.forEach(function(choice) {
                    html += `<option>${choice}</option>`;
                });
            }
            html += `</select>`;
            break;
        case 'CHECKBOX':
            html += `<div class="form-check"><input type="checkbox" class="form-check-input" disabled><label class="form-check-label">${campo.label}</label></div>`;
            break;
        case 'MULTISELECTOR':
            html += `<select class="form-select" disabled>`;
            html += `<option>${campo.placeholder || 'Selecione...'}</option>`;
            if (campo.choices && campo.choices.length > 0) {
                campo.choices.forEach(function(choice) {
                    html += `<option>${choice}</option>`;
                });
            }
            html += `</select>`;
            break;
        case 'FILE':
            html += `<input type="file" class="form-control" disabled>`;
            html += `<small class="text-muted">Upload de arquivo único</small>`;
            break;
        case 'MULTIFILE':
            html += `<input type="file" class="form-control" multiple disabled>`;
            html += `<small class="text-muted">Upload de múltiplos arquivos</small>`;
            break;
        case 'MULTIINPUT':
            const subCamposPreview = campo.choices || [];
            if (subCamposPreview.length === 0) {
                html += `<div class="alert alert-warning">MULTIINPUT sem sub-campos definidos</div>`;
                break;
            }
            
            const campoIdPreview = campo.id ? campo.id.toString() : campo.label.replace(/\s+/g, '_').toLowerCase();
            const subCamposJson = JSON.stringify(subCamposPreview).replace(/"/g, '&quot;');
            
            html += `<div class="multiinput-preview-container mt-2">`;
            html += `<div id="multiinput_preview_${campoIdPreview}_container">`;
            // Primeira linha (exemplo)
            html += `<div class="multiinput-item-preview border rounded p-3 mb-2 bg-light">`;
            html += `<div class="d-flex align-items-center gap-2 flex-wrap">`;
            subCamposPreview.forEach(function(subCampo, index) {
                const label = subCampo.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `<div class="flex-grow-1" style="min-width: 150px;">`;
                html += `<label class="form-label small mb-1">${label}:</label>`;
                html += `<input type="text" class="form-control form-control-sm" placeholder="${label}" disabled>`;
                html += `</div>`;
                if (index < subCamposPreview.length - 1) {
                    html += `<span class="text-muted align-self-end mb-2">|</span>`;
                }
            });
            html += `<div class="ms-auto">`;
            html += `<button type="button" class="btn btn-sm btn-danger" disabled><i class="bx bx-x"></i></button>`;
            html += `</div>`;
            html += `</div></div>`;
            html += `</div>`;
            html += `<button type="button" class="btn btn-sm btn-primary" onclick="adicionarMultiInputPreview('${campoIdPreview}', ${subCamposJson})">`;
            html += `<i class="bx bx-plus"></i> Adicionar Contrato`;
            html += `</button>`;
            html += `</div>`;
            break;
        default:
            html += `<input type="text" class="form-control" placeholder="${campo.placeholder || ''}" disabled>`;
    }
    
    html += `</div>`;
    return html;
}

function adicionarMultiInputPreview(campoId, subCampos) {
    const container = $(`#multiinput_preview_${campoId}_container`);
    let html = `<div class="multiinput-item-preview border rounded p-3 mb-2 bg-light">`;
    html += `<div class="d-flex align-items-center gap-2 flex-wrap">`;
    subCampos.forEach(function(subCampo, index) {
        const label = subCampo.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += `<div class="flex-grow-1" style="min-width: 150px;">`;
        html += `<label class="form-label small mb-1">${label}:</label>`;
        html += `<input type="text" class="form-control form-control-sm" placeholder="${label}" disabled>`;
        html += `</div>`;
        if (index < subCampos.length - 1) {
            html += `<span class="text-muted align-self-end mb-2">|</span>`;
        }
    });
    html += `<div class="ms-auto">`;
    html += `<button type="button" class="btn btn-sm btn-danger" disabled><i class="bx bx-x"></i></button>`;
    html += `</div>`;
    html += `</div></div>`;
    container.append(html);
}

function ativarSchemaParaBanco(bancoId, convenioOperacaoId, titulo) {
    if (!confirm(`Deseja ativar o schema "${titulo}" para este banco?\n\nIsso irá desativar outros schemas da mesma operação para este banco.`)) {
        return;
    }
    
    $.ajax({
        url: '/operacional/contratos/api/ativar-banco-convenio-operacao/',
        method: 'POST',
        data: {
            banco_id: bancoId,
            convenio_operacao_id: convenioOperacaoId,
            csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                alert('Schema ativado com sucesso!');
                location.reload();
            } else {
                alert('Erro ao ativar: ' + response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao ativar schema:', xhr.responseText);
            alert('Erro ao ativar schema');
        }
    });
}

function desativarSchemaParaBanco(bancoId, convenioOperacaoId) {
    if (!confirm('Deseja desativar este schema para este banco?')) {
        return;
    }
    
    $.ajax({
        url: '/operacional/contratos/api/desativar-banco-convenio-operacao/',
        method: 'POST',
        data: {
            banco_id: bancoId,
            convenio_operacao_id: convenioOperacaoId,
            csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                alert('Schema desativado com sucesso!');
                location.reload();
            } else {
                alert('Erro ao desativar: ' + response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao desativar schema:', xhr.responseText);
            alert('Erro ao desativar schema');
        }
    });
}

function confirmarAtivacao() {
    const convenioOperacaoId = $('#modalPreviewSchema').data('convenio-operacao-id');
    
    if (!bancoSelecionadoId || !convenioOperacaoId) {
        alert('Erro: Dados incompletos. Selecione um banco e schema.');
        return;
    }
    
    $.ajax({
        url: '/operacional/contratos/api/ativar-banco-convenio-operacao/',
        method: 'POST',
        data: {
            banco_id: bancoSelecionadoId,
            convenio_operacao_id: convenioOperacaoId,
            csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                alert('Schema ativado com sucesso para este banco!');
                $('#modalPreviewSchema').modal('hide');
                location.reload();
            } else {
                alert('Erro ao ativar: ' + response.message);
            }
        },
        error: function(xhr) {
            console.error('Erro ao ativar:', xhr.responseText);
            alert('Erro ao ativar schema');
        }
    });
}
