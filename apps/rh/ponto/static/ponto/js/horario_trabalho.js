const DIAS_SEMANA = ['SEGUNDA', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SABADO', 'DOMINGO'];
const DIAS_NOMES = {
    'SEGUNDA': 'Segunda-feira',
    'TERCA': 'Terça-feira',
    'QUARTA': 'Quarta-feira',
    'QUINTA': 'Quinta-feira',
    'SEXTA': 'Sexta-feira',
    'SABADO': 'Sábado',
    'DOMINGO': 'Domingo'
};

let funcionariosFimSemana = {};

$(document).ready(function() {
    $('.funcionario-checkbox').on('change', function() {
        const funcionarioId = $(this).val();
        if ($(this).is(':checked')) {
            carregarConfiguracaoExistente(funcionarioId);
        }
        verificarBotoesCopiar();
    });
    verificarBotoesCopiar();
});

function verificarBotoesCopiar() {
    let temDiaAtivo = false;
    DIAS_SEMANA.forEach(function(dia) {
        const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
        if ($(`#check${prefixo}`).is(':checked')) {
            temDiaAtivo = true;
        }
    });
    if (temDiaAtivo) {
        $('#btnCopiarHorarios').show();
    } else {
        $('#btnCopiarHorarios').hide();
    }
}

function toggleDiaHorario(dia) {
    const checkbox = $(`#check${dia.charAt(0) + dia.slice(1).toLowerCase()}`);
    const campos = $(`#campos${dia.charAt(0) + dia.slice(1).toLowerCase()}`);
    if (checkbox.is(':checked')) {
        campos.slideDown();
    } else {
        campos.slideUp();
        limparCamposDia(dia);
    }
    verificarBotoesCopiar();
}

function limparCamposDia(dia) {
    const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
    $(`#entrada1${prefixo}`).val('');
    $(`#saida1${prefixo}`).val('');
    $(`#entrada2${prefixo}`).val('');
    $(`#saida2${prefixo}`).val('');
    $(`#almocoFlexivel${prefixo}`).prop('checked', false);
}

function copiarHorarios() {
    const diasAtivos = [];
    DIAS_SEMANA.forEach(function(dia) {
        const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
        if ($(`#check${prefixo}`).is(':checked')) {
            const entrada1 = $(`#entrada1${prefixo}`).val();
            const saida1 = $(`#saida1${prefixo}`).val();
            if (entrada1 && saida1) {
                diasAtivos.push({
                    dia: dia,
                    entrada1: entrada1,
                    saida1: saida1,
                    entrada2: $(`#entrada2${prefixo}`).val(),
                    saida2: $(`#saida2${prefixo}`).val(),
                    almocoFlexivel: $(`#almocoFlexivel${prefixo}`).is(':checked')
                });
            }
        }
    });
    if (diasAtivos.length === 0) {
        mostrarMensagem('error', 'Nenhum dia com horários preenchidos encontrado');
        return;
    }
    const diaOrigem = diasAtivos[0];
    let copiados = 0;
    diasAtivos.slice(1).forEach(function(diaDestino) {
        const prefixo = diaDestino.dia.charAt(0) + diaDestino.dia.slice(1).toLowerCase();
        $(`#entrada1${prefixo}`).val(diaOrigem.entrada1);
        $(`#saida1${prefixo}`).val(diaOrigem.saida1);
        $(`#entrada2${prefixo}`).val(diaOrigem.entrada2);
        $(`#saida2${prefixo}`).val(diaOrigem.saida2);
        $(`#almocoFlexivel${prefixo}`).prop('checked', diaOrigem.almocoFlexivel);
        copiados++;
    });
    if (copiados > 0) {
        mostrarMensagem('success', `Horários de ${DIAS_NOMES[diaOrigem.dia]} copiados para ${copiados} dia(s)`);
    } else {
        mostrarMensagem('info', 'Apenas um dia está ativo');
    }
}

function copiarDiaParaOutros(diaOrigem) {
    const prefixoOrigem = diaOrigem.charAt(0) + diaOrigem.slice(1).toLowerCase();
    const entrada1 = $(`#entrada1${prefixoOrigem}`).val();
    const saida1 = $(`#saida1${prefixoOrigem}`).val();
    const entrada2 = $(`#entrada2${prefixoOrigem}`).val();
    const saida2 = $(`#saida2${prefixoOrigem}`).val();
    const almocoFlexivel = $(`#almocoFlexivel${prefixoOrigem}`).is(':checked');
    if (!entrada1 || !saida1) {
        mostrarMensagem('error', `Preencha pelo menos Entrada 1 e Saída 1 em ${DIAS_NOMES[diaOrigem]} antes de copiar`);
        return;
    }
    let copiados = 0;
    DIAS_SEMANA.forEach(function(dia) {
        if (dia !== diaOrigem) {
            const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
            const checkbox = $(`#check${prefixo}`);
            if (checkbox.is(':checked')) {
                $(`#entrada1${prefixo}`).val(entrada1);
                $(`#saida1${prefixo}`).val(saida1);
                $(`#entrada2${prefixo}`).val(entrada2);
                $(`#saida2${prefixo}`).val(saida2);
                $(`#almocoFlexivel${prefixo}`).prop('checked', almocoFlexivel);
                copiados++;
            }
        }
    });
    if (copiados > 0) {
        mostrarMensagem('success', `Horários de ${DIAS_NOMES[diaOrigem]} copiados para ${copiados} dia(s) ativo(s)`);
    } else {
        mostrarMensagem('info', 'Nenhum outro dia está ativo para copiar os horários');
    }
}

function abrirModalFimSemana() {
    const funcionariosSelecionados = [];
    $('.funcionario-checkbox:checked').each(function() {
        funcionariosSelecionados.push($(this).val());
    });
    if (funcionariosSelecionados.length === 0) {
        mostrarMensagem('error', 'Selecione pelo menos um funcionário antes de configurar fins de semana');
        return;
    }
    $('.fim-semana-checkbox').prop('checked', false);
    funcionariosSelecionados.forEach(function(id) {
        if (funcionariosFimSemana[id]) {
            $(`#fimSemana_${id}`).prop('checked', true);
        }
    });
    const modal = new bootstrap.Modal(document.getElementById('modalFimSemana'));
    modal.show();
}

function salvarFimSemana() {
    funcionariosFimSemana = {};
    $('.fim-semana-checkbox:checked').each(function() {
        funcionariosFimSemana[$(this).val()] = true;
    });
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalFimSemana'));
    modal.hide();
    mostrarMensagem('success', 'Configuração de fins de semana salva! (será aplicada ao salvar a configuração)');
}

function salvarConfiguracao() {
    const funcionariosSelecionados = [];
    $('.funcionario-checkbox:checked').each(function() {
        funcionariosSelecionados.push($(this).val());
    });
    if (funcionariosSelecionados.length === 0) {
        mostrarMensagem('error', 'Selecione pelo menos um funcionário');
        return;
    }
    const horariosPorDia = {};
    let erroValidacao = false;
    DIAS_SEMANA.forEach(function(dia) {
        if (erroValidacao) return;
        const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
        const checkbox = $(`#check${prefixo}`);
        if (checkbox.is(':checked')) {
            const entrada1 = $(`#entrada1${prefixo}`).val();
            const saida1 = $(`#saida1${prefixo}`).val();
            const entrada2 = $(`#entrada2${prefixo}`).val();
            const saida2 = $(`#saida2${prefixo}`).val();
            const almocoFlexivel = $(`#almocoFlexivel${prefixo}`).is(':checked');
            if (!entrada1 || !saida1) {
                mostrarMensagem('error', `Preencha pelo menos Entrada 1 e Saída 1 para ${DIAS_NOMES[dia]}`);
                erroValidacao = true;
                return;
            }
            if ((entrada2 && !saida2) || (!entrada2 && saida2)) {
                mostrarMensagem('error', `Para ${DIAS_NOMES[dia]}, se preencher Entrada 2, deve preencher Saída 2 também (ou deixe ambos vazios)`);
                erroValidacao = true;
                return;
            }
            horariosPorDia[dia] = {
                entrada1: entrada1,
                saida1: saida1,
                entrada2: entrada2 || null,
                saida2: saida2 || null,
                almoco_flexivel: almocoFlexivel
            };
        }
    });
    if (erroValidacao) {
        return;
    }
    const formData = new FormData();
    funcionariosSelecionados.forEach(function(id) {
        formData.append('funcionarios_ids[]', id);
        const trabalhaFimSemana = funcionariosFimSemana[id] || false;
        formData.append(`trabalha_fim_semana[${id}]`, trabalhaFimSemana);
    });
    formData.append('horarios_por_dia', JSON.stringify(horariosPorDia));
    $.ajax({
        url: '/rh/ponto/api/horario/configurar/',
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
            } else {
                mostrarMensagem('error', response.message);
            }
        },
        error: function(xhr) {
            let mensagem = 'Erro ao salvar configuração';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                mensagem = xhr.responseJSON.message;
            }
            mostrarMensagem('error', mensagem);
        }
    });
}

