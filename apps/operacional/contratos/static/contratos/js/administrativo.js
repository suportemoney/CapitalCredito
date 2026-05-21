// JavaScript para administrativo

// Função global para verificar se pode habilitar botão de importar schema
function verificarHabilitarImportarSchema() {
    const arquivoSelecionado = $('#arquivoSchema')[0].files.length > 0;
    const convenioSelecionado = $('#selectConvenioSchema').val();
    const optionOperacao = $('#selectOperacaoSchema option:selected');
    const operacaoId = optionOperacao.data('operacao-id'); // Pode ter operacao_id mesmo sem convenio_operacao_id
    const operacaoSelecionada = $('#selectOperacaoSchema').val() || operacaoId; // Aceitar se tiver value ou operacao_id
    
    const tituloPreenchido = $('#tituloSchema').val().trim().length > 0;
    
    console.log('=== verificarHabilitarImportarSchema ===');
    console.log('Título preenchido:', tituloPreenchido);
    console.log('Arquivo selecionado:', arquivoSelecionado);
    console.log('Convênio selecionado:', convenioSelecionado);
    console.log('Operação ID:', operacaoId);
    console.log('Operação selecionada (value):', $('#selectOperacaoSchema').val());
    
    if (tituloPreenchido && arquivoSelecionado && convenioSelecionado && operacaoSelecionada) {
        $('#btnImportarSchema').prop('disabled', false);
        console.log('✅ Botão habilitado');
    } else {
        $('#btnImportarSchema').prop('disabled', true);
        console.log('❌ Botão desabilitado');
    }
}

$(document).ready(function() {
    carregarBancos();
    carregarConvenios();
    carregarOperacoes();
    carregarConveniosOperacoes();
    carregarSchemasImportados(); // Carregar tabela de schemas importados
    
    // Eventos Bancos
    $('#btnNovoBanco').on('click', function() {
        abrirModalBanco();
    });
    $('#btnSalvarBanco').on('click', function() {
        salvarBanco();
    });
    $('#formImportarBancos').on('submit', function(e) {
        e.preventDefault();
        importarBancosCSV();
    });
    
    // Eventos Convênios
    $('#btnNovoConvenio').on('click', function() {
        abrirModalConvenio();
    });
    $('#btnSalvarConvenio').on('click', function() {
        salvarConvenio();
    });
    $('#formImportarConvenios').on('submit', function(e) {
        e.preventDefault();
        importarConveniosCSV();
    });
    
    // Eventos Operações
    $('#btnNovaOperacao').on('click', function() {
        abrirModalOperacao();
    });
    $('#btnSalvarOperacao').on('click', function() {
        salvarOperacao();
    });
    $('#formImportarOperacoes').on('submit', function(e) {
        e.preventDefault();
        importarOperacoesCSV();
    });
    
    // Eventos Schemas - Fluxo hierárquico: Título -> Arquivo -> Convênio -> Operação
    $('#tituloSchema').on('input', function() {
        verificarHabilitarImportarSchema();
    });
    
    // Quando arquivo é selecionado, mostrar seleção de convênio
    $('#arquivoSchema').on('change', function() {
        console.log('=== Arquivo CSV selecionado ===');
        const arquivo = $(this)[0].files[0];
        console.log('Arquivo:', arquivo ? arquivo.name : 'nenhum');
        
        if ($(this)[0].files.length > 0) {
            console.log('✅ Arquivo selecionado, mostrando seleção de convênio');
            $('#selecaoConvenio').slideDown();
            carregarConveniosParaSchema();
        } else {
            console.log('❌ Nenhum arquivo selecionado');
            $('#selecaoConvenio').slideUp();
            $('#selecaoOperacao').slideUp();
            $('#selectConvenioSchema').val('');
            $('#selectOperacaoSchema').val('').prop('disabled', true);
            verificarHabilitarImportarSchema();
        }
    });
    
    // Quando convênio é selecionado, carregar operações
    $('#selectConvenioSchema').on('change', function() {
        const convenioId = $(this).val();
        console.log('=== Convênio selecionado ===');
        console.log('Convênio ID:', convenioId);
        console.log('Convênio Nome:', $(this).find('option:selected').text());
        
        if (convenioId) {
            $('#selecaoOperacao').slideDown();
            carregarOperacoesParaSchema(convenioId);
        } else {
            $('#selecaoOperacao').slideUp();
            $('#selectOperacaoSchema').val('').prop('disabled', true);
        }
        verificarHabilitarImportarSchema();
    });
    
    // Quando operação é selecionada, apenas verificar se pode importar
    // A associação será criada apenas quando o usuário importar o CSV
    $('#selectOperacaoSchema').on('change', function() {
        verificarHabilitarImportarSchema();
    });
    
    // Carregar Convênio+Operação para edição (select antigo)
    $('#selectConvenioOperacao').on('change', function() {
        const convenioOperacaoId = $(this).val();
        if (convenioOperacaoId) {
            $('#btnCarregarSchema').prop('disabled', false);
            $('#campo_schema_convenio_operacao_id').val(convenioOperacaoId);
        } else {
            $('#btnCarregarSchema').prop('disabled', true);
        }
    });
    
    $('#btnCarregarSchema').on('click', function() {
        const convenioOperacaoId = $('#selectConvenioOperacao').val();
        if (convenioOperacaoId) {
            carregarCamposSchema(convenioOperacaoId);
        }
    });
    $('#btnNovoCampoSchema').on('click', function() {
        const convenioOperacaoId = $('#selectConvenioOperacao').val();
        if (convenioOperacaoId) {
            abrirModalCampoSchema();
        } else {
            alert('Selecione primeiro um Convênio+Operação');
        }
    });
    $('#btnSalvarCampoSchema').on('click', function() {
        salvarCampoSchema();
    });
    $('#formImportarSchema').on('submit', function(e) {
        e.preventDefault();
        // A validação já é feita em importarSchemaCSV() e verificarHabilitarImportarSchema()
        // O botão só é habilitado quando tudo está preenchido
        importarSchemaCSV();
    });
    $('#campo_schema_type').on('change', function() {
        const tipo = $(this).val();
        if (tipo === 'SELECT' || tipo === 'MULTISELECTOR' || tipo === 'MULTIINPUT' || tipo === 'FILE' || tipo === 'MULTIFILE') {
            $('#campo_schema_choices_container').show();
        } else {
            $('#campo_schema_choices_container').hide();
        }
    });
});

