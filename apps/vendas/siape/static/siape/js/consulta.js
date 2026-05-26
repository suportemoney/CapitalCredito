// SIAPE URLs atualizadas para rota raiz - v2
let clienteSelecionado = null;
let matriculaSelecionada = null;
let clienteCPFAtual = null;

$(document).ready(function() {
    if (typeof window.isSuperUser !== 'undefined' && window.isSuperUser) {
        carregarCampanhas();
    } else {
        $('#filtroCampanha').val('').prop('disabled', true);
    }

    $('#select-matricula').on('change', function() {
        const id = parseInt($(this).val(), 10);
        if (id) {
            selecionarMatricula(id);
        }
    });
    
    $('#formBuscarCliente').on('submit', function(e) {
        e.preventDefault();
        buscarClientePorCPF();
    });
    
    $('#buscaCliente').on('input', function() {
        let valor = $(this).val().replace(/\D/g, '');
        $(this).val(valor);
    });
    
    $('#buscaCliente').on('keypress', function(e) {
        if (e.which === 13) {
            e.preventDefault();
            buscarClientePorCPF();
        }
    });
});

function carregarCampanhas() {
    $.ajax({
        url: '/api/consulta/campanhas-ativas/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const select = $('#filtroCampanha');
                select.empty();
                select.append('<option value="">Todas as campanhas ativas</option>');
                
                response.data.forEach(function(camp) {
                    select.append(`<option value="${camp.id}">${escapeHtml(camp.titulo)}</option>`);
                });
            }
        },
        error: function(xhr) {
            console.error('Erro ao carregar campanhas:', xhr);
        }
    });
}

