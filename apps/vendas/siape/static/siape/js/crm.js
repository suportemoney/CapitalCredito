// SIAPE URLs atualizadas para rota raiz - v2
$(document).ready(function() {
    carregarFuncionarios();
    carregarKanban();
    
    $('#sim-coef-crm, #sim-parcela-crm').on('input', function() {
        const coef = parseFloat($('#sim-coef-crm').val()) || 0;
        const parcela = parseFloat($('#sim-parcela-crm').val()) || 0;
        if (coef > 0 && parcela > 0) {
            const af = parcela * (coef / 100);
            $('#sim-af-crm').val(af.toFixed(2));
        } else {
            $('#sim-af-crm').val('');
        }
    });
    
    // Máscara para CPF
    $('#filtro-cpf').on('input', function() {
        let valor = $(this).val().replace(/\D/g, '');
        if (valor.length <= 11) {
            valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
            valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
            valor = valor.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
            $(this).val(valor);
        }
    });
});

function carregarFuncionarios() {
    $.ajax({
        url: '/api/crm/listar-funcionarios/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const select = $('#filtro-funcionario');
                select.empty();
                select.append('<option value="">Todos</option>');
                response.data.forEach(function(func) {
                    select.append(`<option value="${func.id}">${escapeHtml(func.nome)}</option>`);
                });
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar funcionários:', xhr);
        }
    });
}