// ========== BANCOS ==========
function carregarBancos() {
    $.ajax({
        url: '/operacional/contratos/api/admin/bancos/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderizarBancos(response.data);
            }
        },
        error: function() {
            console.error('Erro ao carregar bancos');
        }
    });
}

function renderizarBancos(bancos) {
    let html = '';
    bancos.forEach(function(banco) {
        html += `<tr>
            <td>${banco.id}</td>
            <td>${banco.nome}</td>
            <td>${banco.codigo || '-'}</td>
            <td><span class="badge ${banco.status ? 'bg-success' : 'bg-secondary'}">${banco.status ? 'Ativo' : 'Inativo'}</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editarBanco(${banco.id})">
                    <i class="bx bx-edit"></i> Editar
                </button>
                <button class="btn btn-sm btn-danger" onclick="deletarBanco(${banco.id})">
                    <i class="bx bx-trash"></i> Deletar
                </button>
            </td>
        </tr>`;
    });
    $('#tabelaBancos tbody').html(html);
}

function abrirModalBanco(bancoId = null) {
    // Limpar formulário
    $('#banco_id').val('');
    $('#banco_nome').val('');
    $('#banco_codigo').val('');
    $('#banco_status').prop('checked', true);
    $('#modalBancoTitle').text('Novo Banco');
    
    if (bancoId) {
        $.ajax({
            url: `/operacional/contratos/api/admin/bancos/${bancoId}/editar/`,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const banco = response.data;
                    $('#banco_id').val(banco.id);
                    $('#banco_nome').val(banco.nome);
                    $('#banco_codigo').val(banco.codigo || '');
                    $('#banco_status').prop('checked', banco.status);
                    $('#modalBancoTitle').text('Editar Banco');
                }
            },
            complete: function() {
                // Abrir modal após carregar dados
                const modalElement = document.getElementById('modalBanco');
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            }
        });
    } else {
        // Abrir modal diretamente para novo banco
        const modalElement = document.getElementById('modalBanco');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}

function salvarBanco() {
    const formData = new FormData();
    formData.append('nome', $('#banco_nome').val());
    formData.append('codigo', $('#banco_codigo').val());
    formData.append('status', $('#banco_status').is(':checked') ? 'on' : 'off');
    
    const bancoId = $('#banco_id').val();
    const url = bancoId 
        ? `/operacional/contratos/api/admin/bancos/${bancoId}/editar/`
        : '/operacional/contratos/api/admin/bancos/criar/';
    const method = bancoId ? 'POST' : 'POST';
    
    $.ajax({
        url: url,
        method: method,
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                const modalElement = document.getElementById('modalBanco');
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    modalInstance.hide();
                }
                carregarBancos();
                alert(response.message || 'Banco salvo com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao salvar banco');
        }
    });
}

function editarBanco(bancoId) {
    abrirModalBanco(bancoId);
}

function deletarBanco(bancoId) {
    if (!confirm('Tem certeza que deseja deletar este banco?')) return;
    
    $.ajax({
        url: `/operacional/contratos/api/admin/bancos/${bancoId}/deletar/`,
        method: 'POST',
        data: { csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val() },
        success: function(response) {
            if (response.success) {
                carregarBancos();
                alert(response.message || 'Banco deletado com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao deletar banco');
        }
    });
}

function importarBancosCSV() {
    const formData = new FormData();
    formData.append('arquivo', $('#arquivoBancos')[0].files[0]);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/operacional/contratos/api/admin/bancos/importar-csv/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                carregarBancos();
                alert(response.message || 'CSV importado com sucesso!');
                $('#arquivoBancos').val('');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao importar CSV');
        }
    });
}

// ========== CONVÊNIOS ==========
function carregarConvenios() {
    $.ajax({
        url: '/operacional/contratos/api/admin/convenios/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderizarConvenios(response.data);
            }
        },
        error: function() {
            console.error('Erro ao carregar convênios');
        }
    });
}

function renderizarConvenios(convenios) {
    let html = '';
    convenios.forEach(function(convenio) {
        html += `<tr>
            <td>${convenio.id}</td>
            <td>${convenio.nome}</td>
            <td>${convenio.codigo || '-'}</td>
            <td><span class="badge ${convenio.status ? 'bg-success' : 'bg-secondary'}">${convenio.status ? 'Ativo' : 'Inativo'}</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editarConvenio(${convenio.id})">
                    <i class="bx bx-edit"></i> Editar
                </button>
                <button class="btn btn-sm btn-danger" onclick="deletarConvenio(${convenio.id})">
                    <i class="bx bx-trash"></i> Deletar
                </button>
            </td>
        </tr>`;
    });
    $('#tabelaConvenios tbody').html(html);
}

