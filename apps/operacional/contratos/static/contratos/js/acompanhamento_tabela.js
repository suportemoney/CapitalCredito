/**
 * Acompanhamento Tabela - Gestão Operacional de Contratos
 * Sistema com SSE para atualizações em tempo real
 */

// URLs dinâmicas
let URLS = {
    tabela: '',
    tabulacoes: '',
    mover: '',
    moverMassa: '',
    bancos: '',
    sse: ''
};

// Estado da aplicação
let contratosData = [];
let contratosOriginal = [];
let tabulacoesData = [];
let sseConectado = false;
let sseReader = null;
let paginaAtual = 1;
const itensPorPagina = 20;
let isSuperuser = false; // Se o usuário é superadmin

$(document).ready(function() {
    const container = $('#tabela-container');
    URLS.tabela = container.data('url-tabela');
    URLS.tabulacoes = container.data('url-tabulacoes');
    URLS.mover = container.data('url-mover');
    URLS.moverMassa = container.data('url-mover-massa');
    URLS.bancos = container.data('url-bancos');
    URLS.sse = container.data('url-sse');
    isSuperuser = container.data('is-superuser') === true || container.data('is-superuser') === 'true';
    
    // Carregar dados iniciais
    Promise.all([
        carregarTabulacoes(),
        carregarBancos()
    ]).then(() => {
        carregarContratos();
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
        if (!response.ok) throw new Error('Erro na conexão SSE');
        
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
                setTimeout(iniciarSSE, 5000);
            });
        }
        
        processarChunk();
    })
    .catch(err => {
        console.error('Erro SSE:', err);
        sseConectado = false;
        atualizarStatusSSE('erro');
        setTimeout(iniciarSSE, 5000);
    });
}

function processarEventoSSE(dados) {
    switch (dados.etapa) {
        case 'conectado':
            console.log('SSE conectado:', dados.mensagem);
            break;
        case 'heartbeat':
            break;
        case 'atualizado':
            if (dados.contrato) {
                atualizarLinhaTabela(dados.contrato);
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

function atualizarLinhaTabela(contrato) {
    // Encontrar e atualizar linha existente ou adicionar nova
    const idx = contratosOriginal.findIndex(c => c.id === contrato.id);
    
    const contratoFormatado = {
        id: contrato.id,
        cliente_nome: contrato.cliente_nome,
        cpf: contrato.cpf,
        banco_nome: contrato.banco_nome,
        convenio_nome: contrato.convenio_nome,
        operacao_nome: contrato.operacao_nome,
        vendedor: contrato.vendedor_nome,
        tabulacao_id: contrato.tabulacao_id,
        tabulacao_nome: contrato.tabulacao_nome,
        tabulacao_cor: contrato.tabulacao_cor,
        link_formalizacao: contrato.link_formalizacao,
        video_cliente: contrato.video_cliente,
        observacoes_incompleto: contrato.observacoes_incompleto,
        data_criacao: contrato.data_atualizacao || contrato.data_criacao
    };
    
    if (idx >= 0) {
        contratosOriginal[idx] = contratoFormatado;
    } else {
        contratosOriginal.unshift(contratoFormatado);
    }
    
    // Reaplicar filtros
    aplicarFiltrosLocais();
}

// ==================== CARREGAR DADOS ====================

function carregarTabulacoes() {
    return new Promise((resolve) => {
        if (!URLS.tabulacoes) {
            resolve();
            return;
        }
        
        $.ajax({
            url: URLS.tabulacoes,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    tabulacoesData = response.data;
                    preencherSelectTabulacoes();
                }
                resolve();
            },
            error: function() {
                resolve();
            }
        });
    });
}

function carregarBancos() {
    return new Promise((resolve) => {
        if (!URLS.bancos) {
            resolve();
            return;
        }
        
        $.ajax({
            url: URLS.bancos,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const select = $('#filtro-banco');
                    response.data.forEach(banco => {
                        select.append(`<option value="${banco.id}">${escapeHtml(banco.nome)}</option>`);
                    });
                }
                resolve();
            },
            error: function() {
                resolve();
            }
        });
    });
}

