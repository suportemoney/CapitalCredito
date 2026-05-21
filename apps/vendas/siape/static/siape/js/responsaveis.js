$(document).ready(function() {
    carregarUsuariosDisponiveis();
    carregarResponsaveis();
});

function carregarUsuariosDisponiveis() {
    $.ajax({
        url: '/api/responsaveis/listar-usuarios/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const select = $('#responsavel_usuarios');
                select.empty();
                response.data.forEach(function(user) {
                    select.append(`<option value="${user.id}">${user.nome} (${user.username})</option>`);
                });
            } else {
                console.error('[Responsáveis] Erro ao carregar usuários:', response.message);
                alert('Erro ao carregar usuários: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('[Responsáveis] Erro na requisição de usuários:', {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            alert('Erro ao carregar usuários disponíveis.');
        }
    });
}

function carregarResponsaveis() {
    $.ajax({
        url: '/api/responsaveis/listar/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                exibirResponsaveis(response.data);
            } else {
                console.error('[Responsáveis] Erro ao carregar responsáveis:', response.message);
                alert('Erro ao carregar responsáveis: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('[Responsáveis] Erro na requisição de responsáveis:', {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            $('#responsaveis-tbody').html('<tr><td colspan="8" class="text-center text-danger">Erro ao carregar responsáveis</td></tr>');
        }
    });
}

function exibirResponsaveis(data) {
    const tbody = $('#responsaveis-tbody');
    tbody.empty();
    
    if (data.length === 0) {
        tbody.append('<tr><td colspan="8" class="text-center">Nenhum responsável cadastrado</td></tr>');
        return;
    }
    
    data.forEach(function(resp) {
        const usuariosHtml = resp.usuarios.length > 0 
            ? resp.usuarios.map(u => u.nome).join(', ')
            : 'Nenhum usuário';
        
        const horarioHtml = resp.horario_inicio && resp.horario_final
            ? `${escapeHtml(resp.horario_inicio)} - ${escapeHtml(resp.horario_final)}`
            : 'Não definido';
        
        const tempoCallHtml = resp.tempo_call 
            ? `${escapeHtml(resp.tempo_call)} min`
            : '30 min';
        
        const statusBadge = resp.status 
            ? '<span class="badge bg-success">Ativo</span>'
            : '<span class="badge bg-secondary">Inativo</span>';
        
        const row = `
            <tr>
                <td>${resp.id}</td>
                <td>${escapeHtml(resp.tipo_display)}</td>
                <td>${escapeHtml(usuariosHtml)}</td>
                <td>${horarioHtml}</td>
                <td>${tempoCallHtml}</td>
                <td>${statusBadge}</td>
                <td>${escapeHtml(resp.data_criacao)}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editarResponsavel(${resp.id})" title="Editar">
                        <i class='bx bx-edit'></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deletarResponsavel(${resp.id}, '${escapeHtml(resp.tipo_display)}')" title="Deletar">
                        <i class='bx bx-trash'></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
}

function abrirModalCriarResponsavel() {
    $('#formResponsavel')[0].reset();
    $('#responsavel_id').val('');
    $('#modalResponsavelTitle').text('Novo Responsável');
    $('#responsavel_usuarios').val([]);
    
    const modal = new bootstrap.Modal(document.getElementById('modalResponsavel'));
    modal.show();
}

function editarResponsavel(id) {
    $.ajax({
        url: `/api/responsaveis/editar/${id}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const data = response.data;
                $('#responsavel_id').val(data.id);
                $('#responsavel_tipo').val(data.tipo);
                $('#responsavel_status').prop('checked', data.status);
                $('#responsavel_horario_inicio').val(data.horario_inicio || '');
                $('#responsavel_horario_final').val(data.horario_final || '');
                $('#responsavel_tempo_call').val(data.tempo_call || 30);
                
                const usuariosIds = data.usuarios.map(u => u.id);
                $('#responsavel_usuarios').val(usuariosIds);
                
                $('#modalResponsavelTitle').text('Editar Responsável');
                const modal = new bootstrap.Modal(document.getElementById('modalResponsavel'));
                modal.show();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('[Responsáveis] Erro ao buscar responsável:', {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            alert('Erro ao buscar responsável: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function salvarResponsavel() {
    const id = $('#responsavel_id').val();
    const tipo = $('#responsavel_tipo').val();
    const usuarios = $('#responsavel_usuarios').val();
    const horarioInicio = $('#responsavel_horario_inicio').val();
    const horarioFinal = $('#responsavel_horario_final').val();
    const tempoCall = $('#responsavel_tempo_call').val();
    const status = $('#responsavel_status').is(':checked');
    
    if (!tipo) {
        alert('Selecione o tipo de responsável.');
        return;
    }
    
    if (!usuarios || usuarios.length === 0) {
        alert('Selecione pelo menos um usuário responsável.');
        return;
    }
    
    if (!horarioInicio || !horarioFinal) {
        alert('Preencha horário de início e final.');
        return;
    }
    
    if (!tempoCall || tempoCall < 1) {
        alert('Preencha o tempo de call (em minutos).');
        return;
    }
    
    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('horario_inicio', horarioInicio);
    formData.append('horario_final', horarioFinal);
    formData.append('tempo_call', tempoCall);
    formData.append('status', status ? 'on' : 'off');
    usuarios.forEach(function(userId) {
        formData.append('usuarios', userId);
    });
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    const url = id 
        ? `/api/responsaveis/editar/${id}/`
        : '/api/responsaveis/criar/';
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                bootstrap.Modal.getInstance(document.getElementById('modalResponsavel')).hide();
                carregarResponsaveis();
                alert(response.message);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('[Responsáveis] Erro ao salvar responsável:', {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            alert('Erro ao salvar responsável: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function deletarResponsavel(id, tipoDisplay) {
    if (!confirm(`Tem certeza que deseja deletar o responsável "${tipoDisplay}"?`)) {
        return;
    }
    
    $.ajax({
        url: `/api/responsaveis/deletar/${id}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                carregarResponsaveis();
                alert(response.message);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('[Responsáveis] Erro ao deletar responsável:', {
                status: xhr.status,
                statusText: xhr.statusText,
                message: response.message || 'Erro desconhecido'
            });
            alert('Erro ao deletar responsável: ' + (response.message || 'Erro desconhecido'));
        }
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