function abrirModalConvenio(convenioId = null) {
    // Limpar formulário
    $('#convenio_id').val('');
    $('#convenio_nome').val('');
    $('#convenio_codigo').val('');
    $('#convenio_status').prop('checked', true);
    $('#modalConvenioTitle').text('Novo Convênio');
    
    if (convenioId) {
        $.ajax({
            url: `/operacional/contratos/api/admin/convenios/${convenioId}/editar/`,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const convenio = response.data;
                    $('#convenio_id').val(convenio.id);
                    $('#convenio_nome').val(convenio.nome);
                    $('#convenio_codigo').val(convenio.codigo || '');
                    $('#convenio_status').prop('checked', convenio.status);
                    $('#modalConvenioTitle').text('Editar Convênio');
                }
            },
            complete: function() {
                // Abrir modal após carregar dados
                const modalElement = document.getElementById('modalConvenio');
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            }
        });
    } else {
        // Abrir modal diretamente para novo convênio
        const modalElement = document.getElementById('modalConvenio');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}

function salvarConvenio() {
    const formData = new FormData();
    formData.append('nome', $('#convenio_nome').val());
    formData.append('codigo', $('#convenio_codigo').val());
    formData.append('status', $('#convenio_status').is(':checked') ? 'on' : 'off');
    
    const convenioId = $('#convenio_id').val();
    const url = convenioId 
        ? `/operacional/contratos/api/admin/convenios/${convenioId}/editar/`
        : '/operacional/contratos/api/admin/convenios/criar/';
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                const modalElement = document.getElementById('modalConvenio');
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    modalInstance.hide();
                }
                carregarConvenios();
                alert(response.message || 'Convênio salvo com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao salvar convênio');
        }
    });
}

function editarConvenio(convenioId) {
    abrirModalConvenio(convenioId);
}

function deletarConvenio(convenioId) {
    if (!confirm('Tem certeza que deseja deletar este convênio?')) return;
    
    $.ajax({
        url: `/operacional/contratos/api/admin/convenios/${convenioId}/deletar/`,
        method: 'POST',
        data: { csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val() },
        success: function(response) {
            if (response.success) {
                carregarConvenios();
                alert(response.message || 'Convênio deletado com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao deletar convênio');
        }
    });
}

function importarConveniosCSV() {
    const formData = new FormData();
    formData.append('arquivo', $('#arquivoConvenios')[0].files[0]);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/operacional/contratos/api/admin/convenios/importar-csv/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                carregarConvenios();
                alert(response.message || 'CSV importado com sucesso!');
                $('#arquivoConvenios').val('');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao importar CSV');
        }
    });
}

// ========== OPERAÇÕES ==========
function carregarOperacoes() {
    $.ajax({
        url: '/operacional/contratos/api/admin/operacoes/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                renderizarOperacoes(response.data);
            }
        },
        error: function() {
            console.error('Erro ao carregar operações');
        }
    });
}

function renderizarOperacoes(operacoes) {
    let html = '';
    operacoes.forEach(function(operacao) {
        html += `<tr>
            <td>${operacao.id}</td>
            <td>${operacao.nome}</td>
            <td>${operacao.codigo || '-'}</td>
            <td><span class="badge ${operacao.status ? 'bg-success' : 'bg-secondary'}">${operacao.status ? 'Ativo' : 'Inativo'}</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editarOperacao(${operacao.id})">
                    <i class="bx bx-edit"></i> Editar
                </button>
                <button class="btn btn-sm btn-danger" onclick="deletarOperacao(${operacao.id})">
                    <i class="bx bx-trash"></i> Deletar
                </button>
            </td>
        </tr>`;
    });
    $('#tabelaOperacoes tbody').html(html);
}

function abrirModalOperacao(operacaoId = null) {
    // Limpar formulário
    $('#operacao_id').val('');
    $('#operacao_nome').val('');
    $('#operacao_codigo').val('');
    $('#operacao_status').prop('checked', true);
    $('#modalOperacaoTitle').text('Nova Operação');
    
    if (operacaoId) {
        $.ajax({
            url: `/operacional/contratos/api/admin/operacoes/${operacaoId}/editar/`,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const operacao = response.data;
                    $('#operacao_id').val(operacao.id);
                    $('#operacao_nome').val(operacao.nome);
                    $('#operacao_codigo').val(operacao.codigo || '');
                    $('#operacao_status').prop('checked', operacao.status);
                    $('#modalOperacaoTitle').text('Editar Operação');
                }
            },
            complete: function() {
                // Abrir modal após carregar dados
                const modalElement = document.getElementById('modalOperacao');
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            }
        });
    } else {
        // Abrir modal diretamente para nova operação
        const modalElement = document.getElementById('modalOperacao');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}

