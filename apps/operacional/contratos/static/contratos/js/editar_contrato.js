/**
 * JavaScript para editar contrato - Sistema de Wizard com Páginas
 * Carrega dados existentes e permite edição
 */

let contratoIdAtual = null;
let convenioOperacaoIdAtual = null;
let bancoIdAtual = null;

// Sistema de páginas/wizard
let paginaAtual = 1;
let totalPaginas = 1;
let camposCarregados = [];
let dadosContratoAtual = {};

$(document).ready(function() {
    const container = $('#editar-container');
    contratoIdAtual = container.data('contrato-id');
    
    if (contratoIdAtual) {
        carregarContrato();
    }
    
    // Botão de avançar/enviar
    $('#btn-avancar').on('click', function() {
        avancarPagina();
    });
});

function voltarParaCRM() {
    window.location.href = '/operacional/contratos/acompanhamento-crm/';
}

function carregarContrato() {
    const container = $('#editar-container');
    const urlContrato = container.data('url-contrato');
    
    $.ajax({
        url: urlContrato,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const contrato = response.data;
                
                // Guardar dados atuais
                dadosContratoAtual = contrato.dados_contrato || {};
                bancoIdAtual = contrato.banco_id;
                convenioOperacaoIdAtual = contrato.convenio_operacao_id;
                
                // Preencher info do produto
                $('#info-banco').text(contrato.banco_nome);
                $('#info-convenio').text(contrato.convenio_nome);
                $('#info-operacao').text(contrato.operacao_nome);
                $('#banco_id').val(contrato.banco_id);
                $('#convenio_operacao_id').val(contrato.convenio_operacao_id);
                
                // Mostrar pendências se houver
                if (contrato.observacoes_incompleto) {
                    $('#texto-pendencias').text(contrato.observacoes_incompleto);
                    $('#alert-pendencias').show();
                }
                
                // Carregar campos do schema
                carregarCampos(contrato.convenio_operacao_id);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao carregar contrato');
        }
    });
}

