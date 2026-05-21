$(document).ready(function() {
    carregarClassificadores();
});

function carregarClassificadores() {
    $.ajax({
        url: '/vendas/financeiro/api/classificador/listar/',
        method: 'GET',
        success: function(response) {
            const tbody = $('#classificadores-tbody');
            tbody.empty();
            
            if (!response.success || response.data.length === 0) {
                tbody.append('<tr><td colspan="6" class="text-center">Nenhum classificador cadastrado</td></tr>');
                return;
            }
            
            response.data.forEach(function(classif) {
                const statusBadge = classif.status ? 
                    '<span class="badge bg-success">Ativo</span>' : 
                    '<span class="badge bg-danger">Inativo</span>';
                
                tbody.append(`
                    <tr>
                        <td>${classif.id}</td>
                        <td>${escapeHtml(classif.titulo)}</td>
                        <td>${classif.percentual.toFixed(2)}%</td>
                        <td>${statusBadge}</td>
                        <td>${classif.data_criacao}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="abrirModalEditarClassificador(${classif.id})" title="Editar">
                                <i class='bx bx-edit'></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deletarClassificador(${classif.id}, '${escapeHtml(classif.titulo)}')" title="Deletar">
                                <i class='bx bx-trash'></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        },
        error: function(xhr) {
            console.error('Erro ao carregar classificadores:', xhr);
            const response = xhr.responseJSON || {};
            $('#classificadores-tbody').html(`<tr><td colspan="6" class="text-center text-danger">Erro ao carregar classificadores: ${response.message || 'Erro desconhecido'}</td></tr>`);
        }
    });
}

function abrirModalCriarClassificador() {
    $('#modalClassificadorTitle').text('Novo Classificador');
    $('#formClassificador')[0].reset();
    $('#classificador_id').val('');
    $('#classificador_status').prop('checked', true);
    const modalElement = document.getElementById('modalClassificador');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function abrirModalEditarClassificador(id) {
    $.ajax({
        url: `/vendas/financeiro/api/classificador/editar/${id}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const classif = response.data;
                $('#modalClassificadorTitle').text('Editar Classificador');
                $('#classificador_id').val(classif.id);
                $('#classificador_titulo').val(classif.titulo);
                $('#classificador_percentual').val(classif.percentual);
                $('#classificador_status').prop('checked', classif.status);
                
                const modalElement = document.getElementById('modalClassificador');
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
            alert('Erro ao carregar classificador: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function salvarClassificador() {
    const form = $('#formClassificador');
    const classificadorId = $('#classificador_id').val();
    const formData = new FormData(form[0]);
    formData.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());
    
    const percentual = parseFloat($('#classificador_percentual').val());
    if (isNaN(percentual) || percentual < 0 || percentual > 100) {
        alert('Percentual deve estar entre 0 e 100');
        return;
    }
    
    const url = classificadorId ? 
        `/vendas/financeiro/api/classificador/editar/${classificadorId}/` : 
        '/vendas/financeiro/api/classificador/criar/';
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
                const modalElement = document.getElementById('modalClassificador');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
                carregarClassificadores();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar classificador: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function deletarClassificador(id, titulo) {
    if (!confirm(`Tem certeza que deseja deletar o classificador "${titulo}"?`)) {
        return;
    }
    
    $.ajax({
        url: `/vendas/financeiro/api/classificador/deletar/${id}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                carregarClassificadores();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao deletar classificador: ' + (response.message || 'Erro desconhecido'));
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