function salvarOperacao() {
    const formData = new FormData();
    formData.append('nome', $('#operacao_nome').val());
    formData.append('codigo', $('#operacao_codigo').val());
    formData.append('status', $('#operacao_status').is(':checked') ? 'on' : 'off');
    
    const operacaoId = $('#operacao_id').val();
    const url = operacaoId 
        ? `/operacional/contratos/api/admin/operacoes/${operacaoId}/editar/`
        : '/operacional/contratos/api/admin/operacoes/criar/';
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                const modalElement = document.getElementById('modalOperacao');
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    modalInstance.hide();
                }
                carregarOperacoes();
                alert(response.message || 'Operação salva com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao salvar operação');
        }
    });
}

function editarOperacao(operacaoId) {
    abrirModalOperacao(operacaoId);
}

function deletarOperacao(operacaoId) {
    if (!confirm('Tem certeza que deseja deletar esta operação?')) return;
    
    $.ajax({
        url: `/operacional/contratos/api/admin/operacoes/${operacaoId}/deletar/`,
        method: 'POST',
        data: { csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val() },
        success: function(response) {
            if (response.success) {
                carregarOperacoes();
                alert(response.message || 'Operação deletada com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao deletar operação');
        }
    });
}

function importarOperacoesCSV() {
    const formData = new FormData();
    formData.append('arquivo', $('#arquivoOperacoes')[0].files[0]);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/operacional/contratos/api/admin/operacoes/importar-csv/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                carregarOperacoes();
                alert(response.message || 'CSV importado com sucesso!');
                $('#arquivoOperacoes').val('');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao importar CSV');
        }
    });
}

// ========== SCHEMAS ==========
function carregarConveniosOperacoes() {
    $.ajax({
        url: '/operacional/contratos/api/admin/convenios-operacoes/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                let options = '<option value="">Selecione Convênio + Operação...</option>';
                response.data.forEach(function(co) {
                    options += `<option value="${co.id}">${co.convenio_nome} - ${co.operacao_nome}</option>`;
                });
                $('#selectConvenioOperacao').html(options);
            }
        },
        error: function() {
            console.error('Erro ao carregar convênios+operações');
        }
    });
}