function carregarCampos(convenioOperacaoId) {
    console.log('Carregando campos para convenio_operacao_id:', convenioOperacaoId);
    
    $.ajax({
        url: '/operacional/contratos/api/schema/campos/',
        method: 'GET',
        data: { convenio_operacao_id: convenioOperacaoId },
        success: function(response) {
            console.log('Resposta da API de campos:', response);
            
            if (response.success) {
                // A API retorna 'data' como array e 'total_paginas' na raiz
                camposCarregados = response.data || [];
                totalPaginas = response.total_paginas || 1;
                
                console.log('Campos carregados:', camposCarregados.length, 'Total páginas:', totalPaginas);
                
                if (camposCarregados.length > 0) {
                    // Mapear campos para formato esperado (categoria, label, etc.)
                    camposCarregados = camposCarregados.map(campo => ({
                        id: campo.id,
                        categoria: campo.category || campo.categoria,
                        label: campo.label,
                        tipo: campo.type || campo.tipo,
                        choices: campo.choices,
                        placeholder: campo.placeholder,
                        obrigatorio: campo.required || campo.obrigatorio,
                        ordem: campo.ordem || 0,
                        pagina: campo.pagina || 1
                    }));
                    
                    paginaAtual = 1;
                    renderizarPaginas();
                    $('#campos-formulario').show();
                    $('#stepper-container').show();
                    $('#btn-avancar').show();
                } else {
                    alert('Nenhum campo encontrado para este schema');
                }
            } else {
                alert('Erro: ' + (response.message || 'Erro ao carregar campos'));
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar campos do schema:', xhr);
            alert('Erro ao carregar campos do schema');
        }
    });
}

function renderizarPaginas() {
    console.log('Renderizando página', paginaAtual, 'de', totalPaginas);
    console.log('Total de campos:', camposCarregados.length);
    
    // Filtrar campos da página atual (converter para número para comparação)
    const camposPagina = camposCarregados.filter(c => parseInt(c.pagina) === paginaAtual);
    console.log('Campos na página', paginaAtual, ':', camposPagina.length);
    
    // Agrupar por categoria
    const categorias = {};
    camposPagina.forEach(campo => {
        const cat = campo.categoria || 'outros';
        if (!categorias[cat]) {
            categorias[cat] = [];
        }
        categorias[cat].push(campo);
    });
    
    // Ordenar categorias pelo menor ordem dos seus campos
    const categoriasOrdenadas = Object.entries(categorias).sort((a, b) => {
        const minOrdemA = Math.min(...a[1].map(c => c.ordem));
        const minOrdemB = Math.min(...b[1].map(c => c.ordem));
        return minOrdemA - minOrdemB;
    });
    
    // Gerar HTML
    let html = `
        <div class="card mb-4">
            <div class="card-header bg-dark text-white">
                <h5 class="mb-0"><i class="bx bx-file me-2"></i>Página ${paginaAtual} de ${totalPaginas}</h5>
            </div>
            <div class="card-body">`;
    
    categoriasOrdenadas.forEach(([categoria, campos]) => {
        // Ordenar campos por ordem
        campos.sort((a, b) => a.ordem - b.ordem);
        
        html += `<div class="categoria-campos mb-4">
            <h4 class="mb-3">${categoria.toUpperCase().replace(/_/g, ' ')}</h4>
            <div class="row">`;
        
        campos.forEach(campo => {
            html += renderizarCampo(campo);
        });
        
        html += '</div></div>';
    });
    
    html += '</div></div>';
    
    $('#campos-formulario').html(html);
    
    // Atualizar stepper
    atualizarStepper();
    
    // Atualizar botão
    atualizarBotaoAvancar();
    
    // Preencher valores existentes
    preencherValoresExistentes();
}

function preencherValoresExistentes() {
    if (!dadosContratoAtual) return;
    
    console.log('Preenchendo valores existentes:', dadosContratoAtual);
    
    // Percorrer dados e preencher campos
    for (const [categoria, campos] of Object.entries(dadosContratoAtual)) {
        if (typeof campos === 'object' && campos !== null && !Array.isArray(campos)) {
            for (const [campo, valor] of Object.entries(campos)) {
                const input = $(`[name="${categoria}__${campo}"]`);
                
                if (input.length === 0) {
                    // Pode ser MultiInput - verificar container
                    const multiContainer = $(`[id^="multiinput_"][id$="_container"]`).filter(function() {
                        return $(this).find(`[name="${categoria}__${campo}[]"]`).length > 0;
                    });
                    
                    if (multiContainer.length > 0 && Array.isArray(valor)) {
                        preencherMultiInput(multiContainer, categoria, campo, valor);
                    }
                    continue;
                }
                
                const tipo = input.attr('type');
                
                if (tipo === 'checkbox') {
                    input.prop('checked', valor === true || valor === 'true' || valor === '1');
                } else if (input.is('select')) {
                    input.val(valor);
                } else if (tipo === 'file') {
                    // Não preencher arquivos - apenas mostrar que já existe
                    if (valor && typeof valor === 'string' && valor.startsWith('/media/')) {
                        const container = input.closest('.mb-3');
                        const nomeArquivo = valor.split('/').pop();
                        container.find('.text-muted').html(`
                            <span class="text-success"><i class="bx bx-check"></i> Arquivo salvo: ${nomeArquivo}</span>
                            <a href="${valor}" target="_blank" class="ms-2"><i class="bx bx-link-external"></i></a>
                        `);
                    }
                } else {
                    input.val(valor);
                }
            }
        }
    }
}

function preencherMultiInput(container, categoria, campo, valores) {
    if (!Array.isArray(valores) || valores.length === 0) return;
    
    // Limpar itens existentes (manter só um)
    const items = container.find('.multiinput-item');
    if (items.length > 1) {
        items.slice(1).remove();
    }
    
    // Preencher primeiro item
    const primeiroItem = items.first();
    if (valores.length > 0 && typeof valores[0] === 'object') {
        for (const [subKey, subVal] of Object.entries(valores[0])) {
            primeiroItem.find(`[data-subcampo="${subKey}"]`).val(subVal);
        }
    }
    
    // Adicionar e preencher itens adicionais
    for (let i = 1; i < valores.length; i++) {
        const btn = container.next('button');
        if (btn.length) {
            btn.click(); // Simular clique para adicionar novo item
            
            // Preencher o novo item
            setTimeout(() => {
                const novoItem = container.find('.multiinput-item').last();
                if (typeof valores[i] === 'object') {
                    for (const [subKey, subVal] of Object.entries(valores[i])) {
                        novoItem.find(`[data-subcampo="${subKey}"]`).val(subVal);
                    }
                }
            }, 50);
        }
    }
}

function renderizarCampo(campo) {
    const tipo = campo.tipo.toUpperCase();
    const required = campo.obrigatorio ? 'required' : '';
    const requiredMark = campo.obrigatorio ? '<span class="text-danger">*</span>' : '';
    const placeholder = campo.placeholder || '';
    const nameBase = `${campo.categoria}__${campo.label}`;
    const fieldId = `campo_${campo.id}`;
    
    // Largura do campo
    let colClass = 'col-md-6';
    if (['TEXTAREA', 'MULTIINPUT'].includes(tipo)) {
        colClass = 'col-md-12';
    }
    
    let html = '';
    
    switch (tipo) {
        case 'TEXT':
        case 'EMAIL':
        case 'TEL':
        case 'NUMBER':
        case 'DECIMAL':
        case 'DATE':
        case 'PASSWORD':
            const inputType = tipo === 'DECIMAL' ? 'number' : tipo.toLowerCase();
            const step = tipo === 'DECIMAL' ? '0.01' : (tipo === 'NUMBER' ? '1' : '');
            html = `
            <div class="${colClass} mb-3">
                <label for="${fieldId}" class="form-label">${campo.label.replace(/_/g, ' ')} ${requiredMark}</label>
                <input type="${inputType}" class="form-control" id="${fieldId}" name="${nameBase}" 
                       ${required} placeholder="${placeholder}" ${step ? 'step="' + step + '"' : ''}>
            </div>`;
            break;
            
        case 'SELECT':
        case 'MULTISELECTOR':
            const isMultiple = tipo === 'MULTISELECTOR' ? 'multiple' : '';
            let options = '<option value="">Selecione...</option>';
            if (campo.choices) {
                const choicesList = campo.choices.split(',').map(c => c.trim()).filter(c => c);
                choicesList.forEach(choice => {
                    options += `<option value="${choice}">${choice}</option>`;
                });
            }
            html = `
            <div class="${colClass} mb-3">
                <label for="${fieldId}" class="form-label">${campo.label.replace(/_/g, ' ')} ${requiredMark}</label>
                <select class="form-select" id="${fieldId}" name="${nameBase}" ${required} ${isMultiple}>
                    ${options}
                </select>
            </div>`;
            break;
            
        case 'TEXTAREA':
            html = `
            <div class="${colClass} mb-3">
                <label for="${fieldId}" class="form-label">${campo.label.replace(/_/g, ' ')} ${requiredMark}</label>
                <textarea class="form-control" id="${fieldId}" name="${nameBase}" ${required} 
                          placeholder="${placeholder}" rows="3"></textarea>
            </div>`;
            break;
            
        case 'CHECKBOX':
            html = `
            <div class="${colClass} mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="${fieldId}" name="${nameBase}" ${required}>
                    <label class="form-check-label" for="${fieldId}">
                        ${campo.label.replace(/_/g, ' ')} ${requiredMark}
                    </label>
                </div>
            </div>`;
            break;
            
        case 'FILE':
        case 'MULTIFILE':
            const isMultipleFile = tipo === 'MULTIFILE' ? 'multiple' : '';
            html = `
            <div class="${colClass} mb-3">
                <label for="${fieldId}" class="form-label">${campo.label.replace(/_/g, ' ')} ${requiredMark}</label>
                <input type="file" class="form-control" id="${fieldId}" name="${nameBase}" ${isMultipleFile}>
                <small class="text-muted">Upload de arquivo${tipo === 'MULTIFILE' ? 's' : ''}</small>
            </div>`;
            break;
            
        case 'MULTIINPUT':
            const subCampos = campo.choices ? campo.choices.split(';').map(c => c.trim()).filter(c => c) : [];
            html = `
            <div class="col-md-12 mb-4">
                <label class="form-label fw-bold">${campo.label.replace(/_/g, ' ')} ${requiredMark}</label>
                <div id="multiinput_${campo.id}_container">
                    ${renderizarMultiInputItem(campo.id, nameBase, subCampos)}
                </div>
                <button type="button" class="btn btn-sm btn-primary" onclick="adicionarMultiInputItem('${campo.id}', '${nameBase}', ${JSON.stringify(subCampos).replace(/"/g, '&quot;')})">
                    <i class="bx bx-plus"></i> Adicionar Item
                </button>
            </div>`;
            break;
            
        default:
            html = `
            <div class="${colClass} mb-3">
                <label for="${fieldId}" class="form-label">${campo.label.replace(/_/g, ' ')} ${requiredMark}</label>
                <input type="text" class="form-control" id="${fieldId}" name="${nameBase}" 
                       ${required} placeholder="${placeholder}">
            </div>`;
    }
    
    return html;
}

function renderizarMultiInputItem(campoId, campoName, subCampos) {
    let html = `<div class="multiinput-item border rounded p-3 mb-2">
        <div class="d-flex align-items-center gap-2 flex-wrap">`;
    
    subCampos.forEach((sub, idx) => {
        const subLabel = sub.charAt(0).toUpperCase() + sub.slice(1).replace(/_/g, ' ');
        html += `<div class="flex-grow-1" style="min-width: 150px;">
                    <label class="form-label small mb-1">${subLabel}:</label>
                    <input type="text" class="form-control form-control-sm" name="${campoName}[]" data-subcampo="${sub}" placeholder="${subLabel}"></div>`;
        if (idx < subCampos.length - 1) {
            html += `<span class="text-muted align-self-end mb-2">|</span>`;
        }
    });
    
    html += `<div class="ms-auto">
                <button type="button" class="btn btn-sm btn-danger" onclick="removerMultiInputItem('${campoId}', this)">
                    <i class="bx bx-x"></i>
                </button>
            </div></div></div>`;
    
    return html;
}

function adicionarMultiInputItem(campoId, campoName, subCampos) {
    const container = $(`#multiinput_${campoId}_container`);
    container.append(renderizarMultiInputItem(campoId, campoName, subCampos));
}

function removerMultiInputItem(campoId, btn) {
    const container = $(`#multiinput_${campoId}_container`);
    if (container.children().length > 1) {
        $(btn).closest('.multiinput-item').remove();
    } else {
        alert('É necessário manter pelo menos um item');
    }
}

function atualizarStepper() {
    const progresso = (paginaAtual / totalPaginas) * 100;
    
    $('#progress-bar')
        .css('width', progresso + '%')
        .attr('aria-valuenow', progresso)
        .text(`Etapa ${paginaAtual} de ${totalPaginas}`);
    
    $('#badge-pagina').text(`Etapa ${paginaAtual} de ${totalPaginas}`);
}

function atualizarBotaoAvancar() {
    const btn = $('#btn-avancar');
    
    if (paginaAtual < totalPaginas) {
        btn.html('Próximo <i class="bx bx-right-arrow-alt ms-2"></i>');
    } else {
        btn.html('<i class="bx bx-check me-2"></i>Salvar e Reenviar');
    }
}

function avancarPagina() {
    // Validar campos obrigatórios da página atual
    const camposPagina = camposCarregados.filter(c => parseInt(c.pagina) === paginaAtual);
    let valido = true;
    
    for (const campo of camposPagina) {
        if (campo.obrigatorio) {
            const nameBase = `${campo.categoria}__${campo.label}`;
            const input = $(`[name="${nameBase}"]`);
            
            if (input.attr('type') === 'file') continue;
            
            if (input.attr('type') === 'checkbox') {
                if (!input.is(':checked')) {
                    valido = false;
                    input.addClass('is-invalid');
                } else {
                    input.removeClass('is-invalid');
                }
            } else {
                if (!input.val() || input.val().trim() === '') {
                    valido = false;
                    input.addClass('is-invalid');
                } else {
                    input.removeClass('is-invalid');
                }
            }
        }
    }
    
    if (!valido) {
        alert('Por favor, preencha todos os campos obrigatórios');
        return;
    }
    
    // Salvar dados da página atual
    salvarDadosPagina();
    
    if (paginaAtual < totalPaginas) {
        // Ir para próxima página
        paginaAtual++;
        renderizarPaginas();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        // Última página - enviar contrato atualizado
        enviarContratoAtualizado();
    }
}

function salvarDadosPagina() {
    const camposPagina = camposCarregados.filter(c => parseInt(c.pagina) === paginaAtual);
    
    camposPagina.forEach(campo => {
        const nameBase = `${campo.categoria}__${campo.label}`;
        const categoria = campo.categoria;
        const label = campo.label;
        const input = $(`[name="${nameBase}"]`);
        
        if (!dadosContratoAtual[categoria]) {
            dadosContratoAtual[categoria] = {};
        }
        
        if (input.attr('type') === 'checkbox') {
            dadosContratoAtual[categoria][label] = input.is(':checked');
        } else if (campo.tipo.toUpperCase() === 'MULTIINPUT') {
            // Coletar multi-inputs
            const items = [];
            $(`[name="${nameBase}[]"]`).closest('.multiinput-item').each(function() {
                const item = {};
                $(this).find('input').each(function() {
                    const subcampo = $(this).data('subcampo');
                    item[subcampo] = $(this).val();
                });
                if (Object.values(item).some(v => v)) {
                    items.push(item);
                }
            });
            dadosContratoAtual[categoria][label] = items;
        } else if (input.attr('type') === 'file') {
            // Arquivos serão tratados no envio
        } else {
            dadosContratoAtual[categoria][label] = input.val();
        }
    });
}

function enviarContratoAtualizado() {
    const btn = $('#btn-avancar');
    btn.prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin me-2"></i>Salvando...');
    
    // Coletar arquivos
    const formData = new FormData();
    formData.append('dados_contrato', JSON.stringify(dadosContratoAtual));
    formData.append('finalizar', 'true'); // Marca que está finalizando
    
    // Adicionar arquivos
    $('input[type="file"]').each(function() {
        const files = this.files;
        const name = $(this).attr('name');
        for (let i = 0; i < files.length; i++) {
            formData.append(name, files[i]);
        }
    });
    
    const container = $('#editar-container');
    const urlAtualizar = container.data('url-atualizar');
    
    $.ajax({
        url: urlAtualizar,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            btn.prop('disabled', false);
            
            if (response.success) {
                alert('Contrato atualizado com sucesso! O contrato foi reenviado para análise.');
                window.location.href = '/operacional/contratos/acompanhamento-crm/';
            } else {
                alert('Erro: ' + response.message);
                atualizarBotaoAvancar();
            }
        },
        error: function(xhr) {
            btn.prop('disabled', false);
            atualizarBotaoAvancar();
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao atualizar contrato'));
        }
    });
}