function preencherSelectTabulacoes() {
    const filtro = $('#filtro-tabulacao');
    const selectMassa = $('#select-tabulacao-massa');
    const selectMover = $('#select-nova-tabulacao');
    
    filtro.find('option:not(:first)').remove();
    selectMassa.find('option:not(:first)').remove();
    selectMover.find('option:not(:first)').remove();
    
    tabulacoesData.forEach(tab => {
        const option = `<option value="${tab.id}">${escapeHtml(tab.nome)}</option>`;
        filtro.append(option);
        selectMassa.append(option);
        selectMover.append(option);
    });
}

function carregarContratos() {
    const btn = $('button:contains("Atualizar")');
    btn.prop('disabled', true).find('i').addClass('bx-spin');
    
    $.ajax({
        url: URLS.tabela || '/operacional/contratos/api/contratos/tabela/',
        method: 'GET',
        data: {
            banco_id: $('#filtro-banco').val(),
            tabulacao_id: $('#filtro-tabulacao').val()
        },
        success: function(response) {
            btn.prop('disabled', false).find('i').removeClass('bx-spin');
            
            if (response.success) {
                contratosOriginal = response.data;
                contratosData = [...contratosOriginal];
                paginaAtual = 1;
                renderizarTabela();
            } else {
                console.error('Erro ao carregar contratos:', response.message);
                mostrarErroTabela('Erro ao carregar contratos');
            }
        },
        error: function() {
            btn.prop('disabled', false).find('i').removeClass('bx-spin');
            mostrarErroTabela('Erro ao conectar com o servidor');
        }
    });
}

// ==================== RENDERIZAÇÃO ====================

function renderizarTabela() {
    const tbody = $('#tbody-contratos');
    
    if (contratosData.length === 0) {
        tbody.html(`
            <tr>
                <td colspan="10" class="text-center py-4">
                    <i class="bx bx-inbox bx-lg text-muted mb-3" style="font-size: 3rem;"></i>
                    <p class="text-muted mb-0">Nenhum contrato encontrado</p>
                </td>
            </tr>
        `);
        atualizarInfoPaginacao(0, 0, 0);
        $('#paginacao').empty();
        return;
    }
    
    // Paginação
    const inicio = (paginaAtual - 1) * itensPorPagina;
    const fim = Math.min(inicio + itensPorPagina, contratosData.length);
    const contratosPagina = contratosData.slice(inicio, fim);
    
    let html = '';
    contratosPagina.forEach(contrato => {
        html += criarLinhaHTML(contrato);
    });
    
    tbody.html(html);
    
    // Atualizar info e paginação
    atualizarInfoPaginacao(inicio + 1, fim, contratosData.length);
    renderizarPaginacao();
    
    // Atualizar container de ações em massa
    verificarSelecao();
}