// Funções para carregar Convênios e Operações para importação de Schema
function carregarConveniosParaSchema() {
    console.log('=== carregarConveniosParaSchema ===');
    
    $.ajax({
        url: '/operacional/contratos/api/admin/convenios/',
        method: 'GET',
        success: function(response) {
            console.log('✅ Resposta da API de convênios:');
            console.log('Response:', response);
            console.log('Success:', response.success);
            console.log('Data:', response.data);
            
            if (response.success) {
                let options = '<option value="">Selecione o convênio...</option>';
                
                response.data.forEach(function(convenio) {
                    console.log('Convênio encontrado:', convenio);
                    const statusBadge = convenio.status ? '' : ' (Inativo)';
                    options += `<option value="${convenio.id}">${convenio.nome}${statusBadge}</option>`;
                    console.log(`  ✅ Adicionado: ${convenio.nome} (ID: ${convenio.id})`);
                });
                
                console.log(`Total de convênios: ${response.data.length}`);
                $('#selectConvenioSchema').html(options);
                console.log('✅ Select de convênios atualizado');
            } else {
                console.error('❌ API retornou success=false');
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao carregar convênios:');
            console.error('Status:', status);
            console.error('Error:', error);
            console.error('XHR:', xhr);
        }
    });
}

function carregarOperacoesParaSchema(convenioId) {
    console.log('=== carregarOperacoesParaSchema ===');
    console.log('Convênio ID recebido:', convenioId);
    console.log('Tipo do convenioId:', typeof convenioId);
    
    if (!convenioId) {
        console.error('❌ convenioId não fornecido ou vazio');
        $('#selectOperacaoSchema').html('<option value="">Selecione primeiro o convênio...</option>').prop('disabled', true);
        return;
    }
    
    // Mostrar loading
    $('#selectOperacaoSchema').html('<option value="">Carregando operações...</option>').prop('disabled', true);
    
    // Buscar TODAS as operações disponíveis (não apenas as associadas)
    carregarTodasOperacoesParaSchema(convenioId);
}

function carregarTodasOperacoesParaSchema(convenioId) {
    console.log('=== carregarTodasOperacoesParaSchema ===');
    console.log('Convênio ID:', convenioId);
    
    // Armazenar convenioId no select para uso posterior
    $('#selectOperacaoSchema').data('convenio-id', convenioId);
    
    $.ajax({
        url: '/operacional/contratos/api/admin/operacoes/',
        method: 'GET',
        success: function(response) {
            console.log('✅ Resposta da API de todas as operações:');
            console.log('Response:', response);
            console.log('Success:', response.success);
            console.log('Data:', response.data);
            
            if (response.success && response.data && response.data.length > 0) {
                let options = '<option value="">Selecione a operação...</option>';
                let operacoesAtivas = 0;
                
                response.data.forEach(function(operacao) {
                    console.log('Operação encontrada:', operacao);
                    const statusBadge = operacao.status ? '' : ' (Inativa)';
                    // Usar operacao.id temporariamente, vamos criar a associação depois
                    options += `<option value="" data-operacao-id="${operacao.id}" data-convenio-id="${convenioId}">${operacao.nome}${statusBadge}</option>`;
                    console.log(`  ✅ Adicionado: ${operacao.nome} (ID: ${operacao.id})`);
                });
                
                console.log(`Total de operações: ${response.data.length}`);
                $('#selectOperacaoSchema').html(options).prop('disabled', false);
                console.log('✅ Select de operações atualizado (será criada associação ao selecionar)');
            } else {
                console.error('❌ Nenhuma operação disponível');
                $('#selectOperacaoSchema').html('<option value="" disabled>Nenhuma operação disponível. Crie uma operação primeiro.</option>').prop('disabled', true);
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao carregar todas as operações:');
            console.error('Status:', status);
            console.error('Error:', error);
            $('#selectOperacaoSchema').html('<option value="">Erro ao carregar operações</option>').prop('disabled', true);
        }
    });
}

function carregarCamposSchema(convenioOperacaoId) {
    console.log('=== carregarCamposSchema ===');
    console.log('📥 Convenio Operacao ID:', convenioOperacaoId);
    console.log('📡 URL:', '/operacional/contratos/api/schemas/por-convenio-operacao/');
    
    $.ajax({
        url: '/operacional/contratos/api/schemas/por-convenio-operacao/',
        method: 'GET',
        data: { convenio_operacao_id: convenioOperacaoId },
        success: function(response) {
            console.log('✅ Resposta da API:');
            console.log('   Success:', response.success);
            console.log('   Data:', response.data);
            console.log('   Quantidade de campos:', response.data ? response.data.length : 0);
            
            if (response.success && response.data) {
                // Mostrar primeiros 3 campos para debug
                console.log('📋 Primeiros 3 campos:');
                response.data.slice(0, 3).forEach((campo, i) => {
                    console.log(`   [${i}] id=${campo.id}, label="${campo.label}", pagina=${campo.pagina}, ordem=${campo.ordem}`);
                });
                
                renderizarCamposSchema(response.data);
                $('#listaCamposSchema').show();
            } else {
                console.error('❌ API retornou success=false ou data vazio');
                console.error('   Message:', response.message);
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao carregar campos do schema:');
            console.error('   Status:', status);
            console.error('   Error:', error);
            console.error('   Response:', xhr.responseText);
        }
    });
}

function renderizarCamposSchema(campos) {
    console.log('=== renderizarCamposSchema ===');
    console.log('📊 Total de campos recebidos:', campos.length);
    
    // Verificar se campos têm a propriedade pagina
    const camposComPagina = campos.filter(c => c.pagina !== undefined && c.pagina !== null);
    const camposSemPagina = campos.filter(c => c.pagina === undefined || c.pagina === null);
    console.log('📄 Campos COM pagina definida:', camposComPagina.length);
    console.log('⚠️ Campos SEM pagina definida:', camposSemPagina.length);
    
    if (camposSemPagina.length > 0) {
        console.warn('⚠️ Campos sem pagina (usarão default 1):');
        camposSemPagina.slice(0, 5).forEach(c => {
            console.warn(`   - ${c.label} (id: ${c.id})`);
        });
    }
    
    let html = '';
    // Ordenar por página e depois por ordem
    campos.sort((a, b) => {
        if ((a.pagina || 1) !== (b.pagina || 1)) {
            return (a.pagina || 1) - (b.pagina || 1);
        }
        return (a.ordem || 0) - (b.ordem || 0);
    });
    
    // Contar páginas únicas
    const paginasUnicas = [...new Set(campos.map(c => c.pagina || 1))].sort((a, b) => a - b);
    console.log('📑 Páginas encontradas:', paginasUnicas);
    
    campos.forEach(function(campo, index) {
        const pagina = campo.pagina || 1;
        
        // Log para os primeiros 5 campos
        if (index < 5) {
            console.log(`   Renderizando [${index}]: pagina=${pagina}, ordem=${campo.ordem}, label="${campo.label}"`);
        }
        
        html += `<tr>
            <td><span class="badge bg-primary">Pág. ${pagina}</span></td>
            <td>${campo.ordem}</td>
            <td>${campo.category}</td>
            <td>${campo.label}</td>
            <td>${campo.type}</td>
            <td><span class="badge ${campo.required ? 'bg-danger' : 'bg-secondary'}">${campo.required ? 'Sim' : 'Não'}</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editarCampoSchema(${campo.id})">
                    <i class="bx bx-edit"></i> Editar
                </button>
                <button class="btn btn-sm btn-danger" onclick="deletarCampoSchema(${campo.id})">
                    <i class="bx bx-trash"></i> Deletar
                </button>
            </td>
        </tr>`;
    });
    
    console.log('✅ HTML gerado, aplicando na tabela...');
    $('#tabelaCamposSchema tbody').html(html);
    console.log('✅ Tabela atualizada!');
}

function abrirModalCampoSchema(campoId = null) {
    // Limpar formulário
    $('#campo_schema_id').val('');
    $('#campo_schema_category').val('');
    $('#campo_schema_label').val('');
    $('#campo_schema_type').val('').trigger('change');
    $('#campo_schema_placeholder').val('');
    $('#campo_schema_choices').val('');
    $('#campo_schema_ordem').val('0');
    $('#campo_schema_pagina').val('1');
    $('#campo_schema_required').prop('checked', false);
    $('#modalCampoSchemaTitle').text('Novo Campo');
    
    // Garantir que o convenio_operacao_id está preenchido
    const convenioOperacaoId = $('#selectConvenioOperacao').val();
    if (convenioOperacaoId) {
        $('#campo_schema_convenio_operacao_id').val(convenioOperacaoId);
    }
    
    if (campoId) {
        $.ajax({
            url: `/operacional/contratos/api/schema/campo/${campoId}/editar/`,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const campo = response.data;
                    $('#campo_schema_id').val(campo.id);
                    $('#campo_schema_convenio_operacao_id').val(campo.convenio_operacao_id);
                    $('#campo_schema_category').val(campo.category);
                    $('#campo_schema_label').val(campo.label);
                    $('#campo_schema_type').val(campo.type).trigger('change');
                    $('#campo_schema_placeholder').val(campo.placeholder || '');
                    $('#campo_schema_choices').val(campo.choices ? campo.choices.join(campo.type === 'MULTIINPUT' ? ';' : ',') : '');
                    $('#campo_schema_ordem').val(campo.ordem);
                    $('#campo_schema_pagina').val(campo.pagina || 1);
                    $('#campo_schema_required').prop('checked', campo.required);
                    $('#modalCampoSchemaTitle').text('Editar Campo');
                }
            },
            complete: function() {
                // Abrir modal após carregar dados
                const modalElement = document.getElementById('modalCampoSchema');
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            }
        });
    } else {
        // Abrir modal diretamente para novo campo
        const modalElement = document.getElementById('modalCampoSchema');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}

function salvarCampoSchema() {
    const formData = new FormData();
    formData.append('convenio_operacao_id', $('#campo_schema_convenio_operacao_id').val());
    formData.append('category', $('#campo_schema_category').val());
    formData.append('label', $('#campo_schema_label').val());
    formData.append('type', $('#campo_schema_type').val());
    formData.append('placeholder', $('#campo_schema_placeholder').val());
    formData.append('choices', $('#campo_schema_choices').val());
    formData.append('ordem', $('#campo_schema_ordem').val());
    formData.append('pagina', $('#campo_schema_pagina').val() || '1');
    formData.append('required', $('#campo_schema_required').is(':checked') ? 'true' : 'false');
    
    const campoId = $('#campo_schema_id').val();
    const url = campoId 
        ? `/operacional/contratos/api/schema/campo/${campoId}/editar/`
        : '/operacional/contratos/api/schema/criar-campo/';
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                const modalElement = document.getElementById('modalCampoSchema');
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    modalInstance.hide();
                }
                const convenioOperacaoId = $('#selectConvenioOperacao').val();
                if (convenioOperacaoId) {
                    carregarCamposSchema(convenioOperacaoId);
                }
                alert(response.message || 'Campo salvo com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao salvar campo');
        }
    });
}