function carregarConfiguracaoExistente(funcionarioId) {
    $.ajax({
        url: '/rh/ponto/api/horario/buscar/',
        method: 'GET',
        data: { funcionario_id: funcionarioId },
        success: function(response) {
            if (response.success && response.data) {
                const config = response.data;
                if (config.trabalha_fim_semana) {
                    funcionariosFimSemana[funcionarioId] = true;
                }
                if (config.horarios_por_dia) {
                    Object.keys(config.horarios_por_dia).forEach(function(dia) {
                        const horario = config.horarios_por_dia[dia];
                        const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
                        $(`#check${prefixo}`).prop('checked', true);
                        $(`#entrada1${prefixo}`).val(horario.entrada1 || '');
                        $(`#saida1${prefixo}`).val(horario.saida1 || '');
                        $(`#entrada2${prefixo}`).val(horario.entrada2 || '');
                        $(`#saida2${prefixo}`).val(horario.saida2 || '');
                        $(`#almocoFlexivel${prefixo}`).prop('checked', horario.almoco_flexivel || false);
                        $(`#campos${prefixo}`).show();
                    });
                }
                verificarBotoesCopiar();
            }
        },
        error: function() {
        }
    });
}

function limparFormulario() {
    $('.funcionario-checkbox').prop('checked', false);
    funcionariosFimSemana = {};
    DIAS_SEMANA.forEach(function(dia) {
        const prefixo = dia.charAt(0) + dia.slice(1).toLowerCase();
        $(`#check${prefixo}`).prop('checked', false);
        limparCamposDia(dia);
        $(`#campos${prefixo}`).hide();
    });
    verificarBotoesCopiar();
}

function mostrarMensagem(tipo, mensagem) {
    let alertClass = 'alert-info';
    if (tipo === 'success') {
        alertClass = 'alert-success';
    } else if (tipo === 'error') {
        alertClass = 'alert-danger';
    } else if (tipo === 'info') {
        alertClass = 'alert-info';
    }
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