function criarLinhaHTML(contrato) {
    const tabulacao = tabulacoesData.find(t => t.id === contrato.tabulacao_id) || {};
    const tabulacaoNome = contrato.tabulacao_nome || tabulacao.nome || 'N/A';
    const tabulacaoCor = contrato.tabulacao_cor || tabulacao.cor || '#6c757d';
    
    // Determinar ações disponíveis baseado na tabulação
    let botoesAcao = `
        <button class="btn btn-sm btn-outline-secondary" onclick="abrirModalMover(${contrato.id})" title="Mover">
            <i class="bx bx-transfer"></i>
        </button>
        <button class="btn btn-sm btn-outline-info" onclick="verDetalhes(${contrato.id})" title="Detalhes">
            <i class="bx bx-show"></i>
        </button>
    `;
    
    // Ações específicas por tabulação
    if (tabulacaoNome.toUpperCase() === 'CONTRATOS ENVIADOS') {
        botoesAcao += `
            <button class="btn btn-sm btn-warning" onclick="abrirModalIncompleto(${contrato.id})" title="Marcar Incompleto">
                <i class="bx bx-error"></i>
            </button>
            <button class="btn btn-sm btn-primary" onclick="abrirModalInformarLink(${contrato.id})" title="Informar Link">
                <i class="bx bx-link"></i>
            </button>
        `;
    }
    
    if (tabulacaoNome.toUpperCase() === 'FORMALIZADO') {
        botoesAcao += `
            <button class="btn btn-sm btn-info" onclick="abrirModalSolicitarVideo(${contrato.id})" title="Solicitar Vídeo">
                <i class="bx bx-video"></i>
            </button>
        `;
    }
    
    if (contrato.video_cliente) {
        botoesAcao += `
            <button class="btn btn-sm btn-success" onclick="abrirModalVerVideo('${contrato.video_cliente}')" title="Ver Vídeo">
                <i class="bx bx-play"></i>
            </button>
        `;
    }
    
    if (contrato.link_formalizacao) {
        botoesAcao += `
            <a href="${escapeHtml(contrato.link_formalizacao)}" target="_blank" class="btn btn-sm btn-outline-primary" title="Abrir Link">
                <i class="bx bx-link-external"></i>
            </a>
        `;
    }
    
    // Botão de excluir (apenas superuser)
    if (isSuperuser) {
        botoesAcao += `
            <button class="btn btn-sm btn-danger" onclick="confirmarExclusao(${contrato.id}, '${escapeHtml(contrato.numero_serie || '')}')" title="Excluir Permanentemente">
                <i class="bx bx-trash"></i>
            </button>
        `;
    }
    
    // Badge de incompleto
    let badgeIncompleto = '';
    if (tabulacaoNome.toUpperCase() === 'INCOMPLETO' && contrato.observacoes_incompleto) {
        badgeIncompleto = `<span class="badge bg-warning text-dark ms-1" title="${escapeHtml(contrato.observacoes_incompleto)}"><i class="bx bx-info-circle"></i></span>`;
    }
    
    return `
    <tr data-contrato-id="${contrato.id}">
        <td>
            <input type="checkbox" class="form-check-input select-contrato" 
                   data-contrato-id="${contrato.id}" onchange="verificarSelecao()">
        </td>
        <td>
            <small class="text-muted">#${contrato.id}</small><br>
            <strong class="text-primary">${escapeHtml(contrato.numero_serie || 'N/A')}</strong>
        </td>
        <td>${escapeHtml(contrato.cliente_nome || 'N/A')}</td>
        <td>${escapeHtml(contrato.cpf || '-')}</td>
        <td>${escapeHtml(contrato.banco_nome || 'N/A')}</td>
        <td>
            <small>${escapeHtml(contrato.convenio_nome || '')} / ${escapeHtml(contrato.operacao_nome || '')}</small>
        </td>
        <td>${escapeHtml(contrato.vendedor || 'N/A')}</td>
        <td>
            <span class="badge" style="background-color: ${tabulacaoCor};">
                ${escapeHtml(tabulacaoNome)}
            </span>
            ${badgeIncompleto}
        </td>
        <td><small>${contrato.data_criacao || '-'}</small></td>
        <td>
            <div class="btn-group btn-group-sm">
                ${botoesAcao}
            </div>
        </td>
    </tr>`;
}

function mostrarErroTabela(mensagem) {
    $('#tbody-contratos').html(`
        <tr>
            <td colspan="10" class="text-center py-4 text-danger">
                <i class="bx bx-error-circle bx-lg mb-3" style="font-size: 3rem;"></i>
                <p class="mb-0">${escapeHtml(mensagem)}</p>
            </td>
        </tr>
    `);
}

// ==================== FILTROS ====================

function aplicarFiltrosLocais() {
    contratosData = [...contratosOriginal];
    
    const vendedor = $('#filtro-vendedor').val().toLowerCase().trim();
    const cpf = $('#filtro-cpf').val().replace(/\D/g, '').trim();
    
    if (vendedor) {
        contratosData = contratosData.filter(c => 
            (c.vendedor || '').toLowerCase().includes(vendedor)
        );
    }
    
    if (cpf) {
        contratosData = contratosData.filter(c => 
            (c.cpf || '').replace(/\D/g, '').includes(cpf)
        );
    }
    
    paginaAtual = 1;
    renderizarTabela();
}

function filtrarPorVendedor() {
    aplicarFiltrosLocais();
}

function filtrarPorCPF() {
    aplicarFiltrosLocais();
}

function limparFiltros() {
    $('#filtro-banco').val('');
    $('#filtro-convenio').val('');
    $('#filtro-tabulacao').val('');
    $('#filtro-vendedor').val('');
    $('#filtro-cpf').val('');
    carregarContratos();
}

// ==================== PAGINAÇÃO ====================

function atualizarInfoPaginacao(inicio, fim, total) {
    $('#info-inicio').text(inicio);
    $('#info-fim').text(fim);
    $('#info-total').text(total);
}