function editarCampoSchema(campoId) {
    abrirModalCampoSchema(campoId);
}

function deletarCampoSchema(campoId) {
    if (!confirm('Tem certeza que deseja deletar este campo?')) return;
    
    $.ajax({
        url: `/operacional/contratos/api/schema/campo/${campoId}/deletar/`,
        method: 'POST',
        data: { csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val() },
        success: function(response) {
            if (response.success) {
                const convenioOperacaoId = $('#selectConvenioOperacao').val();
                if (convenioOperacaoId) {
                    carregarCamposSchema(convenioOperacaoId);
                }
                alert(response.message || 'Campo deletado com sucesso!');
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao deletar campo');
        }
    });
}

function criarAssociacaoConvenioOperacao(convenioId, operacaoId) {
    console.log('=== criarAssociacaoConvenioOperacao ===');
    console.log('Convênio ID:', convenioId);
    console.log('Operação ID:', operacaoId);
    
    const formData = new FormData();
    formData.append('convenio_id', convenioId);
    formData.append('operacao_id', operacaoId);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/operacional/contratos/api/admin/convenios-operacoes/associar/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            console.log('✅ Resposta da criação de associação:', response);
            console.log('Response completo:', JSON.stringify(response, null, 2));
            
            if (response.success) {
                // A API retorna o ID em response.data.id
                let convenioOperacaoId = null;
                if (response.data) {
                    convenioOperacaoId = response.data.id || response.data;
                }
                
                console.log('✅ Associação criada/encontrada com ID:', convenioOperacaoId);
                console.log('Já existia?', response.ja_existia || false);
                
                if (convenioOperacaoId) {
                    // Atualizar o select com o convenio_operacao_id
                    const optionAtual = $('#selectOperacaoSchema option:selected');
                    optionAtual.attr('value', convenioOperacaoId);
                    optionAtual.attr('data-convenio-operacao-id', convenioOperacaoId);
                    optionAtual.text(optionAtual.text().replace(' (Criar associação)', ''));
                    
                    // Ativar a associação automaticamente se foi criada agora
                    if (!response.ja_existia) {
                        ativarAssociacaoConvenioOperacao(convenioOperacaoId);
                    } else {
                        verificarHabilitarImportarSchema();
                    }
                } else {
                    console.error('❌ ID da associação não retornado pela API');
                    alert('Associação criada mas ID não foi retornado. Recarregue a página.');
                }
            } else {
                console.error('❌ Erro ao criar associação:', response.message);
                alert('Erro ao criar associação: ' + response.message);
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao criar associação:');
            console.error('Status:', status);
            console.error('Error:', error);
            let errorMsg = 'Erro ao criar associação';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg = xhr.responseJSON.message;
            }
            alert(errorMsg);
        }
    });
}

