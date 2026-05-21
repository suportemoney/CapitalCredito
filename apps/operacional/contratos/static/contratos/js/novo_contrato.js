// JavaScript para novo contrato - Sistema de Wizard com Páginas
let convenioOperacaoIdAtual = null;
let bancoConvenioOperacaoIdAtual = null;

// Sistema de páginas/wizard
let paginaAtual = 1;
let totalPaginas = 1;
let contratoIdAtual = null;  // ID do contrato (rascunho)
let camposCarregados = [];   // Todos os campos do schema

$(document).ready(function() {
    carregarBancos();
    
    $('#banco').on('change', function() {
        const bancoId = $(this).val();
        resetarFormulario();
        if (bancoId) {
            carregarConvenios(bancoId);
        } else {
            $('#convenio').html('<option value="">Selecione primeiro o banco...</option>').prop('disabled', true);
            $('#operacao').html('<option value="">Selecione primeiro o convênio...</option>').prop('disabled', true);
        }
    });
    
    $('#convenio').on('change', function() {
        const convenioId = $(this).val();
        const bancoId = $('#banco').val();
        resetarFormulario();
        if (convenioId && bancoId) {
            carregarOperacoes(bancoId, convenioId);
        } else {
            $('#operacao').html('<option value="">Selecione primeiro o convênio...</option>').prop('disabled', true);
        }
    });
    
    $('#operacao').on('change', function() {
        const convenioOperacaoId = $(this).find(':selected').data('convenio-operacao-id');
        bancoConvenioOperacaoIdAtual = $(this).find(':selected').data('banco-convenio-operacao-id');
        resetarFormulario();
        if (convenioOperacaoId) {
            convenioOperacaoIdAtual = convenioOperacaoId;
            carregarCampos(convenioOperacaoId);
        }
    });
    
    // Botão de avançar/enviar
    $('#btn-avancar').on('click', function() {
        avancarPagina();
    });
});

function resetarFormulario() {
    paginaAtual = 1;
    totalPaginas = 1;
    contratoIdAtual = null;
    camposCarregados = [];
    $('#campos-formulario').hide().html('');
    $('#stepper-container').hide();
    $('#btn-avancar').hide();
}

function carregarBancos() {
    $.ajax({
        url: '/operacional/contratos/api/bancos/ativos/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                let options = '<option value="">Selecione o banco...</option>';
                response.data.forEach(function(banco) {
                    options += `<option value="${banco.id}">${banco.nome}</option>`;
                });
                $('#banco').html(options);
            }
        },
        error: function() {
            console.error('Erro ao carregar bancos');
        }
    });
}

function carregarConvenios(bancoId) {
    $.ajax({
        url: '/operacional/contratos/api/convenios/por-banco/',
        method: 'GET',
        data: { banco_id: bancoId },
        success: function(response) {
            if (response.success) {
                let options = '<option value="">Selecione o convênio...</option>';
                response.data.forEach(function(convenio) {
                    options += `<option value="${convenio.id}" data-banco-convenio-id="${convenio.banco_convenio_id}">${convenio.nome}</option>`;
                });
                $('#convenio').html(options).prop('disabled', false);
            }
        },
        error: function() {
            console.error('Erro ao carregar convênios');
        }
    });
}

