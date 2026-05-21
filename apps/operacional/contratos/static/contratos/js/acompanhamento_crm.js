/**
 * Acompanhamento CRM - Kanban de Contratos
 * Sistema com SSE para atualizações em tempo real
 */

// URLs dinâmicas carregadas dos data-attributes
let URLS = {
    kanban: '',
    tabulacoes: '',
    mover: '',
    sse: ''
};

// Estado da aplicação
let sseConectado = false;
let sseReader = null;
let tabulacoesCache = [];

$(document).ready(function() {
    const container = $('#crm-container');
    URLS.kanban = container.data('url-kanban');
    URLS.tabulacoes = container.data('url-tabulacoes');
    URLS.mover = container.data('url-mover');
    URLS.sse = container.data('url-sse');
    
    // Carregar tabulações primeiro, depois o kanban
    carregarTabulacoes().then(() => {
        carregarKanban();
        iniciarSSE();
    });
});

// ==================== SSE ====================

function iniciarSSE() {
    if (!URLS.sse) {
        console.warn('URL SSE não configurada');
        return;
    }
    
    atualizarStatusSSE('conectando');
    
    fetch(URLS.sse)
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro na conexão SSE');
        }
        
        sseConectado = true;
        atualizarStatusSSE('conectado');
        
        sseReader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        function processarChunk() {
            sseReader.read().then(({ done, value }) => {
                if (done) {
                    sseConectado = false;
                    atualizarStatusSSE('desconectado');
                    // Tentar reconectar após 5 segundos
                    setTimeout(iniciarSSE, 5000);
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
                console.error('Erro ao ler stream SSE:', err);
                sseConectado = false;
                atualizarStatusSSE('erro');
                // Tentar reconectar após 5 segundos
                setTimeout(iniciarSSE, 5000);
            });
        }
        
        processarChunk();
    })
    .catch(err => {
        console.error('Erro SSE:', err);
        sseConectado = false;
        atualizarStatusSSE('erro');
        // Tentar reconectar após 5 segundos
        setTimeout(iniciarSSE, 5000);
    });
}

function processarEventoSSE(dados) {
    switch (dados.etapa) {
        case 'conectado':
            console.log('SSE conectado:', dados.mensagem);
            break;
        case 'heartbeat':
            // Heartbeat - manter conexão
            break;
        case 'atualizado':
            // Contrato foi atualizado - atualizar no kanban
            if (dados.contrato) {
                atualizarCardKanban(dados.contrato);
            }
            break;
        case 'erro':
            console.error('Erro SSE:', dados.mensagem);
            break;
    }
}

function atualizarStatusSSE(status) {
    const badge = $('#sse-status');
    badge.removeClass('bg-success bg-danger bg-warning bg-secondary');
    
    switch (status) {
        case 'conectado':
            badge.addClass('bg-success').html('<i class="bx bx-radio-circle-marked me-1"></i> Conectado');
            break;
        case 'conectando':
            badge.addClass('bg-warning').html('<i class="bx bx-loader-alt bx-spin me-1"></i> Conectando...');
            break;
        case 'desconectado':
            badge.addClass('bg-secondary').html('<i class="bx bx-radio-circle me-1"></i> Desconectado');
            break;
        case 'erro':
            badge.addClass('bg-danger').html('<i class="bx bx-error-circle me-1"></i> Erro');
            break;
    }
}

function atualizarCardKanban(contrato) {
    // Encontrar o card existente
    const cardExistente = $(`.kanban-card[data-contrato-id="${contrato.id}"]`);
    
    if (cardExistente.length) {
        const tabulacaoAtualId = cardExistente.closest('.kanban-body').data('tab-id');
        
        if (tabulacaoAtualId != contrato.tabulacao_id) {
            // Card mudou de tabulação - mover
            cardExistente.remove();
            const novoBody = $(`.kanban-body[data-tab-id="${contrato.tabulacao_id}"]`);
            novoBody.find('.text-muted.text-center').remove();
            novoBody.prepend(criarCardHTML(contrato));
            
            // Atualizar contadores
            atualizarContadores();
        } else {
            // Apenas atualizar dados do card
            cardExistente.replaceWith(criarCardHTML(contrato));
        }
    } else {
        // Novo card - adicionar na tabulação correta
        const body = $(`.kanban-body[data-tab-id="${contrato.tabulacao_id}"]`);
        body.find('.text-muted.text-center').remove();
        body.prepend(criarCardHTML(contrato));
        atualizarContadores();
    }
    
    // Reconfigurar drag and drop
    configurarDragAndDrop();
}