function buscarAssociacaoExistente(convenioId, operacaoId) {
    console.log('=== buscarAssociacaoExistente ===');
    console.log('Convênio ID:', convenioId);
    console.log('Operação ID:', operacaoId);
    
    $.ajax({
        url: '/operacional/contratos/api/admin/convenios-operacoes/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const associacao = response.data.find(function(co) {
                    return co.convenio_id == convenioId && co.operacao_id == operacaoId;
                });
                
                if (associacao) {
                    console.log('✅ Associação existente encontrada:', associacao);
                    const convenioOperacaoId = associacao.id;
                    
                    // Atualizar o select
                    const optionAtual = $('#selectOperacaoSchema option:selected');
                    optionAtual.attr('value', convenioOperacaoId);
                    optionAtual.attr('data-convenio-operacao-id', convenioOperacaoId);
                    optionAtual.text(optionAtual.text().replace(' (Criar associação)', ''));
                    
                    // Ativar se não estiver ativa
                    if (!associacao.ativo && convenioOperacaoId) {
                        ativarAssociacaoConvenioOperacao(convenioOperacaoId);
                    } else {
                        verificarHabilitarImportarSchema();
                    }
                } else {
                    console.error('❌ Associação não encontrada mesmo após busca');
                    alert('Erro ao encontrar associação. Tente novamente.');
                }
            }
        },
        error: function(xhr) {
            console.error('❌ Erro ao buscar associação existente:', xhr);
        }
    });
}

