$(document).ready(function() {
    carregarProdutos();
});

function carregarProdutos() {
    $.ajax({
        url: '/api/produtos/listar/',
        method: 'GET',
        success: function(response) {
            const tbody = $('#produtos-tbody');
            tbody.empty();
            
            if (!response.success || response.data.length === 0) {
                tbody.append('<tr><td colspan="6" class="text-center">Nenhum produto cadastrado</td></tr>');
                return;
            }
            
            response.data.forEach(function(prod) {
                const statusBadge = prod.status ? 
                    '<span class="badge bg-success">Ativo</span>' : 
                    '<span class="badge bg-danger">Inativo</span>';
                
                const descricao = prod.descricao ? escapeHtml(prod.descricao) : '<span class="text-muted">-</span>';
                
                tbody.append(`
                    <tr>
                        <td>${prod.id}</td>
                        <td>${escapeHtml(prod.nome)}</td>
                        <td>${descricao}</td>
                        <td>${statusBadge}</td>
                        <td>${prod.data_criacao}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="abrirModalEditarProduto(${prod.id})" title="Editar">
                                <i class='bx bx-edit'></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deletarProduto(${prod.id}, '${escapeHtml(prod.nome)}')" title="Deletar">
                                <i class='bx bx-trash'></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        },
        error: function(xhr) {
            console.error('Erro ao carregar produtos:', xhr);
            const response = xhr.responseJSON || {};
            $('#produtos-tbody').html(`<tr><td colspan="6" class="text-center text-danger">Erro ao carregar produtos: ${response.message || 'Erro desconhecido'}</td></tr>`);
        }
    });
}

function abrirModalCriarProduto() {
    $('#modalProdutoTitle').text('Novo Produto');
    $('#formProduto')[0].reset();
    $('#produto_id').val('');
    $('#produto_status').prop('checked', true);
    const modalElement = document.getElementById('modalProduto');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    } else if (modalElement) {
        $(modalElement).modal('show');
    }
}

function abrirModalEditarProduto(id) {
    $.ajax({
        url: `/api/produtos/editar/${id}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const prod = response.data;
                $('#modalProdutoTitle').text('Editar Produto');
                $('#produto_id').val(prod.id);
                $('#produto_nome').val(prod.nome);
                $('#produto_descricao').val(prod.descricao || '');
                $('#produto_status').prop('checked', prod.status);
                
                const modalElement = document.getElementById('modalProduto');
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
            alert('Erro ao carregar produto: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function salvarProduto() {
    const form = $('#formProduto');
    const produtoId = $('#produto_id').val();
    const formData = new FormData(form[0]);
    formData.append('csrfmiddlewaretoken', $('input[name="csrfmiddlewaretoken"]').val());
    
    const url = produtoId ? 
        `/api/produtos/editar/${produtoId}/` : 
        '/api/produtos/criar/';
    const method = produtoId ? 'POST' : 'POST';
    
    $.ajax({
        url: url,
        method: method,
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                const modalElement = document.getElementById('modalProduto');
                if (modalElement && typeof bootstrap !== 'undefined') {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    modal.hide();
                } else if (modalElement) {
                    $(modalElement).modal('hide');
                }
                carregarProdutos();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar produto: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function deletarProduto(id, nome) {
    if (!confirm(`Tem certeza que deseja deletar o produto "${nome}"?`)) {
        return;
    }
    
    $.ajax({
        url: `/api/produtos/deletar/${id}/`,
        method: 'POST',
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(response) {
            if (response.success) {
                alert(response.message);
                carregarProdutos();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao deletar produto: ' + (response.message || 'Erro desconhecido'));
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

