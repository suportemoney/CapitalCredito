$(document).ready(function() {
    carregarNomeFuncionario();
    carregarPontosDia();
    iniciarRelogio();
});

function iniciarRelogio() {
    function atualizarRelogio() {
        const horaEl = document.getElementById('relogioHora');
        const minutoEl = document.getElementById('relogioMinuto');
        const segundoEl = document.getElementById('relogioSegundo');
        if (horaEl && minutoEl && segundoEl) {
            const agora = new Date();
            const horas = String(agora.getHours()).padStart(2, '0');
            const minutos = String(agora.getMinutes()).padStart(2, '0');
            const segundos = String(agora.getSeconds()).padStart(2, '0');
            horaEl.textContent = horas;
            minutoEl.textContent = minutos;
            segundoEl.textContent = segundos;
        }
    }
    atualizarRelogio();
    setInterval(atualizarRelogio, 1000);
}

function carregarNomeFuncionario() {
    const nomeUsuario = $('#saudacao').data('nome-usuario') || 'Usuário';
    $('#saudacao').text('Olá, ' + nomeUsuario + '!');
}

function registrarPonto() {
    const btn = $('#btnRegistrarPonto');
    btn.prop('disabled', true).html('<i class="bx bx-loader-alt bx-spin"></i> Registrando...');
    $.ajax({
        url: '/rh/ponto/api/registro/registrar/',
        method: 'POST',
        headers: {
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val() || $('meta[name=csrf-token]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                mostrarMensagem('success', response.message);
                carregarPontosDia();
            } else {
                mostrarMensagem('error', response.message);
            }
        },
        error: function(xhr) {
            let mensagem = 'Erro ao registrar presença';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                mensagem = xhr.responseJSON.message;
            }
            mostrarMensagem('error', mensagem);
        },
        complete: function() {
            btn.prop('disabled', false).html('<i class="bx bx-log-in"></i> Registrar Presença');
        }
    });
}

function carregarPontosDia() {
    $.ajax({
        url: '/rh/ponto/api/registro/listar-dia/',
        method: 'GET',
        success: function(response) {
            const tbody = $('#tbodyPontos');
            tbody.empty();
            if (response.success && response.data.length > 0) {
                response.data.forEach(function(ponto) {
                    const dataFormatada = ponto.data_hora.split(' ')[0];
                    const linha = `
                        <tr>
                            <td>${ponto.tipo} ${ponto.numero}</td>
                            <td>${ponto.horario}</td>
                            <td>${dataFormatada}</td>
                        </tr>
                    `;
                    tbody.append(linha);
                });
            } else {
                tbody.append('<tr><td colspan="3" class="text-center text-muted">Nenhum registro de presença hoje</td></tr>');
            }
        },
        error: function() {
            $('#tbodyPontos').html('<tr><td colspan="3" class="text-center text-danger">Erro ao carregar registros</td></tr>');
        }
    });
}

function mostrarMensagem(tipo, mensagem) {
    const alertClass = tipo === 'success' ? 'alert-success' : 'alert-danger';
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