function ativarAssociacaoConvenioOperacao(convenioOperacaoId) {
    console.log('=== ativarAssociacaoConvenioOperacao ===');
    console.log('Convenio Operacao ID:', convenioOperacaoId);
    
    const formData = new FormData();
    formData.append('status', 'true');
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: `/operacional/contratos/api/admin/convenios-operacoes/${convenioOperacaoId}/ativar/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            console.log('✅ Associação ativada:', response);
            verificarHabilitarImportarSchema();
        },
        error: function(xhr) {
            console.warn('⚠️ Erro ao ativar associação (não crítico):', xhr);
            // Mesmo com erro, verificar se pode importar
            verificarHabilitarImportarSchema();
        }
    });
}

function carregarSchemasImportados() {
    console.log('=== carregarSchemasImportados ===');
    
    $.ajax({
        url: '/operacional/contratos/api/schemas/importados/',
        method: 'GET',
        success: function(response) {
            console.log('✅ Resposta da API de schemas importados:', response);
            if (response.success) {
                renderizarSchemasImportados(response.data);
            } else {
                console.error('❌ Erro ao carregar schemas:', response.message);
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao carregar schemas importados:', status, error);
        }
    });
}

function renderizarSchemasImportados(schemas) {
    let html = '';
    if (schemas.length === 0) {
        html = '<tr><td colspan="7" class="text-center text-muted">Nenhum schema importado ainda</td></tr>';
    } else {
        schemas.forEach(function(schema) {
            const statusBadge = schema.ativo ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>';
            html += `<tr>
                <td>${schema.id}</td>
                <td><strong>${schema.titulo}</strong></td>
                <td>${schema.convenio_nome}</td>
                <td>${schema.operacao_nome}</td>
                <td><span class="badge bg-info">${schema.campos_count} campos</span></td>
                <td>${schema.data_importacao}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="visualizarSchema(${schema.id})" title="Visualizar/Editar">
                        <i class="bx bx-show"></i> Ver/Editar
                    </button>
                </td>
            </tr>`;
        });
    }
    $('#tabelaSchemasImportados tbody').html(html);
}

function visualizarSchema(convenioOperacaoId) {
    console.log('=== visualizarSchema ===');
    console.log('Convenio Operacao ID:', convenioOperacaoId);
    
    // Selecionar no select de edição e carregar
    $('#selectConvenioOperacao').val(convenioOperacaoId);
    $('#btnCarregarSchema').prop('disabled', false);
    carregarCamposSchema(convenioOperacaoId);
    
    // Scroll até a seção de edição
    $('html, body').animate({
        scrollTop: $('#selectConvenioOperacao').offset().top - 100
    }, 500);
}

function importarSchemaCSV() {
    console.log('=== importarSchemaCSV ===');
    
    // Pegar título, convenio_id e operacao_id (a associação será criada na API ao importar)
    const titulo = $('#tituloSchema').val().trim();
    const convenioId = $('#selectConvenioSchema').val();
    const selectOperacao = $('#selectOperacaoSchema');
    const optionOperacao = selectOperacao.find('option:selected');
    
    // Usar EXATAMENTE a mesma lógica que funciona em verificarHabilitarImportarSchema
    const operacaoId = optionOperacao.data('operacao-id'); // Pode ter operacao_id mesmo sem convenio_operacao_id
    const convenioOperacaoId = selectOperacao.val(); // Pode estar vazio se não houver associação ainda
    const operacaoSelecionada = convenioOperacaoId || operacaoId; // Aceitar se tiver value ou operacao_id
    
    const arquivo = $('#arquivoSchema')[0].files[0];
    
    console.log('=== DADOS COLETADOS ===');
    console.log('Título:', titulo);
    console.log('Convênio ID:', convenioId);
    console.log('Operação selecionada (value):', convenioOperacaoId);
    console.log('Operação ID (data-operacao-id):', operacaoId);
    console.log('Operação selecionada (value ou id):', operacaoSelecionada);
    console.log('Option selecionada:', optionOperacao);
    console.log('HTML da option:', optionOperacao[0] ? optionOperacao[0].outerHTML : 'N/A');
    console.log('Texto da option:', optionOperacao.text());
    console.log('Arquivo:', arquivo ? arquivo.name : 'nenhum');
    
    // Se o botão está habilitado, significa que a validação já passou
    // Apenas verificar se temos os dados necessários para enviar (sem alertas chatos)
    if (!titulo || !arquivo || !convenioId || !operacaoSelecionada) {
        console.error('❌ Dados incompletos apesar do botão estar habilitado');
        console.error('Título:', titulo);
        console.error('Arquivo:', arquivo);
        console.error('Convênio ID:', convenioId);
        console.error('Operação selecionada:', operacaoSelecionada);
        return; // Retornar silenciosamente, o botão não deveria estar habilitado
    }
    
    // Determinar qual ID usar
    let operacaoIdFinal = operacaoId;
    
    // Se tem convenio_operacao_id, usar esse (já tem associação)
    if (convenioOperacaoId && convenioOperacaoId !== '' && convenioOperacaoId !== '0') {
        console.log('✅ Usando convenio_operacao_id existente:', convenioOperacaoId);
        operacaoIdFinal = null; // Não precisa do operacao_id se já tem a associação
    } else if (operacaoIdFinal) {
        console.log('✅ Usando operacao_id para criar associação:', operacaoIdFinal);
    } else {
        // Se chegou aqui, algo está errado, mas vamos tentar continuar se tiver convenioId e operacaoId
        console.warn('⚠️ operacaoIdFinal não encontrado, mas operacaoSelecionada existe');
        // Se operacaoSelecionada existe mas operacaoIdFinal não, pode ser que seja o convenioOperacaoId
        if (convenioOperacaoId && convenioOperacaoId !== '' && convenioOperacaoId !== '0') {
            console.log('✅ Usando convenio_operacao_id como fallback:', convenioOperacaoId);
            operacaoIdFinal = null;
        } else {
            console.error('❌ Não foi possível determinar operacaoId ou convenioOperacaoId');
            return; // Retornar silenciosamente
        }
    }
    
    // Desabilitar botão durante o upload
    $('#btnImportarSchema').prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin"></i> Importando...');
    
    const formData = new FormData();
    formData.append('arquivo', arquivo);
    formData.append('titulo', titulo);
    
    // Se já tem associação (convenio_operacao_id), enviar esse
    // Senão, enviar convenio_id + operacao_id para a API criar a associação
    if (convenioOperacaoId && convenioOperacaoId !== '' && convenioOperacaoId !== '0') {
        formData.append('convenio_operacao_id', convenioOperacaoId);
        console.log('📤 Enviando convenio_operacao_id:', convenioOperacaoId);
    } else if (operacaoIdFinal) {
        formData.append('convenio_id', convenioId);
        formData.append('operacao_id', operacaoIdFinal);
        console.log('📤 Enviando convenio_id + operacao_id para criar associação:', convenioId, operacaoIdFinal);
    } else {
        console.error('❌ Erro: Não foi possível determinar os dados para envio');
        alert('Erro: Não foi possível identificar os dados necessários. Tente novamente.');
        $('#btnImportarSchema').prop('disabled', false).html('<i class="bx bx-upload"></i> Importar Campos');
        return;
    }
    
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/operacional/contratos/api/schema/upload-csv/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            console.log('✅ Resposta da importação:', response);
            if (response.success) {
                // Se a associação foi criada, atualizar o select com o ID retornado
                if (response.data && response.data.convenio_operacao_id) {
                    const novoConvenioOperacaoId = response.data.convenio_operacao_id;
                    console.log('✅ Associação criada/encontrada com ID:', novoConvenioOperacaoId);
                    
                    // Atualizar o select de operação com o convenio_operacao_id
                    optionOperacao.attr('value', novoConvenioOperacaoId);
                    optionOperacao.attr('data-convenio-operacao-id', novoConvenioOperacaoId);
                    optionOperacao.text(optionOperacao.text().replace(' (Criar associação)', ''));
                }
                
                alert(response.message || 'CSV importado com sucesso!');
                
                // Limpar formulário
                $('#tituloSchema').val('');
                $('#arquivoSchema').val('');
                $('#selecaoConvenio').slideUp();
                $('#selecaoOperacao').slideUp();
                $('#selectConvenioSchema').val('').prop('disabled', true);
                $('#selectOperacaoSchema').val('').prop('disabled', true);
                verificarHabilitarImportarSchema();
                
                // Recarregar tabela de schemas importados
                carregarSchemasImportados();
                
                // Recarregar campos se estiver na seção de edição
                const convenioOperacaoIdEdicao = $('#selectConvenioOperacao').val();
                const convenioOperacaoIdFinal = response.data ? response.data.convenio_operacao_id : convenioOperacaoId;
                if (convenioOperacaoIdEdicao == convenioOperacaoIdFinal) {
                    carregarCamposSchema(convenioOperacaoIdFinal);
                }
            } else {
                alert('Erro: ' + response.message);
            }
            $('#btnImportarSchema').prop('disabled', false).html('<i class="bx bx-upload"></i> Importar Campos');
            verificarHabilitarImportarSchema();
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao importar schema:');
            console.error('Status:', status);
            console.error('Error:', error);
            console.error('Response:', xhr.responseText);
            let errorMsg = 'Erro ao importar CSV';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg = xhr.responseJSON.message;
            }
            alert(errorMsg);
            $('#btnImportarSchema').prop('disabled', false).html('<i class="bx bx-upload"></i> Importar Campos');
            verificarHabilitarImportarSchema();
        }
    });
}