function atualizarContadores() {
    $('.kanban-body').each(function() {
        const count = $(this).find('.kanban-card').length;
        $(this).siblings('.kanban-header').find('.badge').text(count);
    });
}

// ==================== KANBAN ====================

function carregarTabulacoes() {
    return new Promise((resolve, reject) => {
        if (!URLS.tabulacoes) {
            resolve();
            return;
        }
        
        $.ajax({
            url: URLS.tabulacoes,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    tabulacoesCache = response.data;
                }
                resolve();
            },
            error: function() {
                resolve();
            }
        });
    });
}

function carregarKanban() {
    if (!URLS.kanban) {
        console.error('URL do kanban não configurada');
        return;
    }
    
    $.ajax({
        url: URLS.kanban,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderizarKanban(response.data);
            } else {
                console.error('Erro ao carregar kanban:', response.message);
                $('#kanban-container').html('<div class="alert alert-danger">Erro ao carregar contratos</div>');
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar kanban');
            $('#kanban-container').html('<div class="alert alert-danger">Erro ao conectar com o servidor</div>');
        }
    });
}

function renderizarKanban(data) {
    let tabulacoes;
    if (Array.isArray(data)) {
        tabulacoes = data;
    } else {
        tabulacoes = Object.values(data);
    }
    tabulacoes = tabulacoes.sort((a, b) => a.ordem - b.ordem);
    
    let html = '<div class="kanban-board">';
    
    tabulacoes.forEach(function(tab) {
        const contratos = tab.contratos || [];
        
        html += `
        <div class="kanban-coluna" data-tab-id="${tab.id}">
            <div class="kanban-header" style="background-color: ${tab.cor};">
                <span class="kanban-header-nome">${escapeHtml(tab.nome)}</span>
                <span class="badge bg-light text-dark">${contratos.length}</span>
            </div>
            <div class="kanban-body" data-tab-id="${tab.id}">`;
        
        if (contratos.length === 0) {
            html += '<p class="text-muted text-center mt-3 mb-0">Nenhum contrato</p>';
        } else {
            contratos.forEach(function(contrato) {
                html += criarCardHTML(contrato, tab);
            });
        }
        
        html += '</div></div>';
    });
    
    html += '</div>';
    $('#kanban-container').html(html);
    
    configurarDragAndDrop();
}