function carregarKanban() {
    const params = new URLSearchParams();
    
    const nome = $('#filtro-nome').val().trim();
    const cpf = $('#filtro-cpf').val().trim();
    const dataInicio = $('#filtro-data-inicio').val();
    const dataFim = $('#filtro-data-fim').val();
    const funcionarioId = $('#filtro-funcionario').val();
    
    if (nome) params.append('nome_cliente', nome);
    if (cpf) params.append('cpf_cliente', cpf);
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (funcionarioId) params.append('funcionario_id', funcionarioId);
    
    const url = '/api/crm/kanban/' + (params.toString() ? '?' + params.toString() : '');
    
    $.ajax({
        url: url,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                exibirKanban(response.data);
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao carregar kanban: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function aplicarFiltros() {
    carregarKanban();
}

function limparFiltros() {
    $('#filtro-nome').val('');
    $('#filtro-cpf').val('');
    $('#filtro-data-inicio').val('');
    $('#filtro-data-fim').val('');
    $('#filtro-funcionario').val('');
    carregarKanban();
}

function exibirKanban(tabulacoes) {
    const container = $('#crm-columns');
    container.empty();
    
    if (tabulacoes.length === 0) {
        container.append('<div class="col-12"><div class="alert alert-info">Nenhuma tabulação cadastrada. Contate o administrador.</div></div>');
        return;
    }
    
    tabulacoes.forEach(function(tab) {
        const col = $(`
            <div class="crm-column-wrapper">
                <div class="card crm-column" style="border-top: 4px solid ${tab.cor};">
                    <div class="card-header" style="background-color: ${tab.cor}; color: white;">
                        <h6 class="mb-0">${escapeHtml(tab.nome)}</h6>
                        <small>${tab.cards.length} card(s)</small>
                    </div>
                    <div class="card-body crm-cards-container" data-tabulacao-id="${tab.id}" data-tabulacao-nome="${tab.nome.toUpperCase()}">
                        ${gerarCards(tab.cards)}
                    </div>
                </div>
            </div>
        `);
        container.append(col);
    });
    
    configurarDragAndDrop();
}

function gerarCards(cards) {
    if (cards.length === 0) {
        return '<div class="text-center text-muted p-3">Nenhum card</div>';
    }
    
    let html = '';
    cards.forEach(function(card) {
        html += `
            <div class="card crm-card mb-2" data-controle-id="${card.id}" data-cpf="${card.cpf}" style="cursor: pointer;" onclick="abrirFichaCliente('${card.cpf}')">
                <div class="card-body p-2">
                    <h6 class="card-title mb-1">${escapeHtml(card.nome)}</h6>
                    <p class="card-text mb-1"><small>CPF: ${formatarCPF(card.cpf)}</small></p>
                    <p class="card-text mb-0"><small><i class='bx bx-calendar'></i> ${card.data_contato} ${card.hora_contato}</small></p>
                </div>
            </div>
        `;
    });
    return html;
}

function configurarDragAndDrop() {
    $('.crm-card').draggable({
        revert: function(dropTarget) {
            if (!dropTarget) {
                return true;
            }
            const card = $(this);
            const tabulacaoAtualId = card.closest('.crm-cards-container').data('tabulacao-id');
            const novaTabulacaoId = dropTarget.data('tabulacao-id');
            return novaTabulacaoId === tabulacaoAtualId;
        },
        cursor: 'move',
        zIndex: 1000,
        helper: 'clone',
        appendTo: 'body',
        containment: 'document',
    });
    
    $('.crm-cards-container').droppable({
        accept: '.crm-card',
        tolerance: 'pointer',
        over: function(event, ui) {
            const card = ui.draggable;
            const tabulacaoAtualId = card.closest('.crm-cards-container').data('tabulacao-id');
            const novaTabulacaoId = $(this).data('tabulacao-id');
            
            if (novaTabulacaoId === tabulacaoAtualId) {
                $(this).addClass('droppable-invalid');
            } else {
                $(this).addClass('droppable-valid');
            }
        },
        out: function(event, ui) {
            $(this).removeClass('droppable-valid droppable-invalid');
        },
        drop: function(event, ui) {
            $(this).removeClass('droppable-valid droppable-invalid');
            
            const card = ui.draggable;
            const controleId = card.data('controle-id');
            const novaTabulacaoId = $(this).data('tabulacao-id');
            const novaTabulacaoNome = $(this).data('tabulacao-nome');
            const tabulacaoAtualId = card.closest('.crm-cards-container').data('tabulacao-id');
            
            if (novaTabulacaoId === tabulacaoAtualId) {
                return false;
            }
            
            if (novaTabulacaoNome === 'REVERSÃO' || novaTabulacaoNome === 'REVERSAO' || novaTabulacaoNome === 'CHECAGEM') {
                if (novaTabulacaoNome === 'REVERSÃO' || novaTabulacaoNome === 'REVERSAO') {
                    abrirModalReversao(controleId, novaTabulacaoId);
                } else if (novaTabulacaoNome === 'CHECAGEM') {
                    abrirModalChecagem(controleId, novaTabulacaoId);
                }
                return false;
            }
            
            moverCard(controleId, novaTabulacaoId, card, $(this));
        }
    });
}

function moverCard(controleId, novaTabulacaoId, cardElement, novoContainer) {
    const novaTabulacaoNome = novoContainer.data('tabulacao-nome');
    
    if (novaTabulacaoNome === 'REVERSÃO' || novaTabulacaoNome === 'REVERSAO') {
        abrirModalReversao(controleId, novaTabulacaoId);
        return false;
    } else if (novaTabulacaoNome === 'CHECAGEM') {
        abrirModalChecagem(controleId, novaTabulacaoId);
        return false;
    }
    
    moverCardNormal(controleId, novaTabulacaoId, cardElement, novoContainer);
}

function moverCardNormal(controleId, novaTabulacaoId, cardElement, novoContainer) {
    novoContainer.find('.text-center.text-muted').remove();
    
    const containerAtual = cardElement.closest('.crm-cards-container');
    
    cardElement.detach();
    
    if (containerAtual.find('.crm-card').length === 0) {
        containerAtual.html('<div class="text-center text-muted p-3">Nenhum card</div>');
    }
    
    cardElement.appendTo(novoContainer);
    
    cardElement.draggable({
        revert: function(dropTarget) {
            if (!dropTarget) {
                return true;
            }
            const card = $(this);
            const tabulacaoAtualId = card.closest('.crm-cards-container').data('tabulacao-id');
            const novaTabulacaoId = dropTarget.data('tabulacao-id');
            return novaTabulacaoId === tabulacaoAtualId;
        },
        cursor: 'move',
        zIndex: 1000,
        helper: 'clone',
        appendTo: 'body',
        containment: 'document',
    });
    
    atualizarContadores();
    
    $.ajax({
        url: '/api/crm/mover-card/',
        method: 'POST',
        data: {
            controle_id: controleId,
            nova_tabulacao_id: novaTabulacaoId,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (!response.success) {
                alert('Erro: ' + response.message);
                carregarKanban();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao mover card: ' + (response.message || 'Erro desconhecido'));
            carregarKanban();
        }
    });
}

function atualizarContadores() {
    $('.crm-column').each(function() {
        const count = $(this).find('.crm-card').length;
        const small = $(this).find('.card-header small');
        if (small.length) {
            small.text(count + ' card(s)');
        }
    });
}

function abrirFichaCliente(cpf) {
    $.ajax({
        url: `/api/crm/ficha-cliente/${cpf}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                exibirFichaCliente(response.data);
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao buscar cliente: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

let clienteSelecionadoCRM = null;
let matriculaSelecionadaCRM = null;
let clienteCPFAtualCRM = null;

function exibirFichaCliente(dados) {
    clienteSelecionadoCRM = dados;
    const dp = dados.dados_pessoais;
    
    clienteCPFAtualCRM = dp.cpf;
    $('#dp-nome').text(dp.nome);
    $('#dp-cpf').text(formatarCPF(dp.cpf));
    $('#dp-uf').text(dp.uf || '-');
    $('#dp-situacao').text(dp.situacao_funcional || '-');
    
    console.log('[CRM] Dados recebidos:', {
        dados_reversao: dados.dados_reversao,
        dados_checagem: dados.dados_checagem
    });
    
    if (dados.dados_reversao) {
        console.log('[CRM] Exibindo dados de reversão:', dados.dados_reversao);
        const rev = dados.dados_reversao;
        $('#rev-data').text(rev.data_para_reversao || '-');
        $('#rev-horario').text(rev.horario_disponivel || '-');
        $('#rev-responsavel').text(rev.responsavel_nome || '-');
        $('#rev-data-criacao').text(rev.data_criacao || '-');
        
        if (rev.observacao && rev.observacao.trim()) {
            $('#rev-observacao').text(rev.observacao);
            $('#rev-observacao-row').show();
        } else {
            $('#rev-observacao-row').hide();
        }
        
        if (rev.arquivos && rev.arquivos.length > 0) {
            const arquivosList = $('#rev-arquivos-list');
            arquivosList.empty();
            rev.arquivos.forEach(function(arquivo) {
                arquivosList.append(`
                    <li>
                        <a href="${arquivo.url}" target="_blank" class="text-decoration-none">
                            <i class='bx bx-file'></i> ${escapeHtml(arquivo.titulo)}
                        </a>
                    </li>
                `);
            });
            $('#rev-arquivos-row').show();
        } else {
            $('#rev-arquivos-row').hide();
        }
        
        $('#dados-reversao-card').show();
        console.log('[CRM] Card de reversão exibido');
    } else {
        $('#dados-reversao-card').hide();
        console.log('[CRM] Nenhum dado de reversão encontrado');
    }
    
    if (dados.dados_checagem) {
        console.log('[CRM] Exibindo dados de checagem:', dados.dados_checagem);
        const chec = dados.dados_checagem;
        $('#chec-data').text(chec.data_para_checagem || '-');
        $('#chec-horario').text(chec.horario_disponivel || '-');
        $('#chec-responsavel').text(chec.responsavel_nome || '-');
        $('#chec-data-criacao').text(chec.data_criacao || '-');
        
        $('#chec-banco').text(limparNomeBanco(chec.nome_banco) || '-');
        $('#chec-valor-af').text(chec.valor_af ? 'R$ ' + formatarMoeda(chec.valor_af) : '-');
        $('#chec-valor-repasse').text(chec.valor_repasse ? 'R$ ' + formatarMoeda(chec.valor_repasse) : '-');
        $('#chec-saldo-devedor').text(chec.saldo_devedor ? 'R$ ' + formatarMoeda(chec.saldo_devedor) : '-');
        $('#chec-parcela-atual').text(chec.valor_parcela_atual ? 'R$ ' + formatarMoeda(chec.valor_parcela_atual) : '-');
        $('#chec-parcela-nova').text(chec.valor_parcela_nova_proposta ? 'R$ ' + formatarMoeda(chec.valor_parcela_nova_proposta) : '-');
        $('#chec-valor-troco').text(chec.valor_troco ? 'R$ ' + formatarMoeda(chec.valor_troco) : '-');
        $('#chec-prazo-atual').text(chec.prazo_atual ? chec.prazo_atual + ' meses' : '-');
        $('#chec-prazo-acordado').text(chec.prazo_acordado ? chec.prazo_acordado + ' meses' : '-');
        
        if (chec.observacao) {
            $('#chec-observacao').text(chec.observacao);
            $('#chec-observacao-row').show();
        } else {
            $('#chec-observacao-row').hide();
        }
        
        if (chec.arquivos && chec.arquivos.length > 0) {
            const arquivosList = $('#chec-arquivos-list');
            arquivosList.empty();
            chec.arquivos.forEach(function(arquivo) {
                arquivosList.append(`
                    <li>
                        <a href="${arquivo.url}" target="_blank" class="text-decoration-none">
                            <i class='bx bx-file'></i> ${escapeHtml(arquivo.titulo)}
                        </a>
                    </li>
                `);
            });
            $('#chec-arquivos-row').show();
        } else {
            $('#chec-arquivos-row').hide();
        }
        
        $('#dados-checagem-card').show();
    } else {
        $('#dados-checagem-card').hide();
    }
    
    const tbody = $('#matriculas-tbody-crm');
    tbody.empty();
    
    if (dados.matriculas.length === 0) {
        tbody.append('<tr><td colspan="8" class="text-center">Nenhuma matrícula encontrada</td></tr>');
    } else {
        dados.matriculas.forEach(function(mat) {
            const matriculaInstituidor = mat.matricula_instituidor || '-';
            const row = `
                <tr style="cursor: pointer;" onclick="selecionarMatriculaCRM(${mat.id})">
                    <td>${escapeHtml(mat.matricula)}</td>
                    <td>${escapeHtml(matriculaInstituidor)}</td>
                    <td>${escapeHtml(mat.orgao || '-')}</td>
                    <td>${escapeHtml(mat.upag || '-')}</td>
                    <td>${mat.qtd_contratos}</td>
                    <td>R$ ${formatarMoeda(mat.base_calculo)}</td>
                    <td>${escapeHtml(mat.rjur || '-')}</td>
                    <td>${escapeHtml(mat.campanha)}</td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    $('#matriculas-container').show();
    $('#detalhes-matricula-container-crm').hide();
    
    const modalElement = document.getElementById('modalFichaCliente');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function selecionarMatriculaCRM(matriculaId) {
    if (!clienteSelecionadoCRM) return;
    
    const matricula = clienteSelecionadoCRM.matriculas.find(m => m.id === matriculaId);
    if (!matricula) return;
    
    matriculaSelecionadaCRM = matricula;
    
    $('#matricula-numero-crm').text(matricula.matricula);
    $('#matricula-selecionada-titulo-crm').html(`Matrícula: <strong>${escapeHtml(matricula.matricula)}</strong>`);
    
    const margens = matricula.margens;
    $('#margem-5-bruta-crm').text(formatarMoeda(margens.bruta_5));
    $('#margem-5-util-crm').text(formatarMoeda(margens.util_5));
    $('#margem-5-saldo-crm').text(formatarMoeda(margens.saldo_5));
    
    $('#margem-5b-bruta-crm').text(formatarMoeda(margens.bruta_5b));
    $('#margem-5b-util-crm').text(formatarMoeda(margens.util_5b));
    $('#margem-5b-saldo-crm').text(formatarMoeda(margens.saldo_5b));
    
    $('#margem-35-bruta-crm').text(formatarMoeda(margens.bruta_35));
    $('#margem-35-util-crm').text(formatarMoeda(margens.util_35));
    $('#margem-35-saldo-crm').text(formatarMoeda(margens.saldo_35));
    
    const contratosTbody = $('#contratos-tbody-crm');
    contratosTbody.empty();
    
    if (matricula.contratos.length === 0) {
        contratosTbody.append('<tr><td colspan="6" class="text-center">Nenhum contrato encontrado</td></tr>');
    } else {
        matricula.contratos.forEach(function(contrato) {
            const row = `
                <tr>
                    <td>${escapeHtml(contrato.contrato)}</td>
                    <td>${escapeHtml(contrato.tipo_contrato || '-')}</td>
                    <td>${escapeHtml(limparNomeBanco(contrato.banco) || '-')}</td>
                    <td>R$ ${formatarMoeda(contrato.valor_parcela)}</td>
                    <td>${contrato.parcelas_restantes || 0}</td>
                    <td>${escapeHtml(contrato.campanha)}</td>
                </tr>
            `;
            contratosTbody.append(row);
        });
    }
    
    $('#matriculas-container').hide();
    $('#detalhes-matricula-container-crm').show();
}

function voltarParaMatriculasCRM() {
    $('#matriculas-container').show();
    $('#detalhes-matricula-container-crm').hide();
    matriculaSelecionadaCRM = null;
}

function abrirModalCalculadorasCRM() {
    const modalElement = document.getElementById('modalCalculadorasCRM');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function calcularSaldoDevedorCRM() {
    const parcela = parseFloat($('#calc-parcela-crm').val()) || 0;
    const prazo = parseInt($('#calc-prazo-crm').val()) || 0;
    
    if (parcela <= 0 || prazo <= 0) {
        alert('Preencha parcela e prazo corretamente');
        return;
    }
    
    if (prazo < 1 || prazo > 96) {
        alert('Prazo deve estar entre 1 e 96 meses');
        return;
    }
    
    const saldoTotal = parcela * prazo;
    
    let percentual = 0;
    if (prazo >= 84 && prazo <= 96) {
        percentual = 40;
    } else if (prazo >= 72 && prazo <= 83) {
        percentual = 35;
    } else if (prazo >= 60 && prazo <= 71) {
        percentual = 30;
    } else if (prazo >= 40 && prazo <= 59) {
        percentual = 25;
    } else if (prazo >= 1 && prazo <= 39) {
        percentual = 15;
    }
    
    const desconto = saldoTotal * (percentual / 100);
    const saldoFinal = saldoTotal - desconto;
    
    $('#calc-saldo-total-crm').text(formatarMoeda(saldoTotal));
    $('#calc-percentual-crm').text(percentual);
    $('#calc-desconto-valor-crm').text(formatarMoeda(desconto));
    $('#calc-saldo-final-crm').text(formatarMoeda(saldoFinal));
}

function limparCalculadoraSaldoCRM() {
    $('#calc-parcela-crm').val('');
    $('#calc-prazo-crm').val('');
    $('#calc-percentual-crm').text('0');
    $('#calc-saldo-total-crm').text('0.00');
    $('#calc-desconto-valor-crm').text('0.00');
    $('#calc-saldo-final-crm').text('0.00');
}

function calcularCoeficienteCRM() {
    const parcela = parseFloat($('#coef-parcela-crm').val()) || 0;
    const coeficiente = parseFloat($('#coef-coeficiente-crm').val()) || 0;
    
    if (parcela <= 0 || coeficiente <= 0) {
        alert('Preencha parcela e coeficiente corretamente (valores devem ser maiores que zero)');
        return;
    }
    
    const saldoLiberado = parcela / coeficiente;
    $('#resultado-coeficiente-crm').text(formatarMoeda(saldoLiberado));
}

function limparCalculadoraCoefCRM() {
    $('#coef-parcela-crm').val('');
    $('#coef-coeficiente-crm').val('');
    $('#resultado-coeficiente-crm').text('0.00');
}

function calcularBeneficioCRM() {
    const margemLiq = parseFloat($('#beneficio-margem-crm').val()) || 0;
    
    if (margemLiq <= 0) {
        alert('Preencha a margem líquida corretamente (valor deve ser maior que zero)');
        return;
    }
    
    const parcela = margemLiq * 0.90;
    const limite = parcela * 23;
    const saque = limite * 0.70;
    
    $('#beneficio-parcela-crm').text(formatarMoeda(parcela));
    $('#beneficio-limite-crm').text(formatarMoeda(limite));
    $('#beneficio-saque-crm').text(formatarMoeda(saque));
}

function limparCalculadoraBeneficioCRM() {
    $('#beneficio-margem-crm').val('');
    $('#beneficio-parcela-crm').text('0.00');
    $('#beneficio-limite-crm').text('0.00');
    $('#beneficio-saque-crm').text('0.00');
}

function abrirModalSimuladorCRM() {
    const modalElement = document.getElementById('modalSimuladorCRM');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function calcularSimulacaoCRM() {
    const coef = parseFloat($('#sim-coef-crm').val()) || 0;
    const parcela = parseFloat($('#sim-parcela-crm').val()) || 0;
    const saldoDevedor = parseFloat($('#sim-saldo-devedor-crm').val()) || 0;
    const incluir35 = $('#sim-incluir-35-crm').is(':checked');
    
    if (coef <= 0 || parcela <= 0) {
        alert('Preencha COEF e Parcela corretamente');
        return;
    }
    
    const af = parcela * (coef / 100);
    $('#sim-af-crm').val(af.toFixed(2));
    
    let saldoTotal = saldoDevedor;
    if (incluir35 && clienteSelecionadoCRM && clienteSelecionadoCRM.matriculas && clienteSelecionadoCRM.matriculas.length > 0) {
        const margens = clienteSelecionadoCRM.matriculas[0].margens;
        if (margens && margens.saldo_35) {
            saldoTotal += parseFloat(margens.saldo_35);
        }
    }
    
    const troco = af - saldoTotal;
    $('#sim-troco-crm').val(troco.toFixed(2));
    
    const resultadoDiv = $('#simulacao-resultado-crm');
    const mensagemDiv = $('#simulacao-mensagem-crm');
    
    if (troco >= 0) {
        mensagemDiv.removeClass('alert-danger').addClass('alert-success');
        mensagemDiv.html('<i class="bx bx-check-circle"></i> Simulação aprovada! Troco disponível: R$ ' + formatarMoeda(troco));
    } else {
        mensagemDiv.removeClass('alert-success').addClass('alert-danger');
        mensagemDiv.html('<i class="bx bx-x-circle"></i> Simulação reprovada! Faltam R$ ' + formatarMoeda(Math.abs(troco)));
    }
    
    resultadoDiv.show();
}

function limparSimuladorCRM() {
    $('#sim-coef-crm').val('');
    $('#sim-parcela-crm').val('');
    $('#sim-af-crm').val('');
    $('#sim-saldo-devedor-crm').val('');
    $('#sim-troco-crm').val('');
    $('#sim-incluir-35-crm').prop('checked', false);
    $('#simulacao-resultado-crm').hide();
}

function formatarMoeda(valor) {
    if (!valor || valor === 0) return '0,00';
    return parseFloat(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function abrirModalNovaTabulacao() {
    new bootstrap.Modal(document.getElementById('modalNovaTabulacao')).show();
}

function salvarNovaTabulacao() {
    const nome = $('#tabulacao-nome').val().trim();
    const ordem = $('#tabulacao-ordem').val();
    const cor = $('#tabulacao-cor').val();
    
    if (!nome || !ordem) {
        alert('Preencha todos os campos');
        return;
    }
    
    $.ajax({
        url: '/api/crm/criar-tabulacao/',
        method: 'POST',
        data: {
            nome: nome,
            ordem: ordem,
            cor: cor,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                bootstrap.Modal.getInstance(document.getElementById('modalNovaTabulacao')).hide();
                carregarKanban();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao criar tabulação: ' + (response.message || 'Erro desconhecido'));
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

function limparNomeBanco(nomeBanco) {
    if (!nomeBanco) return '';
    // Remove "SERV d8" ou "PENS d8" do final do nome (case insensitive)
    return String(nomeBanco).replace(/\s+(SERV|PENS)\s+d8$/i, '').trim();
}

function abrirModalReversao(controleId, novaTabulacaoId) {
    $('#reversao-controle-id').val(controleId);
    $('#reversao-nova-tabulacao-id').val(novaTabulacaoId);
    
    $('#formDadosReversao')[0].reset();
    $('#reversao-controle-id').val(controleId);
    $('#reversao-nova-tabulacao-id').val(novaTabulacaoId);
    $('#reversao-horario').empty();
    $('#reversao-data').empty().append('<option value="">Selecione o responsável primeiro</option>');
    $('#reversao-data-msg').text('').removeClass('text-danger text-success');
    
    carregarRepresentantes('REVERSAO', '#reversao-responsavel', function() {
        $('#reversao-responsavel').off('change').on('change', function() {
            const responsavelId = $(this).val();
            if (responsavelId) {
                carregarDiasDisponiveis('reversao', responsavelId);
            } else {
                $('#reversao-data').empty().append('<option value="">Selecione o responsável primeiro</option>');
                $('#reversao-horario').empty().append('<option value="">Selecione o responsável e a data primeiro</option>');
            }
        });
        
        $('#reversao-data').off('change').on('change', function() {
            const responsavelId = $('#reversao-responsavel').val();
            const data = $(this).val();
            
            if (responsavelId && data) {
                carregarHorariosDisponiveis('reversao', responsavelId, data, novaTabulacaoId);
            } else {
                $('#reversao-horario').empty().append('<option value="">Selecione o responsável e a data primeiro</option>');
            }
        });
    });
    
    const modalElement = document.getElementById('modalDadosReversao');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function abrirModalChecagem(controleId, novaTabulacaoId) {
    $('#checagem-controle-id').val(controleId);
    $('#checagem-nova-tabulacao-id').val(novaTabulacaoId);
    
    $('#formDadosChecagem')[0].reset();
    $('#checagem-controle-id').val(controleId);
    $('#checagem-nova-tabulacao-id').val(novaTabulacaoId);
    $('#checagem-horario').empty();
    $('#checagem-data').empty().append('<option value="">Selecione o responsável primeiro</option>');
    $('#checagem-data-msg').text('').removeClass('text-danger text-success');
    
    carregarRepresentantes('CHECAGEM', '#checagem-responsavel', function() {
        $('#checagem-responsavel').off('change').on('change', function() {
            const responsavelId = $(this).val();
            if (responsavelId) {
                carregarDiasDisponiveis('checagem', responsavelId);
            } else {
                $('#checagem-data').empty().append('<option value="">Selecione o responsável primeiro</option>');
                $('#checagem-horario').empty().append('<option value="">Selecione o responsável e a data primeiro</option>');
            }
        });
        
        $('#checagem-data').off('change').on('change', function() {
            const responsavelId = $('#checagem-responsavel').val();
            const data = $(this).val();
            
            if (responsavelId && data) {
                carregarHorariosDisponiveis('checagem', responsavelId, data, novaTabulacaoId);
            } else {
                $('#checagem-horario').empty().append('<option value="">Selecione o responsável e a data primeiro</option>');
            }
        });
    });
    
    const modalElement = document.getElementById('modalDadosChecagem');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function carregarRepresentantes(tipo, selectId, callback) {
    $.ajax({
        url: `/api/crm/listar-representantes/${tipo}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const select = $(selectId);
                select.empty();
                select.append('<option value="">Selecione...</option>');
                
                if (response.data && response.data.length > 0) {
                    response.data.forEach(function(user) {
                        const option = $(`<option value="${user.id}" 
                            data-horario-inicio="${user.horario_inicio || ''}" 
                            data-horario-final="${user.horario_final || ''}" 
                            data-tempo-call="${user.tempo_call || 30}">${user.nome}</option>`);
                        select.append(option);
                    });
                    
                    if (callback && typeof callback === 'function') {
                        callback();
                    }
                } else {
                    console.warn(`[CRM] Nenhum representante encontrado para o tipo: ${tipo}`);
                }
            } else {
                console.error(`[CRM] Erro ao carregar representantes: ${response.message || 'Erro desconhecido'}`);
                alert('Erro ao carregar representantes: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            const errorMsg = response.message || 'Erro ao carregar representantes.';
            console.error(`[CRM] Erro na requisição de representantes (tipo: ${tipo}):`, {
                status: xhr.status,
                statusText: xhr.statusText,
                message: errorMsg,
                response: response
            });
            alert('Erro ao carregar representantes: ' + errorMsg);
        }
    });
}

function carregarDiasDisponiveis(tipo, responsavelId) {
    const prefixo = tipo === 'reversao' ? 'reversao' : 'checagem';
    const selectResponsavel = $(`#${prefixo}-responsavel`);
    const selectData = $(`#${prefixo}-data`);
    
    const horarioInicio = selectResponsavel.find('option:selected').data('horario-inicio');
    const horarioFinal = selectResponsavel.find('option:selected').data('horario-final');
    const tempoCall = parseInt(selectResponsavel.find('option:selected').data('tempo-call')) || 30;
    
    if (!horarioInicio || !horarioFinal) {
        console.warn(`[CRM] Horários não definidos para o responsável ${responsavelId}`);
        selectData.empty();
        selectData.append('<option value="">Horários não configurados</option>');
        return;
    }
    
    $.ajax({
        url: '/api/crm/listar-dias-disponiveis/',
        method: 'GET',
        data: {
            responsavel_id: responsavelId,
            horario_inicio: horarioInicio,
            horario_final: horarioFinal,
            tempo_call: tempoCall
        },
        success: function(response) {
            if (response.success) {
                selectData.empty();
                selectData.append('<option value="">Selecione...</option>');
                
                if (response.data && response.data.length > 0) {
                    response.data.forEach(function(dia) {
                        selectData.append(`<option value="${dia.data}">${dia.display}</option>`);
                    });
                    $(`#${prefixo}-data-msg`).text(`${response.data.length} dia(s) disponível(is)`).addClass('text-success').removeClass('text-danger');
                } else {
                    selectData.append('<option value="">Nenhum dia disponível</option>');
                    $(`#${prefixo}-data-msg`).text('Nenhum dia disponível para este responsável.').addClass('text-danger').removeClass('text-success');
                }
            } else {
                console.error('[CRM] Erro ao carregar dias:', response.message);
                selectData.empty();
                selectData.append('<option value="">Erro ao carregar dias</option>');
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('[CRM] Erro na requisição de dias:', {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            selectData.empty();
            selectData.append('<option value="">Erro ao carregar dias</option>');
        }
    });
}

function carregarHorariosDisponiveis(tipo, responsavelId, data, tabulacaoId) {
    const prefixo = tipo === 'reversao' ? 'reversao' : 'checagem';
    const selectResponsavel = $(`#${prefixo}-responsavel`);
    const selectHorario = $(`#${prefixo}-horario`);
    const controleId = $(`#${prefixo}-controle-id`).val();
    
    const horarioInicio = selectResponsavel.find('option:selected').data('horario-inicio');
    const horarioFinal = selectResponsavel.find('option:selected').data('horario-final');
    const tempoCall = parseInt(selectResponsavel.find('option:selected').data('tempo-call')) || 30;
    
    if (!horarioInicio || !horarioFinal) {
        console.warn(`[CRM] Horários não definidos para o responsável ${responsavelId}`);
        selectHorario.empty();
        selectHorario.append('<option value="">Horários não configurados</option>');
        return;
    }
    
    $.ajax({
        url: '/api/crm/listar-horarios-disponiveis/',
        method: 'GET',
        data: {
            responsavel_id: responsavelId,
            data: data,
            tabulacao_id: tabulacaoId,
            horario_inicio: horarioInicio,
            horario_final: horarioFinal,
            tempo_call: tempoCall,
            controle_id: controleId || ''
        },
        success: function(response) {
            const dataMsg = $(`#${prefixo}-data-msg`);
            
            if (response.success) {
                selectHorario.empty();
                selectHorario.append('<option value="">Selecione...</option>');
                
                if (response.data && response.data.length > 0) {
                    response.data.forEach(function(horario) {
                        selectHorario.append(`<option value="${horario.hora}">${horario.display}</option>`);
                    });
                    dataMsg.text(`${response.data.length} horário(s) disponível(is)`).addClass('text-success').removeClass('text-danger');
                } else {
                    selectHorario.append('<option value="">Nenhum horário disponível</option>');
                    dataMsg.text('Nenhum horário disponível para esta data. Selecione outra data.').addClass('text-danger').removeClass('text-success');
                }
            } else {
                console.error(`[CRM] Erro ao carregar horários: ${response.message || 'Erro desconhecido'}`);
                selectHorario.empty();
                selectHorario.append('<option value="">Erro ao carregar horários</option>');
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error(`[CRM] Erro na requisição de horários:`, {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            selectHorario.empty();
            selectHorario.append('<option value="">Erro ao carregar horários</option>');
        }
    });
}

function salvarDadosReversao() {
    const controleId = $('#reversao-controle-id').val();
    const novaTabulacaoId = $('#reversao-nova-tabulacao-id').val();
    const data = $('#reversao-data').val();
    const horario = $('#reversao-horario').val();
    const responsavel = $('#reversao-responsavel').val();
    const observacao = $('#reversao-observacao').val();
    const arquivos = $('#reversao-arquivos')[0].files;
    
    if (!data || !horario || !responsavel) {
        alert('Preencha data, horário e responsável.');
        return;
    }
    
    const formData = new FormData();
    formData.append('controle_id', controleId);
    formData.append('nova_tabulacao_id', novaTabulacaoId);
    formData.append('data_para_reversao', data);
    formData.append('horario_disponivel', horario);
    formData.append('responsavel_por_reversao', responsavel);
    formData.append('observacao', observacao);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    for (let i = 0; i < arquivos.length; i++) {
        formData.append('arquivos_reversao', arquivos[i]);
    }
    
    $.ajax({
        url: '/api/crm/mover-card/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                const modalElement = document.getElementById('modalDadosReversao');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
                carregarKanban();
                alert(response.message);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function() {
            alert('Erro ao salvar dados de reversão.');
        }
    });
}

function salvarDadosChecagem() {
    const controleId = $('#checagem-controle-id').val();
    const novaTabulacaoId = $('#checagem-nova-tabulacao-id').val();
    const data = $('#checagem-data').val();
    const horario = $('#checagem-horario').val();
    const responsavel = $('#checagem-responsavel').val();
    const observacao = $('#checagem-observacao').val();
    const nomeBanco = $('#checagem-banco').val();
    const valorAf = $('#checagem-valor-af').val();
    const valorRepasse = $('#checagem-valor-repasse').val();
    const saldoDevedor = $('#checagem-saldo-devedor').val();
    const parcelaAtual = $('#checagem-parcela-atual').val();
    const parcelaNova = $('#checagem-parcela-nova').val();
    const troco = $('#checagem-troco').val();
    const prazoAtual = $('#checagem-prazo-atual').val();
    const prazoAcordado = $('#checagem-prazo-acordado').val();
    const arquivos = $('#checagem-arquivos')[0].files;
    
    if (!data || !horario || !responsavel) {
        alert('Preencha data, horário e responsável.');
        return;
    }
    
    const formData = new FormData();
    formData.append('controle_id', controleId);
    formData.append('nova_tabulacao_id', novaTabulacaoId);
    formData.append('data_para_checagem', data);
    formData.append('horario_disponivel', horario);
    formData.append('responsavel_por_checagem', responsavel);
    formData.append('observacao', observacao);
    formData.append('nome_banco', nomeBanco);
    formData.append('valor_af', valorAf);
    formData.append('valor_repasse', valorRepasse);
    formData.append('saldo_devedor', saldoDevedor);
    formData.append('valor_parcela_atual', parcelaAtual);
    formData.append('valor_parcela_nova_proposta', parcelaNova);
    formData.append('valor_troco', troco);
    formData.append('prazo_atual', prazoAtual);
    formData.append('prazo_acordado', prazoAcordado);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    for (let i = 0; i < arquivos.length; i++) {
        formData.append('arquivos_checagem', arquivos[i]);
    }
    
    $.ajax({
        url: '/api/crm/mover-card/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                const modalElement = document.getElementById('modalDadosChecagem');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
                carregarKanban();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar dados de checagem: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

