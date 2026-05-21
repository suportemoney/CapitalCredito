$(document).ready(function() {
    carregarMetas();
});

function carregarMetas() {
    $.ajax({
        url: '/api/metas/listar/',
        method: 'GET',
        success: function(response) {
            const tbody = $('#metas-tbody');
            tbody.empty();
            
            if (!response.success || response.data.length === 0) {
                tbody.append('<tr><td colspan="8" class="text-center">Nenhuma meta cadastrada</td></tr>');
                return;
            }
            
            response.data.forEach(function(meta) {
                const statusBadge = meta.status ? 
                    '<span class="badge bg-success">Ativa</span>' : 
                    '<span class="badge bg-danger">Inativa</span>';
                
                const valorFormatado = formatarMoeda(meta.valor_meta);
                const dataInicio = formatarData(meta.data_inicio);
                const dataFinal = formatarData(meta.data_final);
                
                tbody.append(`
                    <tr>
                        <td>${meta.id}</td>
                        <td>${escapeHtml(meta.titulo)}</td>
                        <td>${valorFormatado}</td>
                        <td>${dataInicio}</td>
                        <td>${dataFinal}</td>
                        <td>${statusBadge}</td>
                        <td>${meta.data_criacao}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="abrirModalEditarMeta(${meta.id})" title="Editar">
                                <i class='bx bx-edit'></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deletarMeta(${meta.id}, '${escapeHtml(meta.titulo)}')" title="Deletar">
                                <i class='bx bx-trash'></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        },
        error: function(xhr) {
            console.error('Erro ao carregar metas:', xhr);
            const response = xhr.responseJSON || {};
            $('#metas-tbody').html(`<tr><td colspan="8" class="text-center text-danger">Erro ao carregar metas: ${response.message || 'Erro desconhecido'}</td></tr>`);
        }
    });
}

function abrirModalCriarMeta() {
    $('#modalMetaTitle').text('Nova Meta');
    $('#formMeta')[0].reset();
    $('#meta_id').val('');
    $('#meta_status').prop('checked', true);
    const modalElement = document.getElementById('modalMeta');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function abrirModalEditarMeta(id) {
    $.ajax({
        url: `/api/metas/editar/${id}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const meta = response.data;
                $('#modalMetaTitle').text('Editar Meta');
                $('#meta_id').val(meta.id);
                $('#meta_titulo').val(meta.titulo);
                $('#meta_valor').val(meta.valor_meta);
                $('#meta_data_inicio').val(meta.data_inicio);
                $('#meta_data_final').val(meta.data_final);
                $('#meta_status').prop('checked', meta.status);
                
                const modalElement = document.getElementById('modalMeta');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
                    modal.show();
                } else if (modalElement) {
                    $(modalElement).modal('show');
                }
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao carregar meta: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function salvarMeta() {
    const form = $('#formMeta');
    const metaId = $('#meta_id').val();
    const formData = new FormData(form[0]);
    formData.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());
    
    const url = metaId ? 
        `/api/metas/editar/${metaId}/` : 
        '/api/metas/criar/';
    const method = 'POST';
    
    $.ajax({
        url: url,
        method: method,
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                const modalElement = document.getElementById('modalMeta');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
                carregarMetas();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar meta: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function deletarMeta(id, titulo) {
    if (!confirm(`Tem certeza que deseja deletar a meta "${titulo}"?`)) {
        return;
    }
    
    $.ajax({
        url: `/api/metas/deletar/${id}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                carregarMetas();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao deletar meta: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function formatarMoeda(valor) {
    if (!valor || valor === 0) return 'R$ 0,00';
    return 'R$ ' + parseFloat(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatarData(dataString) {
    if (!dataString) return '-';
    const [ano, mes, dia] = dataString.split('-');
    return `${dia}/${mes}/${ano}`;
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