function criarCardHTML(contrato, tab) {
    const tabulacaoNome = tab ? tab.nome : (contrato.tabulacao_nome || '');
    
    // Verificar se precisa de ação especial baseado na tabulação
    let botoesEspeciais = '';
    
    // LINK DE FORMALIZACAO - mostrar modal com link e botão confirmar
    if (tabulacaoNome.toUpperCase().includes('LINK DE FORMALIZACAO') || tabulacaoNome.toUpperCase().includes('LINK DE FORMALIZAÇÃO')) {
        if (contrato.link_formalizacao) {
            botoesEspeciais = `
                <button class="btn btn-sm btn-primary w-100 mt-2" onclick="abrirModalLinkFormalizacao(${contrato.id}, '${escapeHtml(contrato.link_formalizacao)}')">
                    <i class="bx bx-link me-1"></i> Ver Link / Confirmar Assinatura
                </button>`;
        }
    }
    
    // SOLICITACAO DE VIDEO - mostrar modal para upload
    if (tabulacaoNome.toUpperCase().includes('SOLICITACAO DE VIDEO') || tabulacaoNome.toUpperCase().includes('SOLICITAÇÃO DE VÍDEO')) {
        botoesEspeciais = `
            <button class="btn btn-sm btn-warning w-100 mt-2" onclick="abrirModalUploadVideo(${contrato.id})">
                <i class="bx bx-video me-1"></i> Enviar Vídeo do Cliente
            </button>`;
    }
    
    // VIDEO ANEXADO - mostrar botão para ver vídeo
    if (tabulacaoNome.toUpperCase().includes('VIDEO ANEXADO') || tabulacaoNome.toUpperCase().includes('VÍDEO ANEXADO')) {
        if (contrato.video_cliente) {
            botoesEspeciais = `
                <button class="btn btn-sm btn-info w-100 mt-2" onclick="abrirModalVerVideo('${contrato.video_cliente}')">
                    <i class="bx bx-play-circle me-1"></i> Ver Vídeo
                </button>`;
        }
    }
    
    // INCOMPLETO - mostrar observações
    let obsIncompleto = '';
    if (tabulacaoNome.toUpperCase() === 'INCOMPLETO' && contrato.observacoes_incompleto) {
        obsIncompleto = `
            <div class="alert alert-warning py-1 px-2 mb-2 small">
                <i class="bx bx-error me-1"></i>${escapeHtml(contrato.observacoes_incompleto)}
            </div>`;
    }
    
    return `
    <div class="kanban-card" data-contrato-id="${contrato.id}" draggable="true">
        <div class="kanban-card-header">
            <h6 class="mb-0">${escapeHtml(contrato.cliente_nome || 'N/A')}</h6>
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">#${contrato.id}</small>
                <span class="badge bg-primary">${escapeHtml(contrato.numero_serie || 'N/A')}</span>
            </div>
        </div>
        ${obsIncompleto}
        <div class="kanban-card-body">
            <div class="card-info">
                <i class="bx bx-building"></i>
                <span>${escapeHtml(contrato.banco_nome || 'N/A')}</span>
            </div>
            <div class="card-info">
                <i class="bx bx-file"></i>
                <span>${escapeHtml(contrato.convenio_nome || '')} - ${escapeHtml(contrato.operacao_nome || '')}</span>
            </div>
            <div class="card-info">
                <i class="bx bx-money"></i>
                <span>R$ ${formatarValor(contrato.valor_operacao)}</span>
            </div>
            <div class="card-info">
                <i class="bx bx-user"></i>
                <span>${escapeHtml(contrato.vendedor_nome || 'N/A')}</span>
            </div>
            <div class="card-info text-muted">
                <i class="bx bx-time"></i>
                <span>${contrato.data_criacao || ''}</span>
            </div>
        </div>
        <div class="kanban-card-footer">
            ${contrato.cliente_formalizou ? '<span class="badge bg-success me-1"><i class="bx bx-check"></i> Formalizou</span>' : ''}
            ${contrato.video_cliente ? '<span class="badge bg-info me-1"><i class="bx bx-video"></i> Vídeo</span>' : ''}
        </div>
        ${botoesEspeciais}
        <button class="btn btn-sm btn-outline-secondary w-100 mt-2" onclick="verDetalhesContrato(${contrato.id})">
            <i class="bx bx-show me-1"></i> Ver Detalhes
        </button>
    </div>`;
}

function configurarDragAndDrop() {
    $('.kanban-card').off('dragstart dragend');
    $('.kanban-body').off('dragover dragleave drop');
    
    $('.kanban-card').on('dragstart', function(e) {
        $(this).addClass('dragging');
        e.originalEvent.dataTransfer.setData('text/plain', $(this).data('contrato-id'));
        e.originalEvent.dataTransfer.effectAllowed = 'move';
    });
    
    $('.kanban-card').on('dragend', function() {
        $(this).removeClass('dragging');
        $('.kanban-body').removeClass('drag-over');
    });
    
    $('.kanban-body').on('dragover', function(e) {
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'move';
        $(this).addClass('drag-over');
    });
    
    $('.kanban-body').on('dragleave', function() {
        $(this).removeClass('drag-over');
    });
    
    $('.kanban-body').on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('drag-over');
        
        const contratoId = e.originalEvent.dataTransfer.getData('text/plain');
        const novaTabulacaoId = $(this).data('tab-id');
        
        moverContrato(contratoId, novaTabulacaoId);
    });
}

function moverContrato(contratoId, novaTabulacaoId) {
    $.ajax({
        url: URLS.mover || '/operacional/contratos/api/contratos/mover/',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            contrato_id: parseInt(contratoId),
            nova_tabulacao_id: parseInt(novaTabulacaoId)
        }),
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        success: function(response) {
            if (response.success) {
                carregarKanban();
            } else {
                alert('Erro: ' + response.message);
                carregarKanban();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao mover contrato: ' + (response.message || 'Erro desconhecido'));
            carregarKanban();
        }
    });
}

// ==================== MODAIS ====================

function verDetalhesContrato(contratoId) {
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                mostrarModalDetalhes(response.data);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao carregar detalhes do contrato');
        }
    });
}

// Armazenar contrato atual para edição
let contratoAtual = null;