function renderizarPaginacao() {
    const totalPaginas = Math.ceil(contratosData.length / itensPorPagina);
    const paginacao = $('#paginacao');
    paginacao.empty();
    
    if (totalPaginas <= 1) return;
    
    // Anterior
    paginacao.append(`
        <li class="page-item ${paginaAtual === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="irParaPagina(${paginaAtual - 1}); return false;">&laquo;</a>
        </li>
    `);
    
    // Páginas
    let inicio = Math.max(1, paginaAtual - 2);
    let fim = Math.min(totalPaginas, paginaAtual + 2);
    
    if (inicio > 1) {
        paginacao.append(`<li class="page-item"><a class="page-link" href="#" onclick="irParaPagina(1); return false;">1</a></li>`);
        if (inicio > 2) {
            paginacao.append(`<li class="page-item disabled"><span class="page-link">...</span></li>`);
        }
    }
    
    for (let i = inicio; i <= fim; i++) {
        paginacao.append(`
            <li class="page-item ${i === paginaAtual ? 'active' : ''}">
                <a class="page-link" href="#" onclick="irParaPagina(${i}); return false;">${i}</a>
            </li>
        `);
    }
    
    if (fim < totalPaginas) {
        if (fim < totalPaginas - 1) {
            paginacao.append(`<li class="page-item disabled"><span class="page-link">...</span></li>`);
        }
        paginacao.append(`<li class="page-item"><a class="page-link" href="#" onclick="irParaPagina(${totalPaginas}); return false;">${totalPaginas}</a></li>`);
    }
    
    // Próximo
    paginacao.append(`
        <li class="page-item ${paginaAtual === totalPaginas ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="irParaPagina(${paginaAtual + 1}); return false;">&raquo;</a>
        </li>
    `);
}