function buscarClientePorCPF() {
    const busca = $('#buscaCliente').val().trim();
    const campanhaId = $('#filtroCampanha').val();
    
    if (!busca) {
        alert('Digite um CPF para buscar');
        return;
    }
    
    const cpf_limpo = busca.replace(/\D/g, '');
    if (cpf_limpo.length !== 11) {
        alert('CPF deve conter 11 dígitos');
        return;
    }
    
    $.ajax({
        url: '/api/consulta/buscar/',
        method: 'GET',
        data: {
            busca: cpf_limpo,
            campanha_id: campanhaId
        },
        success: function(response) {
            if (response.success) {
                clienteSelecionado = response.data;
                exibirDetalhesCliente(response.data);
                
                if (response.data.matriculas && response.data.matriculas.length > 0) {
                    const primeiraMatricula = response.data.matriculas[0];
                    selecionarMatricula(primeiraMatricula.id);
                }
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            if (xhr.status === 404) {
                alert('Cliente não encontrado');
            } else {
                alert('Erro ao buscar cliente: ' + (response.message || 'Erro desconhecido'));
            }
        }
    });
}

function selecionarCliente(clienteId) {
    $.ajax({
        url: `/api/consulta/detalhes/${clienteId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                clienteSelecionado = response.data;
                exibirDetalhesCliente(response.data);
                if (response.data.matriculas && response.data.matriculas.length > 0) {
                    selecionarMatricula(response.data.matriculas[0].id);
                }
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao buscar detalhes: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function exibirDetalhesCliente(dados) {
    const dp = dados.dados_pessoais;
    
    clienteCPFAtual = dp.cpf;
    matriculaSelecionada = null;
    $('#dp-nome').text(dp.nome || '—');
    $('#dp-cpf').text(formatarCPF(dp.cpf));
    $('#dp-uf').text(dp.uf || '—');
    renderSituacaoFuncional(dp.situacao_funcional);
    $('#dp-celular').text(dp.celular ? formatarTelefone(dp.celular) : '-');
    $('#dp-tipo-base').text(formatarTipoBase(dp.tipo_base));
    $('#esteira-cpf').val(dp.cpf);
    $('#contato-cliente-id').val(dp.id || '');

    const agora = new Date();
    $('#sidebar-data-consulta').text(
        agora.toLocaleDateString('pt-BR') + ' ' + agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    );

    const selectMat = $('#select-matricula');
    selectMat.empty();
    if (!dados.matriculas || dados.matriculas.length === 0) {
        selectMat.append('<option value="">Nenhuma matrícula</option>');
        limparDetalhesMatricula();
    } else {
        dados.matriculas.forEach(function(mat) {
            selectMat.append(
                `<option value="${mat.id}">${escapeHtml(mat.matricula)} — ${escapeHtml(mat.campanha)}</option>`
            );
        });
    }

    $('#area-resultados').show();
    $('#detalhes-cliente-container').show();
    $('#detalhes-matricula-inline').show();

    if (typeof window.initConsultaOperacional === 'function') {
        window.initConsultaOperacional(
            dados.carteira_id,
            dados.status_comercial,
            dp.cpf,
            dp.nome
        );
    }
}

function renderSituacaoFuncional(situacao) {
    const texto = situacao || '—';
    const $el = $('#dp-situacao');
    $el.empty().text(texto);
    if (texto && String(texto).toUpperCase().indexOf('ATIVO') !== -1) {
        $el.append('<span class="siape-badge-ativo">ATIVO</span>');
    }
}

function formatarTipoBase(tipo) {
    if (!tipo) return '—';
    const map = {
        'PENSIONISTA': 'Pensionista',
        'SERVIDOR': 'Servidor'
    };
    return map[String(tipo).toUpperCase()] || tipo;
}

function limparDetalhesMatricula() {
    $('#status-campanha').text('—');
    $('#sidebar-matricula').text('—');
    $('#sidebar-base-calculo').text('—');
    $('#sidebar-margem-5').text('—');
    $('#sidebar-margem-35').text('—');
    $('#sidebar-origem').text('—');
    $('#grid-orgao, #grid-upag, #grid-rubrica, #grid-rjur, #grid-base-calculo, #grid-matricula-instituidor').text('—');
    $('#detalhe-matricula-instituidor, #detalhe-qtd-contratos, #detalhe-rjur').text('—');
    $('#margem-5-bruta, #margem-5-util, #margem-5-saldo, #margem-5b-bruta, #margem-5b-util, #margem-5b-saldo, #margem-35-bruta, #margem-35-util, #margem-35-saldo').text('0,00');
    $('#contratos-tbody').html('<tr><td colspan="7" class="text-center">Nenhuma matrícula selecionada</td></tr>');
}

function selecionarMatricula(matriculaId) {
    if (!clienteSelecionado) return;
    
    const matricula = clienteSelecionado.matriculas.find(m => m.id === matriculaId);
    if (!matricula) return;
    
    matriculaSelecionada = matricula;

    $('#select-matricula').val(String(matriculaId));
    $('#status-campanha').text(matricula.campanha || '—');
    $('#sidebar-matricula').text(matricula.matricula || '—');
    $('#sidebar-base-calculo').text('R$ ' + formatarMoeda(matricula.base_calculo));
    $('#sidebar-origem').text(matricula.campanha || '—');

    $('#grid-orgao').text(matricula.orgao || '—');
    $('#grid-upag').text(matricula.upag || '—');
    $('#grid-rubrica').text(matricula.rubrica || '—');
    $('#grid-rjur').text(matricula.rjur || '—');
    $('#grid-base-calculo').text('R$ ' + formatarMoeda(matricula.base_calculo));
    $('#grid-matricula-instituidor').text(matricula.matricula_instituidor || '—');

    $('#detalhe-matricula-instituidor').text(matricula.matricula_instituidor || '—');
    $('#detalhe-qtd-contratos').text(matricula.qtd_contratos != null ? matricula.qtd_contratos : '—');
    $('#detalhe-rjur').text(matricula.rjur || '—');
    
    const margens = matricula.margens || {};
    $('#margem-5-bruta').text(formatarMoeda(margens.bruta_5));
    $('#margem-5-util').text(formatarMoeda(margens.util_5));
    $('#margem-5-saldo').text(formatarMoeda(margens.saldo_5));
    $('#sidebar-margem-5').text('R$ ' + formatarMoeda(margens.saldo_5));
    
    $('#margem-5b-bruta').text(formatarMoeda(margens.bruta_5b));
    $('#margem-5b-util').text(formatarMoeda(margens.util_5b));
    $('#margem-5b-saldo').text(formatarMoeda(margens.saldo_5b));
    
    $('#margem-35-bruta').text(formatarMoeda(margens.bruta_35));
    $('#margem-35-util').text(formatarMoeda(margens.util_35));
    $('#margem-35-saldo').text(formatarMoeda(margens.saldo_35));
    $('#sidebar-margem-35').text('R$ ' + formatarMoeda(margens.saldo_35));
    
    const contratosTbody = $('#contratos-tbody');
    contratosTbody.empty();
    
    if (!matricula.contratos || matricula.contratos.length === 0) {
        contratosTbody.append('<tr><td colspan="7" class="text-center">Nenhum contrato encontrado</td></tr>');
    } else {
        matricula.contratos.forEach(function(contrato) {
            const row = `
                <tr>
                    <td>${escapeHtml(contrato.contrato)}</td>
                    <td>${escapeHtml(contrato.tipo_contrato)}</td>
                    <td>${escapeHtml(limparNomeBanco(contrato.banco))}</td>
                    <td>R$ ${formatarMoeda(contrato.valor_parcela)}</td>
                    <td>${contrato.parcelas_restantes}</td>
                    <td>${contrato.numero_parcela != null ? contrato.numero_parcela : '—'}</td>
                    <td>${escapeHtml(contrato.campanha)}</td>
                </tr>
            `;
            contratosTbody.append(row);
        });
    }
}

function formatarCPF(cpf) {
    if (!cpf) return '-';
    cpf = cpf.replace(/\D/g, '');
    if (cpf.length === 11) {
        return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }
    return cpf;
}

function formatarMoeda(valor) {
    if (!valor || valor === 0) return '0,00';
    return parseFloat(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
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

function abrirModalEsteira() {
    if (!clienteCPFAtual) {
        alert('Selecione um cliente primeiro');
        return;
    }
    const hoje = new Date().toISOString().split('T')[0];
    const agora = new Date().toTimeString().slice(0, 5);
    $('#esteira-data').val(hoje);
    $('#esteira-hora').val(agora);
    const modalElement = document.getElementById('modalEsteira');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    } else {
        console.error('Modal modalEsteira não encontrado');
        alert('Erro ao abrir modal. Recarregue a página.');
    }
}

function salvarEsteira() {
    const cpf = $('#esteira-cpf').val();
    const data = $('#esteira-data').val();
    const hora = $('#esteira-hora').val();
    
    if (!cpf || !data || !hora) {
        alert('Preencha todos os campos');
        return;
    }
    
    $.ajax({
        url: '/api/crm/adicionar-esteira/',
        method: 'POST',
        data: {
            cpf: cpf,
            data_contato: data,
            hora_contato: hora,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                const modalElement = document.getElementById('modalEsteira');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao adicionar à esteira: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function abrirModalCalculadoras() {
    const modalElement = document.getElementById('modalCalculadoras');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    } else {
        console.error('Modal modalCalculadoras não encontrado');
        alert('Erro ao abrir modal. Recarregue a página.');
    }
}

function calcularSaldoDevedor() {
    const parcela = parseFloat($('#calc-parcela').val()) || 0;
    const prazo = parseInt($('#calc-prazo').val()) || 0;
    
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
    
    $('#calc-saldo-total').text(formatarMoeda(saldoTotal));
    $('#calc-percentual').text(percentual);
    $('#calc-desconto-valor').text(formatarMoeda(desconto));
    $('#calc-saldo-final').text(formatarMoeda(saldoFinal));
}

function limparCalculadoraSaldo() {
    $('#calc-parcela').val('');
    $('#calc-prazo').val('');
    $('#calc-percentual').text('0');
    $('#calc-saldo-total').text('0.00');
    $('#calc-desconto-valor').text('0.00');
    $('#calc-saldo-final').text('0.00');
}

function obterPercentualDesconto(prazo) {
    if (prazo >= 84 && prazo <= 96) return 40;
    if (prazo >= 72 && prazo <= 83) return 35;
    if (prazo >= 60 && prazo <= 71) return 30;
    if (prazo >= 40 && prazo <= 59) return 25;
    if (prazo >= 1 && prazo <= 39) return 15;
    return 0;
}

function calcularCoeficiente() {
    const parcela = parseFloat($('#coef-parcela').val()) || 0;
    const coeficiente = parseFloat($('#coef-coeficiente').val()) || 0;
    
    if (parcela <= 0 || coeficiente <= 0) {
        alert('Preencha parcela e coeficiente corretamente (valores devem ser maiores que zero)');
        return;
    }
    
    const saldoLiberado = parcela / coeficiente;
    $('#resultado-coeficiente').text(formatarMoeda(saldoLiberado));
}

function limparCalculadoraCoef() {
    $('#coef-parcela').val('');
    $('#coef-coeficiente').val('');
    $('#resultado-coeficiente').text('0.00');
}

function calcularBeneficio() {
    const margemLiq = parseFloat($('#beneficio-margem').val()) || 0;
    
    if (margemLiq <= 0) {
        alert('Preencha a margem líquida corretamente (valor deve ser maior que zero)');
        return;
    }
    
    const parcela = margemLiq * 0.90;
    const limite = parcela * 23;
    const saque = limite * 0.70;
    
    $('#beneficio-parcela').text(formatarMoeda(parcela));
    $('#beneficio-limite').text(formatarMoeda(limite));
    $('#beneficio-saque').text(formatarMoeda(saque));
}

function limparCalculadoraBeneficio() {
    $('#beneficio-margem').val('');
    $('#beneficio-parcela').text('0.00');
    $('#beneficio-limite').text('0.00');
    $('#beneficio-saque').text('0.00');
}

function abrirModalSimulador() {
    if (!matriculaSelecionada) {
        alert('Selecione uma matrícula primeiro para visualizar as margens e contratos disponíveis.');
        return;
    }
    
    const margens = matriculaSelecionada.margens;
    if (margens) {
        $('#simulacao-margem-5-saldo').text(formatarMoeda(margens.saldo_5));
        $('#simulacao-margem-5b-saldo').text(formatarMoeda(margens.saldo_5b));
        $('#simulacao-margem-35-saldo').text(formatarMoeda(margens.saldo_35));
        $('#simulacao-margens-container').show();
    } else {
        $('#simulacao-margens-container').hide();
    }
    
    const contratosTbody = $('#simulacao-contratos-tbody');
    contratosTbody.empty();
    
    if (matriculaSelecionada.contratos && matriculaSelecionada.contratos.length > 0) {
        matriculaSelecionada.contratos.forEach(function(contrato) {
            const valorParcela = parseFloat(contrato.valor_parcela) || 0;
            const parcelasRestantes = parseInt(contrato.parcelas_restantes) || 0;
            const saldoDevedor = valorParcela * parcelasRestantes;
            
            const row = `
                <tr>
                    <td style="text-align: center;">
                        <input type="checkbox" class="form-check-input simulacao-checkbox" 
                               name="simulacao_checkboxes" 
                               data-parcela="${valorParcela}" 
                               data-saldo-devedor="${saldoDevedor}"
                               style="cursor: pointer;">
                    </td>
                    <td>${escapeHtml(contrato.contrato)}</td>
                    <td>${escapeHtml(limparNomeBanco(contrato.banco) || '-')}</td>
                    <td>R$ ${formatarMoeda(contrato.valor_parcela)}</td>
                    <td>${contrato.parcelas_restantes || 0}</td>
                    <td>R$ ${formatarMoeda(saldoDevedor)}</td>
                </tr>
            `;
            contratosTbody.append(row);
        });
        $('#simulacao-contratos-container').show();
    } else {
        $('#simulacao-contratos-container').hide();
    }
    
    const modalElement = document.getElementById('modalSimulador');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    } else {
        console.error('Modal modalSimulador não encontrado');
        alert('Erro ao abrir modal. Recarregue a página.');
    }
}

function parseValor(valor) {
    if (!valor || valor === '') return 0;
    let valorStr = String(valor).trim();
    valorStr = valorStr.replace(/\./g, '');
    valorStr = valorStr.replace(',', '.');
    return parseFloat(valorStr) || 0;
}

function calcularSimulacao() {
    const coefInput = $('#simulacao_coef').val().trim();
    const parcelaInput = $('#simulacao_parcela').val().trim();
    const saldoDevedorInput = $('#simulacao_saldo_devedor').val().trim();
    
    const coef = parseValor(coefInput);
    const parcelaManual = parseValor(parcelaInput);
    const saldoDevedorManual = parseValor(saldoDevedorInput);
    
    let parcelaTotal = 0;
    let saldoDevedorTotal = 0;
    let checkboxesMarcados = 0;
    
    $('input[name="simulacao_checkboxes"]:checked').each(function() {
        const parcela = parseFloat($(this).data('parcela')) || 0;
        const saldoDevedor = parseFloat($(this).data('saldo-devedor')) || 0;
        parcelaTotal += parcela;
        saldoDevedorTotal += saldoDevedor;
        checkboxesMarcados++;
    });
    
    if (matriculaSelecionada && matriculaSelecionada.margens) {
        const margens = matriculaSelecionada.margens;
        
        const checkboxSaldo5 = $('#simulacao_checkbox_saldo_5').is(':checked');
        if (checkboxSaldo5 && margens.saldo_5) {
            const saldo5 = parseFloat(margens.saldo_5) || 0;
            parcelaTotal += saldo5;
        }
        
        const checkboxSaldo5b = $('#simulacao_checkbox_saldo_5b').is(':checked');
        if (checkboxSaldo5b && margens.saldo_5b) {
            const saldo5b = parseFloat(margens.saldo_5b) || 0;
            parcelaTotal += saldo5b;
        }
        
        const checkboxSaldo35 = $('#simulacao_checkbox_saldo_35').is(':checked');
        if (checkboxSaldo35 && margens.saldo_35) {
            const saldo35 = parseFloat(margens.saldo_35) || 0;
            parcelaTotal += saldo35;
        }
    }
    
    let parcelaFinal = parcelaTotal;
    if (checkboxesMarcados === 0 && parcelaManual > 0) {
        parcelaFinal = parcelaManual;
    }
    
    let saldoDevedorFinal = saldoDevedorTotal;
    if (saldoDevedorManual > 0) {
        saldoDevedorFinal = saldoDevedorManual;
    }
    
    if (checkboxesMarcados === 0 && coef > 0 && parcelaManual > 0 && saldoDevedorManual === 0) {
        alert('Selecione pelo menos um item para simulação ou informe o saldo devedor total.');
        return;
    }
    
    if (coef <= 0 || parcelaFinal <= 0) {
        $('#simulacao_af').val('');
        $('#simulacao_troco').val('');
        $('#simulacao-resultado').hide();
        return;
    }
    
    const af = parcelaFinal / coef;
    $('#simulacao_af').val(af.toFixed(2).replace('.', ','));
    
    const troco = af - saldoDevedorFinal;
    $('#simulacao_troco').val(troco.toFixed(2).replace('.', ','));
    
    if (checkboxesMarcados > 0) {
        const parcelaAtual = $('#simulacao_parcela').val().trim();
        if (parcelaAtual === '' || parcelaAtual === '0' || parcelaAtual === '0,00' || parcelaAtual === '0.00') {
            $('#simulacao_parcela').val(parcelaTotal.toFixed(2).replace('.', ','));
        }
        
        const saldoAtual = $('#simulacao_saldo_devedor').val().trim();
        if (saldoAtual === '' || saldoAtual === '0' || saldoAtual === '0,00' || saldoAtual === '0.00') {
            $('#simulacao_saldo_devedor').val(saldoDevedorTotal.toFixed(2).replace('.', ','));
        }
    }
    
    const resultadoDiv = $('#simulacao-resultado');
    const mensagemDiv = $('#simulacao-mensagem');
    
    if (troco > 0) {
        mensagemDiv.removeClass('alert-danger').addClass('alert-success');
        mensagemDiv.html('<i class="bx bx-check-circle"></i> AF cobre a operação com troco de R$ ' + formatarMoeda(troco));
    } else if (troco < 0) {
        mensagemDiv.removeClass('alert-success').addClass('alert-danger');
        mensagemDiv.html('<i class="bx bx-x-circle"></i> AF não cobre a operação. Faltam R$ ' + formatarMoeda(Math.abs(troco)));
    } else {
        mensagemDiv.removeClass('alert-danger').addClass('alert-success');
        mensagemDiv.html('<i class="bx bx-check-circle"></i> AF cobre exatamente a operação (sem troco)');
    }
    
    resultadoDiv.show();
}

function limparSimulador() {
    $('#simulacao_coef').val('');
    $('#simulacao_parcela').val('');
    $('#simulacao_af').val('');
    $('#simulacao_saldo_devedor').val('');
    $('#simulacao_troco').val('');
    $('#simulacao_checkbox_saldo_5').prop('checked', false);
    $('#simulacao_checkbox_saldo_5b').prop('checked', false);
    $('#simulacao_checkbox_saldo_35').prop('checked', false);
    $('input[name="simulacao_checkboxes"]').prop('checked', false);
    $('#simulacao-selecionar-todos').prop('checked', false);
    $('#simulacao-resultado').hide();
}

function formatarTelefone(telefone) {
    if (!telefone) return '-';
    const tel = telefone.replace(/\D/g, '');
    if (tel.length === 10) {
        return tel.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    } else if (tel.length === 11) {
        return tel.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    }
    return telefone;
}

function abrirModalContato() {
    const clienteId = $('#contato-cliente-id').val();
    if (!clienteId) {
        alert('Cliente não selecionado');
        return;
    }
    
    // Preencher o campo com o celular atual se existir
    const celularAtual = $('#dp-celular').text();
    if (celularAtual && celularAtual !== '-') {
        const celularLimpo = celularAtual.replace(/\D/g, '');
        $('#contato-celular').val(formatarTelefone(celularLimpo));
    } else {
        $('#contato-celular').val('');
    }
    
    $('#modalContato').modal('show');
}

function salvarContato() {
    const clienteId = $('#contato-cliente-id').val();
    const celular = $('#contato-celular').val().trim();
    
    if (!clienteId) {
        alert('Cliente não selecionado');
        return;
    }
    
    if (!celular) {
        alert('Digite o celular do cliente');
        return;
    }
    
    $.ajax({
        url: `/api/consulta/adicionar-contato/${clienteId}/`,
        method: 'POST',
        data: {
            celular: celular,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message || 'Contato adicionado com sucesso!');
                $('#dp-celular').text(formatarTelefone(response.celular));
                $('#modalContato').modal('hide');
                $('#contato-celular').val('');
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar contato: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

$(document).ready(function() {
    function formatarNumeroInput(input) {
        let valor = $(input).val();
        valor = valor.replace(/[^\d,.-]/g, '');
        valor = valor.replace(/\./g, ',');
        const partes = valor.split(',');
        if (partes.length > 2) {
            valor = partes[0] + ',' + partes.slice(1).join('');
        }
        $(input).val(valor);
    }
    
    $(document).on('input', '#simulacao_coef, #simulacao_parcela, #simulacao_saldo_devedor', function() {
        formatarNumeroInput(this);
        calcularSimulacao();
    });
    
    $(document).on('change', 'input[name="simulacao_checkboxes"]', function() {
        calcularSimulacao();
    });
    
    $(document).on('change', '#simulacao_checkbox_saldo_5, #simulacao_checkbox_saldo_5b, #simulacao_checkbox_saldo_35', function() {
        calcularSimulacao();
    });
    
    $(document).on('blur', '#simulacao_saldo_devedor', function() {
        calcularSimulacao();
    });
    
    $(document).on('change', '#simulacao-selecionar-todos', function() {
        const checked = $(this).is(':checked');
        $('input[name="simulacao_checkboxes"]').prop('checked', checked);
        calcularSimulacao();
    });
    
    // Máscara de telefone no campo de contato
    $('#contato-celular').on('input', function() {
        let valor = $(this).val().replace(/\D/g, '');
        if (valor.length <= 11) {
            if (valor.length <= 10) {
                valor = valor.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
            } else {
                valor = valor.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
            }
            $(this).val(valor);
        }
    });
});