function formatarValorCampo(campo, valor) {
    if (valor === null || valor === undefined || valor === '') {
        return '<span class="text-muted">N/A</span>';
    }
    
    // Verificar se é um array (MultiInput)
    if (Array.isArray(valor)) {
        if (valor.length === 0) return '<span class="text-muted">Nenhum item</span>';
        
        let html = '<div class="multi-input-display">';
        valor.forEach((item, idx) => {
            if (typeof item === 'object' && item !== null) {
                html += `<div class="border rounded p-2 mb-2 bg-light">`;
                html += `<small class="text-muted">Item ${idx + 1}</small><br>`;
                for (const [key, val] of Object.entries(item)) {
                    html += `<span class="me-3"><strong>${escapeHtml(key)}:</strong> ${escapeHtml(val || 'N/A')}</span>`;
                }
                html += `</div>`;
            } else {
                html += `<span class="badge bg-secondary me-1">${escapeHtml(item)}</span>`;
            }
        });
        html += '</div>';
        return html;
    }
    
    // Verificar se é um objeto (MultiInput único)
    if (typeof valor === 'object' && valor !== null) {
        let html = '<div class="border rounded p-2 bg-light">';
        for (const [key, val] of Object.entries(valor)) {
            html += `<span class="me-3"><strong>${escapeHtml(key)}:</strong> ${escapeHtml(val || 'N/A')}</span>`;
        }
        html += '</div>';
        return html;
    }
    
    // Verificar se é um arquivo (começa com /media/ ou é URL)
    const valorStr = String(valor);
    if (valorStr.startsWith('/media/') || valorStr.startsWith('http')) {
        const nomeArquivo = valorStr.split('/').pop();
        const extensao = nomeArquivo.split('.').pop().toLowerCase();
        const isImagem = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extensao);
        
        if (isImagem) {
            return `
                <div class="d-flex align-items-center gap-2">
                    <a href="${escapeHtml(valorStr)}" target="_blank" class="btn btn-sm btn-outline-primary">
                        <i class="bx bx-image me-1"></i> Ver Imagem
                    </a>
                    <a href="${escapeHtml(valorStr)}" download class="btn btn-sm btn-outline-secondary">
                        <i class="bx bx-download me-1"></i> Baixar
                    </a>
                    <small class="text-muted">${escapeHtml(nomeArquivo)}</small>
                </div>`;
        } else {
            return `
                <div class="d-flex align-items-center gap-2">
                    <a href="${escapeHtml(valorStr)}" target="_blank" class="btn btn-sm btn-outline-primary">
                        <i class="bx bx-file me-1"></i> Abrir
                    </a>
                    <a href="${escapeHtml(valorStr)}" download class="btn btn-sm btn-outline-secondary">
                        <i class="bx bx-download me-1"></i> Baixar
                    </a>
                    <small class="text-muted">${escapeHtml(nomeArquivo)}</small>
                </div>`;
        }
    }
    
    // Verificar se parece ser um caminho de arquivo local (fake path)
    if (valorStr.includes('fakepath') || valorStr.match(/^[A-Z]:\\/i)) {
        return `<span class="text-warning"><i class="bx bx-error me-1"></i>Arquivo não enviado corretamente</span>`;
    }
    
    return escapeHtml(valorStr);
}