function irParaPagina(pagina) {
    const totalPaginas = Math.ceil(contratosData.length / itensPorPagina);
    if (pagina < 1 || pagina > totalPaginas) return;
    paginaAtual = pagina;
    renderizarTabela();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==================== SELEÇÃO ====================

function toggleSelectAll() {
    const checked = $('#select-all').is(':checked');
    $('.select-contrato').prop('checked', checked);
    verificarSelecao();
}

function verificarSelecao() {
    const selecionados = $('.select-contrato:checked').length;
    const container = $('#acoes-massa-container');
    
    if (selecionados > 0) {
        container.slideDown();
        $('#qtd-selecionados').text(selecionados);
    } else {
        container.slideUp();
    }
    
    // Atualizar checkbox master
    const total = $('.select-contrato').length;
    $('#select-all').prop('checked', selecionados === total && total > 0);
    $('#select-all').prop('indeterminate', selecionados > 0 && selecionados < total);
}

function deselecionarTodos() {
    $('#select-all').prop('checked', false).prop('indeterminate', false);
    $('.select-contrato').prop('checked', false);
    verificarSelecao();
}

// ==================== MODAIS ====================

function abrirModalIncompleto(contratoId) {
    $('#incompleto-contrato-id').val(contratoId);
    $('#input-observacoes-incompleto').val('');
    new bootstrap.Modal(document.getElementById('modalIncompleto')).show();
}

function confirmarIncompleto() {
    const contratoId = $('#incompleto-contrato-id').val();
    const observacoes = $('#input-observacoes-incompleto').val().trim();
    
    if (!observacoes) {
        alert('Informe as observações do que está faltando');
        return;
    }
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/marcar-incompleto/`,
        method: 'POST',
        data: { observacoes: observacoes },
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalIncompleto')).hide();
                carregarContratos();
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

function abrirModalInformarLink(contratoId) {
    $('#link-contrato-id').val(contratoId);
    $('#input-link-formalizacao').val('');
    new bootstrap.Modal(document.getElementById('modalInformarLink')).show();
}

function confirmarLink() {
    const contratoId = $('#link-contrato-id').val();
    const link = $('#input-link-formalizacao').val().trim();
    
    if (!link) {
        alert('Informe o link de formalização');
        return;
    }
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/informar-link/`,
        method: 'POST',
        data: { link_formalizacao: link },
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalInformarLink')).hide();
                carregarContratos();
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

function abrirModalSolicitarVideo(contratoId) {
    $('#video-solicit-contrato-id').val(contratoId);
    new bootstrap.Modal(document.getElementById('modalSolicitarVideo')).show();
}

function confirmarSolicitarVideo() {
    const contratoId = $('#video-solicit-contrato-id').val();
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/solicitar-video/`,
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalSolicitarVideo')).hide();
                carregarContratos();
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

function abrirModalVerVideo(videoUrl) {
    const video = document.getElementById('video-visualizar');
    video.src = videoUrl;
    $('#link-download-video').attr('href', videoUrl);
    
    new bootstrap.Modal(document.getElementById('modalVerVideo')).show();
    
    $('#modalVerVideo').off('hidden.bs.modal').on('hidden.bs.modal', function() {
        video.pause();
        video.src = '';
    });
}

function abrirModalMover(contratoId) {
    $('#mover-contrato-id').val(contratoId);
    $('#select-nova-tabulacao').val('');
    // Limpar e esconder campos extras
    $('#input-observacoes-mover').val('');
    $('#input-link-mover').val('');
    $('#campo-observacoes-mover').hide();
    $('#campo-link-mover').hide();
    $('#campo-video-mover').hide();
    new bootstrap.Modal(document.getElementById('modalMover')).show();
}

function verificarCamposExtras() {
    const tabulacaoId = $('#select-nova-tabulacao').val();
    const tabulacao = tabulacoesData.find(t => t.id == tabulacaoId);
    const nome = tabulacao ? tabulacao.nome.toUpperCase() : '';
    
    // Esconder todos os campos extras
    $('#campo-observacoes-mover').hide();
    $('#campo-link-mover').hide();
    $('#campo-video-mover').hide();
    
    // Mostrar campo específico baseado na tabulação
    if (nome.includes('INCOMPLETO')) {
        $('#campo-observacoes-mover').slideDown();
    } else if (nome.includes('LINK DE FORMALIZACAO') || nome.includes('LINK DE FORMALIZAÇÃO')) {
        $('#campo-link-mover').slideDown();
    } else if (nome.includes('SOLICITACAO DE VIDEO') || nome.includes('SOLICITAÇÃO DE VÍDEO')) {
        $('#campo-video-mover').slideDown();
    }
}

function confirmarMover() {
    const contratoId = $('#mover-contrato-id').val();
    const tabulacaoId = $('#select-nova-tabulacao').val();
    
    if (!tabulacaoId) {
        alert('Selecione uma tabulação');
        return;
    }
    
    const tabulacao = tabulacoesData.find(t => t.id == tabulacaoId);
    const nome = tabulacao ? tabulacao.nome.toUpperCase() : '';
    
    // Validar campos extras obrigatórios
    if (nome.includes('INCOMPLETO')) {
        const observacoes = $('#input-observacoes-mover').val().trim();
        if (!observacoes) {
            alert('Informe as observações do que está faltando');
            return;
        }
        // Usar API específica para marcar como incompleto
        $.ajax({
            url: `/operacional/contratos/api/contratos/${contratoId}/marcar-incompleto/`,
            method: 'POST',
            data: { observacoes: observacoes },
            headers: { 'X-CSRFToken': getCsrfToken() },
            success: function(response) {
                if (response.success) {
                    alert(response.message);
                    bootstrap.Modal.getInstance(document.getElementById('modalMover')).hide();
                    carregarContratos();
                } else {
                    alert('Erro: ' + response.message);
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        });
        return;
    }
    
    if (nome.includes('LINK DE FORMALIZACAO') || nome.includes('LINK DE FORMALIZAÇÃO')) {
        const link = $('#input-link-mover').val().trim();
        if (!link) {
            alert('Informe o link de formalização');
            return;
        }
        // Usar API específica para informar link
        $.ajax({
            url: `/operacional/contratos/api/contratos/${contratoId}/informar-link/`,
            method: 'POST',
            data: { link_formalizacao: link },
            headers: { 'X-CSRFToken': getCsrfToken() },
            success: function(response) {
                if (response.success) {
                    alert(response.message);
                    bootstrap.Modal.getInstance(document.getElementById('modalMover')).hide();
                    carregarContratos();
                } else {
                    alert('Erro: ' + response.message);
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        });
        return;
    }
    
    if (nome.includes('SOLICITACAO DE VIDEO') || nome.includes('SOLICITAÇÃO DE VÍDEO')) {
        // Usar API específica para solicitar vídeo
        $.ajax({
            url: `/operacional/contratos/api/contratos/${contratoId}/solicitar-video/`,
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            success: function(response) {
                if (response.success) {
                    alert(response.message);
                    bootstrap.Modal.getInstance(document.getElementById('modalMover')).hide();
                    carregarContratos();
                } else {
                    alert('Erro: ' + response.message);
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        });
        return;
    }
    
    // Mover normal para outras tabulações
    $.ajax({
        url: URLS.mover || '/operacional/contratos/api/contratos/mover/',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            contrato_id: parseInt(contratoId),
            nova_tabulacao_id: parseInt(tabulacaoId)
        }),
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalMover')).hide();
                carregarContratos();
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

function verDetalhes(contratoId) {
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                mostrarDetalhes(response.data);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao carregar detalhes');
        }
    });
}

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
    
    // Verificar se é um objeto
    if (typeof valor === 'object' && valor !== null) {
        let html = '<div class="border rounded p-2 bg-light">';
        for (const [key, val] of Object.entries(valor)) {
            html += `<span class="me-3"><strong>${escapeHtml(key)}:</strong> ${escapeHtml(val || 'N/A')}</span>`;
        }
        html += '</div>';
        return html;
    }
    
    // Verificar se é um arquivo
    const valorStr = String(valor);
    if (valorStr.startsWith('/media/') || valorStr.startsWith('http')) {
        const nomeArquivo = valorStr.split('/').pop();
        const extensao = nomeArquivo.split('.').pop().toLowerCase();
        const isImagem = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extensao);
        
        if (isImagem) {
            return `<a href="${escapeHtml(valorStr)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bx bx-image me-1"></i>Ver</a>
                    <a href="${escapeHtml(valorStr)}" download class="btn btn-sm btn-outline-secondary"><i class="bx bx-download"></i></a>`;
        } else {
            return `<a href="${escapeHtml(valorStr)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bx bx-file me-1"></i>Abrir</a>
                    <a href="${escapeHtml(valorStr)}" download class="btn btn-sm btn-outline-secondary"><i class="bx bx-download"></i></a>`;
        }
    }
    
    // Verificar caminho de arquivo local (fake path)
    if (valorStr.includes('fakepath') || valorStr.match(/^[A-Z]:\\/i)) {
        return `<span class="text-warning"><i class="bx bx-error me-1"></i>Arquivo não enviado</span>`;
    }
    
    return escapeHtml(valorStr);
}

function mostrarDetalhes(contrato) {
    let dadosHtml = '';
    if (contrato.dados_contrato && typeof contrato.dados_contrato === 'object') {
        for (const [categoria, campos] of Object.entries(contrato.dados_contrato)) {
            dadosHtml += `<h6 class="text-uppercase text-primary mt-3 mb-2 border-bottom pb-1">${escapeHtml(categoria.replace(/_/g, ' '))}</h6>`;
            if (typeof campos === 'object' && campos !== null) {
                dadosHtml += '<div class="row">';
                for (const [campo, valor] of Object.entries(campos)) {
                    dadosHtml += `
                        <div class="col-md-4 mb-2">
                            <strong class="text-muted small">${escapeHtml(campo.replace(/_/g, ' '))}:</strong><br>
                            ${formatarValorCampo(campo, valor)}
                        </div>`;
                }
                dadosHtml += '</div>';
            }
        }
    }
    
    // Alert de observações de incompleto
    const alertIncompleto = contrato.observacoes_incompleto ? `
        <div class="alert alert-warning">
            <strong><i class="bx bx-error me-2"></i>Pendências:</strong><br>
            ${escapeHtml(contrato.observacoes_incompleto)}
        </div>` : '';
    
    const html = `
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header"><i class="bx bx-info-circle me-2"></i>Informações Gerais</div>
                    <div class="card-body">
                        <p><strong>ID:</strong> #${contrato.id}</p>
                        <p><strong>Nº Série:</strong> <span class="badge bg-primary">${escapeHtml(contrato.numero_serie || 'N/A')}</span></p>
                        <p><strong>Cliente:</strong> ${escapeHtml(contrato.cliente_nome || 'N/A')}</p>
                        <p><strong>Banco:</strong> ${escapeHtml(contrato.banco_nome)}</p>
                        <p><strong>Convênio:</strong> ${escapeHtml(contrato.convenio_nome)}</p>
                        <p><strong>Operação:</strong> ${escapeHtml(contrato.operacao_nome)}</p>
                        <p><strong>Status:</strong> <span class="badge" style="background-color: ${contrato.status_tabulacao_cor}">${escapeHtml(contrato.status_tabulacao)}</span></p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header"><i class="bx bx-group me-2"></i>Responsáveis e Datas</div>
                    <div class="card-body">
                        <p><strong>Vendedor:</strong> ${escapeHtml(contrato.vendedor_nome)}</p>
                        <p><strong>Operador:</strong> ${escapeHtml(contrato.operador_nome || 'Não atribuído')}</p>
                        <p><strong>Criação:</strong> ${contrato.data_criacao}</p>
                        ${contrato.data_formalizacao ? `<p><strong>Formalização:</strong> ${contrato.data_formalizacao}</p>` : ''}
                        ${contrato.data_liberacao ? `<p><strong>Liberação:</strong> ${contrato.data_liberacao}</p>` : ''}
                        ${contrato.data_pagamento ? `<p><strong>Pagamento:</strong> ${contrato.data_pagamento}</p>` : ''}
                    </div>
                </div>
            </div>
        </div>
        ${alertIncompleto}
        ${contrato.link_formalizacao ? `
        <div class="alert alert-info">
            <strong><i class="bx bx-link me-2"></i>Link de Formalização:</strong><br>
            <a href="${escapeHtml(contrato.link_formalizacao)}" target="_blank">${escapeHtml(contrato.link_formalizacao)}</a>
        </div>` : ''}
        ${contrato.video_cliente ? `
        <div class="alert alert-success">
            <strong><i class="bx bx-video me-2"></i>Vídeo do Cliente:</strong><br>
            <a href="${escapeHtml(contrato.video_cliente)}" target="_blank" class="btn btn-sm btn-success"><i class="bx bx-play me-1"></i>Assistir</a>
            <a href="${escapeHtml(contrato.video_cliente)}" download class="btn btn-sm btn-outline-success"><i class="bx bx-download"></i>Download</a>
        </div>` : ''}
        ${contrato.observacoes ? `
        <div class="alert alert-secondary">
            <strong><i class="bx bx-comment me-2"></i>Observações:</strong><br>
            ${escapeHtml(contrato.observacoes)}
        </div>` : ''}
        <div class="card">
            <div class="card-header"><i class="bx bx-file me-2"></i>Dados do Contrato</div>
            <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                ${dadosHtml || '<p class="text-muted">Nenhum dado registrado</p>'}
            </div>
        </div>
    `;
    
    $('#modal-detalhes-body').html(html);
    new bootstrap.Modal(document.getElementById('modalDetalhes')).show();
}

// ==================== EXCLUSÃO (SUPERUSER) ====================

function confirmarExclusao(contratoId, numeroSerie) {
    if (!isSuperuser) {
        alert('Apenas administradores podem excluir contratos.');
        return;
    }
    
    const mensagem = numeroSerie 
        ? `ATENÇÃO: Esta ação é irreversível!\n\nDeseja excluir PERMANENTEMENTE o contrato ${numeroSerie}?`
        : `ATENÇÃO: Esta ação é irreversível!\n\nDeseja excluir PERMANENTEMENTE o contrato #${contratoId}?`;
    
    if (!confirm(mensagem)) {
        return;
    }
    
    // Segunda confirmação
    if (!confirm('TEM CERTEZA? O contrato será excluído permanentemente e não poderá ser recuperado!')) {
        return;
    }
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoId}/excluir/`,
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                carregarContratos();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao excluir contrato'));
        }
    });
}

// ==================== AÇÕES EM MASSA ====================

function moverEmMassa() {
    const tabulacaoId = $('#select-tabulacao-massa').val();
    if (!tabulacaoId) {
        alert('Selecione uma tabulação de destino');
        return;
    }
    
    const contratoIds = $('.select-contrato:checked').map(function() {
        return $(this).data('contrato-id');
    }).get();
    
    if (contratoIds.length === 0) {
        alert('Selecione pelo menos um contrato');
        return;
    }
    
    if (!confirm(`Deseja mover ${contratoIds.length} contrato(s) para a tabulação selecionada?`)) {
        return;
    }
    
    $.ajax({
        url: URLS.moverMassa || '/operacional/contratos/api/contratos/mover-massa/',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            contrato_ids: contratoIds,
            nova_tabulacao_id: parseInt(tabulacaoId)
        }),
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                deselecionarTodos();
                carregarContratos();
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