function carregarOperacoes(bancoId, convenioId) {
    $.ajax({
        url: '/operacional/contratos/api/operacoes/por-convenio/',
        method: 'GET',
        data: { banco_id: bancoId, convenio_id: convenioId },
        success: function(response) {
            if (response.success) {
                let options = '<option value="">Selecione a operação...</option>';
                if (response.data.length === 0) {
                    options = '<option value="">Nenhuma operação ativa para este banco+convênio</option>';
                } else {
                    response.data.forEach(function(operacao) {
                        options += `<option value="${operacao.id}" 
                            data-convenio-operacao-id="${operacao.convenio_operacao_id}"
                            data-titulo-schema="${operacao.titulo_schema || ''}">${operacao.nome} - ${operacao.titulo_schema || 'Schema'}</option>`;
                    });
                }
                $('#operacao').html(options).prop('disabled', false);
            } else {
                $('#operacao').html('<option value="">Erro ao carregar operações</option>').prop('disabled', true);
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar operações:', xhr.responseText);
            $('#operacao').html('<option value="">Erro ao carregar operações</option>').prop('disabled', true);
        }
    });
}

function carregarCampos(convenioOperacaoId) {
    console.log('=== carregarCampos (novo_contrato.js) ===');
    console.log('📥 convenioOperacaoId:', convenioOperacaoId);
    
    $.ajax({
        url: '/operacional/contratos/api/schema/campos/',
        method: 'GET',
        data: { convenio_operacao_id: convenioOperacaoId },
        success: function(response) {
            console.log('✅ Resposta da API:');
            console.log('   Success:', response.success);
            console.log('   Total campos:', response.data ? response.data.length : 0);
            console.log('   total_paginas (da API):', response.total_paginas);
            
            if (response.success) {
                camposCarregados = response.data;
                totalPaginas = response.total_paginas || 1;
                paginaAtual = 1;
                
                console.log('📊 Configuração:');
                console.log('   totalPaginas:', totalPaginas);
                console.log('   paginaAtual:', paginaAtual);
                
                // Debug: verificar páginas dos campos
                const paginasUnicas = [...new Set(response.data.map(c => c.pagina || 1))].sort((a, b) => a - b);
                console.log('📑 Páginas únicas nos campos:', paginasUnicas);
                console.log('   Campos por página:', paginasUnicas.map(p => `Pág ${p}: ${response.data.filter(c => (c.pagina || 1) === p).length} campos`));
                
                renderizarPaginas(camposCarregados, totalPaginas);
                mostrarPagina(1);
                atualizarStepper();
                atualizarBotao();
                
                $('#campos-formulario').show();
                $('#stepper-container').show();
                $('#btn-avancar').show();
                
                console.log('✅ Renderização completa!');
                console.log('   #campos-formulario visible:', $('#campos-formulario').is(':visible'));
                console.log('   #stepper-container visible:', $('#stepper-container').is(':visible'));
                console.log('   #btn-avancar visible:', $('#btn-avancar').is(':visible'));
            } else {
                console.error('❌ API retornou success=false:', response.message);
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Erro ao carregar campos:');
            console.error('   Status:', status);
            console.error('   Error:', error);
            console.error('   Response:', xhr.responseText);
        }
    });
}

function renderizarPaginas(campos, totalPaginas) {
    console.log('=== renderizarPaginas ===');
    console.log('📊 Total campos:', campos.length);
    console.log('📑 Total páginas:', totalPaginas);
    
    // Agrupar campos por página
    const camposPorPagina = {};
    for (let i = 1; i <= totalPaginas; i++) {
        camposPorPagina[i] = [];
    }
    
    campos.forEach(function(campo) {
        const pag = campo.pagina || 1;
        if (!camposPorPagina[pag]) {
            camposPorPagina[pag] = [];
        }
        camposPorPagina[pag].push(campo);
    });
    
    console.log('📦 Campos por página:');
    Object.keys(camposPorPagina).forEach(p => {
        console.log(`   Página ${p}: ${camposPorPagina[p].length} campos`);
    });
    
    let html = '';
    
    // Renderizar cada página
    for (let pag = 1; pag <= totalPaginas; pag++) {
        const camposDaPagina = camposPorPagina[pag] || [];
        const display = pag === 1 ? 'block' : 'none';
        
        console.log(`🔧 Renderizando página ${pag} (${camposDaPagina.length} campos, display: ${display})`);
        
        html += `<div class="pagina-campos" data-pagina="${pag}" style="display: ${display};">`;
        
        // Cabeçalho da página
        if (totalPaginas > 1) {
            html += `<div class="alert alert-primary mb-4">
                <h5 class="mb-0"><i class="bx bx-file me-2"></i>Página ${pag} de ${totalPaginas}</h5>
            </div>`;
        }
        
        // Agrupar campos da página por categoria
        const camposPorCategoria = {};
        const menorOrdemCategoria = {}; // Para ordenar categorias pela menor ordem
        
        camposDaPagina.forEach(function(campo) {
            if (!camposPorCategoria[campo.category]) {
                camposPorCategoria[campo.category] = [];
                menorOrdemCategoria[campo.category] = campo.ordem || 999;
            }
            camposPorCategoria[campo.category].push(campo);
            // Guardar a menor ordem da categoria
            if ((campo.ordem || 999) < menorOrdemCategoria[campo.category]) {
                menorOrdemCategoria[campo.category] = campo.ordem || 999;
            }
        });
        
        // Ordenar categorias pela MENOR ORDEM dos campos (não alfabeticamente)
        const categoriasOrdenadas = Object.keys(camposPorCategoria).sort((a, b) => {
            return menorOrdemCategoria[a] - menorOrdemCategoria[b];
        });
        
        // Ordenar campos dentro de cada categoria
        categoriasOrdenadas.forEach(function(cat) {
            camposPorCategoria[cat].sort((a, b) => (a.ordem || 0) - (b.ordem || 0));
        });
        
        // Renderizar campos por categoria
        categoriasOrdenadas.forEach(function(categoria) {
            html += `<div class="categoria-campos mb-4">
                <h5 class="mb-3 border-bottom pb-2">${categoria.replace(/_/g, ' ').toUpperCase()}</h5>
                <div class="row">`;
            
            camposPorCategoria[categoria].forEach(function(campo) {
                html += renderizarCampo(campo);
            });
            
            html += `</div></div>`;
        });
        
        if (camposDaPagina.length === 0) {
            html += `<div class="alert alert-warning">Nenhum campo configurado para esta página.</div>`;
        }
        
        html += `</div>`;
    }
    
    console.log('✅ HTML gerado, aplicando no DOM...');
    $('#campos-formulario').html(html);
    
    // Verificar se as páginas foram criadas
    const paginasCriadas = $('.pagina-campos').length;
    console.log(`✅ ${paginasCriadas} páginas criadas no DOM`);
}

function mostrarPagina(numeroPagina) {
    // Salvar dados da página atual antes de trocar
    if (paginaAtual !== numeroPagina) {
        salvarDadosPaginaLocal();
    }
    
    // Esconder todas as páginas
    $('.pagina-campos').hide();
    // Mostrar página específica
    $(`.pagina-campos[data-pagina="${numeroPagina}"]`).show();
    paginaAtual = numeroPagina;
    
    // Carregar dados salvos da página
    carregarDadosPaginaLocal(numeroPagina);
    
    atualizarStepper();
    atualizarBotao();
}

function atualizarStepper() {
    const progresso = (paginaAtual / totalPaginas) * 100;
    console.log('=== atualizarStepper ===');
    console.log('   Progresso:', progresso.toFixed(1) + '%');
    
    $('#progress-bar')
        .css('width', progresso + '%')
        .attr('aria-valuenow', progresso)
        .text(`Etapa ${paginaAtual} de ${totalPaginas}`);
    
    $('#badge-pagina').text(`Etapa ${paginaAtual} de ${totalPaginas}`);
}

function atualizarBotao() {
    console.log('=== atualizarBotao ===');
    console.log('   paginaAtual:', paginaAtual);
    console.log('   totalPaginas:', totalPaginas);
    
    // Mostrar/ocultar botão voltar
    if (paginaAtual > 1) {
        $('#btn-voltar').show();
    } else {
        $('#btn-voltar').hide();
    }
    
    if (paginaAtual >= totalPaginas) {
        console.log('   → Última página: botão ENVIAR');
        $('#btn-avancar')
            .html('<i class="bx bx-check me-2"></i>Enviar Contrato')
            .removeClass('btn-primary')
            .addClass('btn-success');
    } else {
        console.log('   → Página intermediária: botão PRÓXIMO');
        $('#btn-avancar')
            .html('Próximo <i class="bx bx-right-arrow-alt ms-2"></i>')
            .removeClass('btn-success')
            .addClass('btn-primary');
    }
}

function validarPaginaAtual() {
    // Validar campos obrigatórios da página atual
    let valido = true;
    const pagina = $(`.pagina-campos[data-pagina="${paginaAtual}"]`);
    
    pagina.find('input[required], select[required], textarea[required]').each(function() {
        const input = $(this);
        const tipo = input.attr('type');
        
        if (tipo === 'file') {
            // Validar arquivo obrigatório
            const files = this.files;
            if (!files || files.length === 0) {
                input.addClass('is-invalid');
                valido = false;
                console.log(`[DEBUG validarPaginaAtual] Campo de arquivo obrigatório não preenchido: ${input.attr('name')}`);
            } else {
                input.removeClass('is-invalid');
                console.log(`[DEBUG validarPaginaAtual] Campo de arquivo obrigatório OK: ${input.attr('name')}, arquivos: ${files.length}`);
            }
        } else if (tipo === 'checkbox') {
            // Checkbox obrigatório
            if (!input.is(':checked')) {
                input.addClass('is-invalid');
                valido = false;
            } else {
                input.removeClass('is-invalid');
            }
        } else {
            // Campo de texto/select/textarea
            const valor = input.val();
            if (!valor || valor.trim() === '') {
                input.addClass('is-invalid');
                valido = false;
            } else {
                input.removeClass('is-invalid');
            }
        }
    });
    
    if (!valido) {
        alert('Preencha todos os campos obrigatórios antes de avançar.');
    }
    
    return valido;
}

function coletarDadosPaginaAtual() {
    const dados = {};
    const pagina = $(`.pagina-campos[data-pagina="${paginaAtual}"]`);
    
    pagina.find('input, select, textarea').each(function() {
        const name = $(this).attr('name');
        if (!name || name === 'csrfmiddlewaretoken') return;
        
        // IGNORAR campos de arquivo - serão enviados via FormData/request.FILES
        if ($(this).attr('type') === 'file') {
            return; // Pular inputs de arquivo
        }
        
        const parts = name.split('__');
        if (parts.length === 2) {
            const [category, label] = parts;
            if (!dados[category]) {
                dados[category] = {};
            }
            
            if ($(this).is(':checkbox')) {
                dados[category][label] = $(this).is(':checked');
            } else if ($(this).is('select[multiple]')) {
                dados[category][label] = $(this).val() || [];
            } else if (name.endsWith('[]')) {
                // MULTIINPUT
                const baseName = name.replace('[]', '');
                const baseParts = baseName.split('__');
                if (baseParts.length === 2) {
                    const [baseCategory, baseLabel] = baseParts;
                    if (!dados[baseCategory]) {
                        dados[baseCategory] = {};
                    }
                    if (!dados[baseCategory][baseLabel]) {
                        dados[baseCategory][baseLabel] = [];
                    }
                }
            } else {
                const value = $(this).val();
                // Não incluir valores vazios (exceto para campos numéricos que podem ser 0)
                if (value !== null && value !== undefined && value !== '') {
                    dados[category][label] = value;
                }
            }
        }
    });
    
    // Processar MULTIINPUT (arrays de objetos) da página atual
    pagina.find('.multiinput-item').each(function() {
        const inputs = $(this).find('input[name$="[]"]');
        if (inputs.length > 0) {
            const firstInput = inputs.first();
            const name = firstInput.attr('name').replace('[]', '');
            const parts = name.split('__');
            if (parts.length === 2) {
                const [category, label] = parts;
                if (!dados[category]) {
                    dados[category] = {};
                }
                if (!dados[category][label]) {
                    dados[category][label] = [];
                }
                
                const item = {};
                inputs.each(function() {
                    const subCampo = $(this).data('subcampo');
                    const value = $(this).val();
                    if (value) {
                        item[subCampo] = value;
                    }
                });
                if (Object.keys(item).length > 0) {
                    dados[category][label].push(item);
                }
            }
        }
    });
    
    return dados;
}

function voltarPagina() {
    if (paginaAtual > 1) {
        // Salvar dados da página atual antes de voltar
        salvarDadosPaginaLocal();
        
        // Voltar para página anterior
        paginaAtual--;
        mostrarPagina(paginaAtual);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function salvarDadosPaginaLocal() {
    // Salvar dados da página atual no armazenamento local (sem enviar ao servidor)
    const dadosPagina = coletarDadosPaginaAtual();
    const key = `contrato_rascunho_pagina_${paginaAtual}`;
    localStorage.setItem(key, JSON.stringify(dadosPagina));
    
    // Salvar arquivos também (como FileList não pode ser serializado, vamos guardar referência)
    const paginaAtualElement = $(`.pagina-campos[data-pagina="${paginaAtual}"]`);
    const arquivosDaPagina = paginaAtualElement.find('input[type="file"]');
    const arquivosInfo = [];
    
    arquivosDaPagina.each(function() {
        const input = $(this);
        if (this.files && this.files.length > 0) {
            arquivosInfo.push({
                name: input.attr('name'),
                files_count: this.files.length
            });
        }
    });
    
    if (arquivosInfo.length > 0) {
        localStorage.setItem(`arquivos_pagina_${paginaAtual}`, JSON.stringify(arquivosInfo));
    }
}

function carregarDadosPaginaLocal(numeroPagina) {
    // Carregar dados salvos localmente
    const key = `contrato_rascunho_pagina_${numeroPagina}`;
    const dadosSalvos = localStorage.getItem(key);
    
    if (dadosSalvos) {
        const dados = JSON.parse(dadosSalvos);
        // Preencher campos com dados salvos
        for (const [categoria, campos] of Object.entries(dados)) {
            if (typeof campos === 'object' && campos !== null && !Array.isArray(campos)) {
                for (const [campo, valor] of Object.entries(campos)) {
                    const input = $(`[name="${categoria}__${campo}"]`);
                    if (input.length > 0) {
                        if (input.attr('type') === 'checkbox') {
                            input.prop('checked', valor === true || valor === 'true');
                        } else if (input.is('select')) {
                            input.val(valor);
                        } else {
                            input.val(valor);
                        }
                    }
                }
            }
        }
    }
}

function avancarPagina() {
    // Validar página atual (apenas na última página)
    const isUltimaPagina = paginaAtual >= totalPaginas;
    
    if (isUltimaPagina) {
        // Última página - validar tudo antes de finalizar
        if (!validarPaginaAtual()) {
            return;
        }
    } else {
        // Páginas intermediárias - validar apenas campos obrigatórios
        if (!validarPaginaAtual()) {
            return;
        }
    }
    
    // Coletar dados da página atual
    const dadosPagina = coletarDadosPaginaAtual();
    
    // Verificar se tem banco e convenio_operacao selecionados
    const bancoId = $('#banco').val();
    if (!bancoId || !convenioOperacaoIdAtual) {
        alert('Selecione banco, convênio e operação');
        return;
    }
    
    // Desabilitar botão durante envio
    $('#btn-avancar').prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin me-2"></i>Salvando...');
    
    // Verificar se é última página
    const isFinalizar = paginaAtual >= totalPaginas;
    
    // Coletar arquivos da página ATUAL (arquivos são processados na página em que estão)
    // TENTAR MÚLTIPLOS SELETORES para garantir que encontramos os inputs
    const paginaAtualElement = $(`.pagina-campos[data-pagina="${paginaAtual}"]`);
    let arquivosDaPagina = paginaAtualElement.find('input[type="file"]');
    
    // Se não encontrou, tentar buscar diretamente no DOM
    if (arquivosDaPagina.length === 0) {
        console.log(`[DEBUG avancarPagina] ⚠️ Tentativa 1 falhou, tentando buscar todos os inputs file e filtrar por página`);
        const todosInputsFile = $('#campos-formulario').find('input[type="file"]');
        arquivosDaPagina = todosInputsFile.filter(function() {
            const input = $(this);
            const parentPagina = input.closest('.pagina-campos');
            return parentPagina.length > 0 && parentPagina.data('pagina') == paginaAtual;
        });
    }
    
    const arquivosParaEnviar = [];
    
    console.log(`[DEBUG avancarPagina] ============================================`);
    console.log(`[DEBUG avancarPagina] Procurando arquivos na página ${paginaAtual}`);
    console.log(`[DEBUG avancarPagina] Seletor: .pagina-campos[data-pagina="${paginaAtual}"]`);
    console.log(`[DEBUG avancarPagina] Elemento encontrado:`, paginaAtualElement.length > 0 ? 'SIM' : 'NÃO');
    console.log(`[DEBUG avancarPagina] Total de inputs file na página: ${arquivosDaPagina.length}`);
    console.log(`[DEBUG avancarPagina] Todos os inputs file na página (debug):`, arquivosDaPagina.map(function() { return $(this).attr('name'); }).get());
    
    if (arquivosDaPagina.length === 0) {
        console.log(`[DEBUG avancarPagina] ⚠️ ATENÇÃO: Nenhum input[type="file"] encontrado na página ${paginaAtual}`);
        console.log(`[DEBUG avancarPagina] HTML da página (primeiros 500 chars):`, paginaAtualElement.html() ? paginaAtualElement.html().substring(0, 500) : 'VAZIO');
        
        // Tentar buscar todos os inputs file no documento inteiro para debug
        const todosInputsFileDoc = $('input[type="file"]');
        console.log(`[DEBUG avancarPagina] 🔍 DEBUG: Total de inputs file no documento inteiro: ${todosInputsFileDoc.length}`);
        todosInputsFileDoc.each(function() {
            const input = $(this);
            const parent = input.closest('.pagina-campos');
            console.log(`[DEBUG avancarPagina]   - Input: name="${input.attr('name')}", data-pagina pai: ${parent.length > 0 ? parent.data('pagina') : 'NÃO TEM PAI .pagina-campos'}`);
        });
    }
    
    arquivosDaPagina.each(function(index) {
        const input = $(this);
        const name = input.attr('name');
        const isMultiple = input.attr('multiple') !== undefined;
        
        // IMPORTANTE: Verificar files do elemento DOM nativo, não do jQuery
        const domElement = this; // Elemento DOM nativo
        const files = domElement.files; // FileList nativo
        
        console.log(`[DEBUG avancarPagina] --- Campo ${index + 1} ---`);
        console.log(`[DEBUG avancarPagina]   name: ${name}`);
        console.log(`[DEBUG avancarPagina]   multiple: ${isMultiple}`);
        console.log(`[DEBUG avancarPagina]   domElement:`, domElement);
        console.log(`[DEBUG avancarPagina]   files (FileList):`, files);
        console.log(`[DEBUG avancarPagina]   files.length: ${files ? files.length : 0}`);
        console.log(`[DEBUG avancarPagina]   input.is(':visible'): ${input.is(':visible')}`);
        console.log(`[DEBUG avancarPagina]   input.parent().is(':visible'): ${input.parent().is(':visible')}`);
        
        // Verificar se tem arquivos (mesmo que o input esteja oculto)
        if (files && files.length > 0) {
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                console.log(`[DEBUG avancarPagina] ✅ Arquivo ${i+1}/${files.length}: ${file.name} (${file.size} bytes, type: ${file.type})`);
                arquivosParaEnviar.push({
                    name: name,
                    file: file
                });
            }
        } else {
            console.log(`[DEBUG avancarPagina] ⚠️ Campo ${name} não tem arquivos selecionados`);
            console.log(`[DEBUG avancarPagina]   Valor do input:`, input.val());
            console.log(`[DEBUG avancarPagina]   files é null/undefined:`, files === null || files === undefined);
        }
    });
    
    console.log(`[DEBUG avancarPagina] ============================================`);
    console.log(`[DEBUG avancarPagina] Página ${paginaAtual}/${totalPaginas} ${isFinalizar ? '(FINALIZANDO)' : ''}`);
    console.log(`[DEBUG avancarPagina] Total de arquivos para enviar: ${arquivosParaEnviar.length}`);
    
    if (arquivosParaEnviar.length > 0) {
        // Usar FormData para enviar arquivos
        const formData = new FormData();
        formData.append('contrato_id', contratoIdAtual || '');
        formData.append('banco_id', bancoId);
        formData.append('convenio_operacao_id', convenioOperacaoIdAtual);
        formData.append('pagina_atual', paginaAtual);
        formData.append('total_paginas', totalPaginas);
        formData.append('dados_pagina', JSON.stringify(dadosPagina));
        if (isFinalizar) {
            formData.append('finalizar', 'true'); // Marca que está finalizando
        }
        
        // Adicionar arquivos da página atual
        console.log(`[DEBUG avancarPagina] Preparando FormData com ${arquivosParaEnviar.length} arquivo(s)`);
        arquivosParaEnviar.forEach((item, idx) => {
            formData.append(item.name, item.file);
            console.log(`[DEBUG avancarPagina] ✅ Arquivo ${idx+1}/${arquivosParaEnviar.length} adicionado ao FormData: ${item.name} -> ${item.file.name} (${item.file.size} bytes)`);
        });
        
        // Verificar FormData antes de enviar
        console.log(`[DEBUG avancarPagina] FormData criado. Enviando requisição...`);
        for (let pair of formData.entries()) {
            if (pair[1] instanceof File) {
                console.log(`[DEBUG avancarPagina] FormData entry: ${pair[0]} = [File] ${pair[1].name} (${pair[1].size} bytes)`);
            } else {
                console.log(`[DEBUG avancarPagina] FormData entry: ${pair[0]} = ${pair[1]}`);
            }
        }
        
        $.ajax({
            url: '/operacional/contratos/api/contratos/salvar-pagina/',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                console.log(`[DEBUG avancarPagina] ✅ Resposta do servidor:`, response);
                handleSalvarPaginaSuccess(response);
            },
            error: function(xhr, status, error) {
                console.log(`[DEBUG avancarPagina] ❌ Erro na requisição:`, xhr, status, error);
                handleSalvarPaginaError(xhr);
            }
        });
    } else {
        // Sem arquivos - enviar apenas JSON
        const dadosEnvio = {
            contrato_id: contratoIdAtual,
            banco_id: parseInt(bancoId),
            convenio_operacao_id: parseInt(convenioOperacaoIdAtual),
            pagina_atual: paginaAtual,
            total_paginas: totalPaginas,
            dados_pagina: dadosPagina
        };
        
        if (isFinalizar) {
            dadosEnvio.finalizar = true;
        }
        
        $.ajax({
            url: '/operacional/contratos/api/contratos/salvar-pagina/',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(dadosEnvio),
            headers: {
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
            },
            success: handleSalvarPaginaSuccess,
            error: handleSalvarPaginaError
        });
    }
    
    // Se não é última página, o código acima já processou tudo
}

function handleSalvarPaginaSuccess(response) {
    $('#btn-avancar').prop('disabled', false);
    
    console.log(`[DEBUG handleSalvarPaginaSuccess] ============================================`);
    console.log(`[DEBUG handleSalvarPaginaSuccess] Resposta recebida:`, response);
    
    if (response.success) {
        // Guardar ID do contrato (rascunho)
        contratoIdAtual = response.data.contrato_id;
        console.log(`[DEBUG handleSalvarPaginaSuccess] Contrato ID: ${contratoIdAtual}`);
        console.log(`[DEBUG handleSalvarPaginaSuccess] Finalizado: ${response.data.finalizado}`);
        console.log(`[DEBUG handleSalvarPaginaSuccess] is_rascunho: ${response.data.is_rascunho}`);
        
        if (response.data.finalizado) {
            // Contrato finalizado - redirecionar
            console.log(`[DEBUG handleSalvarPaginaSuccess] ✅ CONTRATO FINALIZADO!`);
            console.log(`[DEBUG handleSalvarPaginaSuccess] Redirecionando para CRM em 2 segundos...`);
            console.log(`[DEBUG handleSalvarPaginaSuccess] ============================================`);
            
            setTimeout(() => {
                alert('Contrato enviado com sucesso!');
                window.location.href = '/operacional/contratos/acompanhamento-crm/';
            }, 2000);
        } else {
            // Avançar para próxima página e carregar dados salvos
            const proximaPagina = response.data.proxima_pagina;
            console.log(`[DEBUG handleSalvarPaginaSuccess] Avançando para página ${proximaPagina}`);
            mostrarPagina(proximaPagina);
            
            // Carregar dados do servidor se o contrato já existe
            if (contratoIdAtual) {
                carregarDadosDoServidor(proximaPagina);
            }
            
            // Scroll para topo
            $('html, body').animate({ scrollTop: 0 }, 300);
            console.log(`[DEBUG handleSalvarPaginaSuccess] ============================================`);
        }
    } else {
        console.log(`[DEBUG handleSalvarPaginaSuccess] ❌ ERRO: ${response.message}`);
        alert('Erro: ' + response.message);
        atualizarBotao();
    }
}

function carregarDadosDoServidor(pagina) {
    if (!contratoIdAtual) return;
    
    console.log(`[DEBUG] Carregando dados do servidor para página ${pagina}, contrato ${contratoIdAtual}`);
    
    $.ajax({
        url: `/operacional/contratos/api/contratos/${contratoIdAtual}/`,
        method: 'GET',
        success: function(response) {
            if (response.success && response.data.dados_contrato) {
                const dadosContrato = response.data.dados_contrato;
                const paginaElement = $(`.pagina-campos[data-pagina="${pagina}"]`);
                
                // Preencher campos da página com dados do servidor
                for (const [categoria, campos] of Object.entries(dadosContrato)) {
                    if (typeof campos === 'object' && campos !== null && !Array.isArray(campos)) {
                        for (const [campo, valor] of Object.entries(campos)) {
                            const input = paginaElement.find(`[name="${categoria}__${campo}"]`);
                            if (input.length > 0) {
                                if (input.attr('type') === 'file') {
                                    // Para arquivos, mostrar URL se já existe
                                    if (typeof valor === 'string' && valor.startsWith('/media/')) {
                                        const nomeArquivo = valor.split('/').pop();
                                        input.closest('.mb-3').find('.text-muted').html(
                                            `<span class="text-success"><i class="bx bx-check"></i> Arquivo salvo: ${nomeArquivo}</span>`
                                        );
                                    }
                                } else if (input.attr('type') === 'checkbox') {
                                    input.prop('checked', valor === true || valor === 'true' || valor === '1');
                                } else if (input.is('select')) {
                                    input.val(valor);
                                } else {
                                    input.val(valor);
                                }
                            }
                        }
                    }
                }
                console.log(`[DEBUG] Dados da página ${pagina} carregados do servidor`);
            }
        },
        error: function() {
            console.log(`[DEBUG] Erro ao carregar dados do servidor para página ${pagina}`);
        }
    });
}

function handleSalvarPaginaError(xhr) {
    $('#btn-avancar').prop('disabled', false);
    atualizarBotao();
    
    let errorMsg = 'Erro ao salvar página';
    if (xhr.responseJSON && xhr.responseJSON.message) {
        errorMsg = xhr.responseJSON.message;
    }
    alert(errorMsg);
}

function renderizarCampo(campo) {
    const campoId = campo.id || campo.label.replace(/\s+/g, '_').toLowerCase();
    const campoName = `${campo.category}__${campo.label}`;
    const required = campo.required ? 'required' : '';
    const requiredLabel = campo.required ? '<span class="text-danger">*</span>' : '';
    let html = '';
    
    switch(campo.type) {
        case 'TEXT':
        case 'EMAIL':
        case 'TEL':
        case 'PASSWORD':
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <input type="${campo.type.toLowerCase()}" class="form-control" id="campo_${campoId}" 
                    name="${campoName}" ${required} 
                    placeholder="${campo.placeholder || ''}">
            </div>`;
            break;
        case 'NUMBER':
        case 'DECIMAL':
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <input type="number" class="form-control" id="campo_${campoId}" 
                    name="${campoName}" ${required} 
                    placeholder="${campo.placeholder || ''}" 
                    step="${campo.type === 'DECIMAL' ? '0.01' : '1'}">
            </div>`;
            break;
        case 'DATE':
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <input type="date" class="form-control" id="campo_${campoId}" 
                    name="${campoName}" ${required}>
            </div>`;
            break;
        case 'TEXTAREA':
            html = `<div class="col-md-12 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <textarea class="form-control" id="campo_${campoId}" 
                    name="${campoName}" ${required} 
                    placeholder="${campo.placeholder || ''}" rows="3"></textarea>
            </div>`;
            break;
        case 'SELECT':
            let options = `<option value="">${campo.placeholder || 'Selecione...'}</option>`;
            if (campo.choices && campo.choices.length > 0) {
                campo.choices.forEach(function(choice) {
                    options += `<option value="${choice}">${choice}</option>`;
                });
            }
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <select class="form-select" id="campo_${campoId}" 
                    name="${campoName}" ${required}>
                    ${options}
                </select>
            </div>`;
            break;
        case 'CHECKBOX':
            html = `<div class="col-md-6 mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="campo_${campoId}" 
                        name="${campoName}" ${required}>
                    <label class="form-check-label" for="campo_${campoId}">
                        ${campo.label} ${requiredLabel}
                    </label>
                </div>
            </div>`;
            break;
        case 'MULTISELECTOR':
            let multiOptions = `<option value="">${campo.placeholder || 'Selecione...'}</option>`;
            if (campo.choices && campo.choices.length > 0) {
                campo.choices.forEach(function(choice) {
                    multiOptions += `<option value="${choice}">${choice}</option>`;
                });
            }
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <select class="form-select" id="campo_${campoId}" 
                    name="${campoName}" ${required}>
                    ${multiOptions}
                </select>
            </div>`;
            break;
        case 'FILE':
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <input type="file" class="form-control" id="campo_${campoId}" 
                    name="${campoName}" ${required}>
                <small class="text-muted">Upload de arquivo único</small>
            </div>`;
            break;
        case 'MULTIFILE':
            html = `<div class="col-md-6 mb-3">
                <label for="campo_${campoId}" class="form-label">${campo.label} ${requiredLabel}</label>
                <input type="file" class="form-control" id="campo_${campoId}" 
                    name="${campoName}" multiple ${required}>
                <small class="text-muted">Upload de múltiplos arquivos</small>
            </div>`;
            break;
        case 'MULTIINPUT':
            const subCampos = campo.choices || [];
            const campoLabelFormatado = campo.label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html = `<div class="col-md-12 mb-4">
                <label class="form-label fw-bold">${campoLabelFormatado} ${requiredLabel}</label>
                <div id="multiinput_${campoId}_container">
                    <div class="multiinput-item border rounded p-3 mb-2">
                        <div class="d-flex align-items-center gap-2 flex-wrap">`;
            subCampos.forEach(function(subCampo, index) {
                const subCampoLabel = subCampo.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `<div class="flex-grow-1" style="min-width: 150px;">
                    <label class="form-label small mb-1">${subCampoLabel}:</label>
                    <input type="text" class="form-control form-control-sm" 
                        name="${campoName}[]" 
                        data-subcampo="${subCampo}"
                        placeholder="${subCampoLabel}">`;
                html += `</div>`;
                if (index < subCampos.length - 1) {
                    html += `<span class="text-muted align-self-end mb-2">|</span>`;
                }
            });
            html += `<div class="ms-auto">
                <button type="button" class="btn btn-sm btn-danger" onclick="removerMultiInputItem('${campoId}', this)">
                    <i class="bx bx-x"></i>
                </button>
            </div>`;
            html += `</div></div></div>
                <button type="button" class="btn btn-sm btn-primary" onclick="adicionarMultiInputItem('${campoId}', '${campoName}', ${JSON.stringify(subCampos).replace(/"/g, '&quot;')})">
                    <i class="bx bx-plus"></i> Adicionar Item
                </button>
            </div>`;
            break;
    }
    
    return html;
}

function adicionarMultiInputItem(campoId, campoName, subCampos) {
    const container = $(`#multiinput_${campoId}_container`);
    
    let html = `<div class="multiinput-item border rounded p-3 mb-2">
        <div class="d-flex align-items-center gap-2 flex-wrap">`;
    
    subCampos.forEach(function(subCampo, index) {
        const subCampoLabel = subCampo.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += `<div class="flex-grow-1" style="min-width: 150px;">
            <label class="form-label small mb-1">${subCampoLabel}:</label>
            <input type="text" class="form-control form-control-sm" 
                name="${campoName}[]" 
                data-subcampo="${subCampo}"
                placeholder="${subCampoLabel}">`;
        html += `</div>`;
        if (index < subCampos.length - 1) {
            html += `<span class="text-muted align-self-end mb-2">|</span>`;
        }
    });
    
    html += `<div class="ms-auto">
        <button type="button" class="btn btn-sm btn-danger" onclick="removerMultiInputItem('${campoId}', this)">
            <i class="bx bx-x"></i>
        </button>
    </div>`;
    html += `</div></div>`;
    container.append(html);
}

function removerMultiInputItem(campoId, button) {
    if ($(`#multiinput_${campoId}_container .multiinput-item`).length > 1) {
        $(button).closest('.multiinput-item').remove();
    } else {
        alert('É necessário ter pelo menos um item');
    }
}