function mostrarModalDetalhes(contrato) {
    contratoAtual = contrato;
    
    let dadosHtml = '';
    if (contrato.dados_contrato && typeof contrato.dados_contrato === 'object') {
        for (const [categoria, campos] of Object.entries(contrato.dados_contrato)) {
            dadosHtml += `<h6 class="text-uppercase text-primary mt-3 border-bottom pb-1">${escapeHtml(categoria.replace(/_/g, ' '))}</h6>`;
            if (typeof campos === 'object' && campos !== null) {
                dadosHtml += '<div class="ps-2">';
                for (const [campo, valor] of Object.entries(campos)) {
                    dadosHtml += `<div class="mb-2"><strong>${escapeHtml(campo.replace(/_/g, ' '))}:</strong> ${formatarValorCampo(campo, valor)}</div>`;
                }
                dadosHtml += '</div>';
            }
        }
    }
    
    // Verificar se está em INCOMPLETO para mostrar botão de editar
    const statusNome = (contrato.status_tabulacao || '').toUpperCase();
    const isIncompleto = statusNome.includes('INCOMPLETO');
    
    // Botão de editar se estiver incompleto
    const btnEditar = isIncompleto ? `
        <button class="btn btn-warning btn-sm" onclick="abrirModalEditar(${contrato.id})">
            <i class="bx bx-edit me-1"></i> Completar Dados
        </button>` : '';
    
    // Alert de observações de incompleto
    const alertIncompleto = (isIncompleto && contrato.observacoes_incompleto) ? `
        <div class="alert alert-warning mt-3">
            <strong><i class="bx bx-error me-2"></i>Pendências Informadas pelo Operacional:</strong><br>
            ${escapeHtml(contrato.observacoes_incompleto)}
        </div>` : '';
    
    const html = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary"><i class="bx bx-info-circle me-2"></i>Informações Gerais</h6>
                <p><strong>ID:</strong> #${contrato.id}</p>
                <p><strong>Nº Série:</strong> <span class="badge bg-primary">${escapeHtml(contrato.numero_serie || 'N/A')}</span></p>
                <p><strong>Cliente:</strong> ${escapeHtml(contrato.cliente_nome || 'N/A')}</p>
                <p><strong>Banco:</strong> ${escapeHtml(contrato.banco_nome)}</p>
                <p><strong>Convênio:</strong> ${escapeHtml(contrato.convenio_nome)}</p>
                <p><strong>Operação:</strong> ${escapeHtml(contrato.operacao_nome)}</p>
                <p><strong>Status:</strong> <span class="badge" style="background-color: ${contrato.status_tabulacao_cor}">${escapeHtml(contrato.status_tabulacao)}</span> ${btnEditar}</p>
            </div>
            <div class="col-md-6">
                <h6 class="text-primary"><i class="bx bx-group me-2"></i>Responsáveis</h6>
                <p><strong>Vendedor:</strong> ${escapeHtml(contrato.vendedor_nome)}</p>
                <p><strong>Operador:</strong> ${escapeHtml(contrato.operador_nome || 'Não atribuído')}</p>
                <h6 class="text-primary mt-3"><i class="bx bx-calendar me-2"></i>Datas</h6>
                <p><strong>Criação:</strong> ${contrato.data_criacao}</p>
                ${contrato.data_formalizacao ? `<p><strong>Formalização:</strong> ${contrato.data_formalizacao}</p>` : ''}
                ${contrato.data_liberacao ? `<p><strong>Liberação:</strong> ${contrato.data_liberacao}</p>` : ''}
                ${contrato.data_pagamento ? `<p><strong>Pagamento:</strong> ${contrato.data_pagamento}</p>` : ''}
            </div>
        </div>
        ${alertIncompleto}
        ${contrato.link_formalizacao ? `
        <div class="alert alert-info mt-3">
            <strong><i class="bx bx-link me-2"></i>Link de Formalização:</strong><br>
            <a href="${escapeHtml(contrato.link_formalizacao)}" target="_blank">${escapeHtml(contrato.link_formalizacao)}</a>
        </div>` : ''}
        ${contrato.observacoes ? `
        <div class="alert alert-secondary mt-3">
            <strong><i class="bx bx-comment me-2"></i>Observações:</strong><br>
            ${escapeHtml(contrato.observacoes)}
        </div>` : ''}
        <hr>
        <h6 class="text-primary"><i class="bx bx-file me-2"></i>Dados do Contrato</h6>
        <div class="dados-contrato-scroll" style="max-height: 300px; overflow-y: auto;">
            ${dadosHtml || '<p class="text-muted">Nenhum dado registrado</p>'}
        </div>
    `;
    
    $('#modal-contrato-body').html(html);
    new bootstrap.Modal(document.getElementById('modalVerContrato')).show();
}

// ==================== EDIÇÃO DE CONTRATO INCOMPLETO ====================

function abrirModalEditar(contratoId) {
    // Fechar modal de detalhes
    bootstrap.Modal.getInstance(document.getElementById('modalVerContrato'))?.hide();
    
    // Redirecionar para página de edição do contrato
    window.location.href = `/operacional/contratos/editar/${contratoId}/`;
}

// ==================== LINK DE FORMALIZAÇÃO ====================

function abrirModalLinkFormalizacao(contratoId, link) {
    $('#link-contrato-id').val(contratoId);
    $('#input-link-formalizacao').val(link);
    $('#link-abrir-formalizacao').attr('href', link);
    
    new bootstrap.Modal(document.getElementById('modalLinkFormalizacao')).show();
}

function copiarLinkFormalizacao() {
    const input = document.getElementById('input-link-formalizacao');
    input.select();
    input.setSelectionRange(0, 99999);
    
    navigator.clipboard.writeText(input.value).then(() => {
        alert('Link copiado para a área de transferência!');
    }).catch(() => {
        document.execCommand('copy');
        alert('Link copiado!');
    });
}

function confirmarAssinatura() {
    const contratoId = $('#link-contrato-id').val();
    
    if (!confirm('Confirmar que o cliente já assinou no link de formalização?\n\nO contrato será movido para FORMALIZADO.')) {
        return;
    }
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/confirmar-assinatura/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalLinkFormalizacao')).hide();
                carregarKanban();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

// ==================== UPLOAD DE VÍDEO ====================

function abrirModalUploadVideo(contratoId) {
    $('#video-contrato-id').val(contratoId);
    $('#input-video-cliente').val('');
    $('#video-preview-container').hide();
    $('#video-info').hide();
    $('#video-erro').hide();
    $('#btn-enviar-video').prop('disabled', true);
    
    new bootstrap.Modal(document.getElementById('modalUploadVideo')).show();
}

function validarVideo() {
    const input = document.getElementById('input-video-cliente');
    const file = input.files[0];
    
    $('#video-erro').hide();
    $('#video-info').hide();
    $('#video-preview-container').hide();
    $('#btn-enviar-video').prop('disabled', true);
    
    if (!file) {
        return;
    }
    
    // Validar extensão
    if (!file.name.toLowerCase().endsWith('.mp4')) {
        $('#video-erro').text('Formato inválido! Apenas arquivos .mp4 são aceitos.').show();
        input.value = '';
        return;
    }
    
    // Validar tamanho (25MB)
    const maxSize = 25 * 1024 * 1024;
    if (file.size > maxSize) {
        $('#video-erro').text('Arquivo muito grande! Tamanho máximo: 25MB. Seu arquivo: ' + formatarTamanho(file.size)).show();
        input.value = '';
        return;
    }
    
    // Mostrar informações do arquivo
    $('#video-nome').text(file.name);
    $('#video-tamanho').text(formatarTamanho(file.size));
    $('#video-info').show();
    
    // Mostrar preview
    const videoPreview = document.getElementById('video-preview');
    const url = URL.createObjectURL(file);
    videoPreview.src = url;
    $('#video-preview-container').show();
    
    // Habilitar botão de enviar
    $('#btn-enviar-video').prop('disabled', false);
}

function enviarVideo() {
    const contratoId = $('#video-contrato-id').val();
    const input = document.getElementById('input-video-cliente');
    const file = input.files[0];
    
    if (!file) {
        alert('Selecione um vídeo');
        return;
    }
    
    const formData = new FormData();
    formData.append('video', file);
    
    const btn = $('#btn-enviar-video');
    btn.prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin me-2"></i>Enviando...');
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/upload-video/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        xhr: function() {
            const xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    btn.html(`<i class="bx bx-loader-alt bx-spin me-2"></i>Enviando... ${percent}%`);
                }
            });
            return xhr;
        },
        success: function(response) {
            btn.prop('disabled', false).html('<i class="bx bx-upload me-2"></i>Enviar Vídeo');
            
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalUploadVideo')).hide();
                carregarKanban();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            btn.prop('disabled', false).html('<i class="bx bx-upload me-2"></i>Enviar Vídeo');
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao enviar vídeo'));
        }
    });
}

function abrirModalVerVideo(videoUrl) {
    const video = document.getElementById('video-visualizar');
    video.src = videoUrl;
    $('#link-download-video').attr('href', videoUrl);
    
    new bootstrap.Modal(document.getElementById('modalVerVideo')).show();
    
    // Pausar vídeo ao fechar modal
    $('#modalVerVideo').on('hidden.bs.modal', function() {
        video.pause();
        video.src = '';
    });
}

// ==================== UTILITÁRIOS ====================

function getCsrfToken() {
    return $('[name=csrfmiddlewaretoken]').val() || 
           document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
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

function formatarValor(valor) {
    if (!valor) return 'N/A';
    const numero = parseFloat(valor);
    if (isNaN(numero)) return valor;
    return numero.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatarTamanho(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
