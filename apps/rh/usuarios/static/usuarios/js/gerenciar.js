$(document).ready(function() {
    carregarUsuarios();
});

function carregarUsuarios() {
    $.ajax({
        url: '/rh/usuarios/api/gerenciar/listar/',
        method: 'GET',
        success: function(dados) {
            atualizarTabela(dados);
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('Erro ao listar usuários:', response);
            $('#usuarios-tbody').html('<tr><td colspan="7" class="text-center text-danger">Erro ao carregar usuários</td></tr>');
        }
    });
}

function atualizarTabela(dados) {
    const tbody = $('#usuarios-tbody');
    
    if (dados.length === 0) {
        tbody.html('<tr><td colspan="7" class="text-center">Nenhum usuário encontrado</td></tr>');
        return;
    }
    
    let html = '';
    dados.forEach(function(user) {
        const funcionarioInfo = user.funcionario 
            ? `${escapeHtml(user.funcionario.apelido || user.funcionario.nome_completo)} (${user.funcionario.cpf})`
            : '<span class="text-muted">Não associado</span>';
        
        const statusChecked = user.status ? 'checked' : '';
        const statusBadge = user.status 
            ? '<span class="badge bg-success">Ativo</span>' 
            : '<span class="badge bg-danger">Inativo</span>';
        
        html += `
            <tr data-user-id="${user.id}">
                <td>${escapeHtml(user.username)}</td>
                <td>
                    <code class="senha-padrao">${escapeHtml(user.senha_padrao)}</code>
                    <button class="btn btn-sm btn-link p-0 ms-2" onclick="copiarSenha('${escapeHtml(user.senha_padrao)}')" title="Copiar senha">
                        <i class='bx bx-copy'></i>
                    </button>
                </td>
                <td>${user.data_criacao}</td>
                <td>${funcionarioInfo}</td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input status-toggle" 
                               type="checkbox" 
                               data-user-id="${user.id}"
                               ${statusChecked}
                               onchange="atualizarStatus(${user.id}, this.checked)">
                        <label class="form-check-label">
                            ${statusBadge}
                        </label>
                    </div>
                </td>
                <td>${escapeHtml(user.email)}</td>
                <td>${escapeHtml(user.first_name + ' ' + user.last_name).trim() || '-'}</td>
            </tr>
        `;
    });
    
    tbody.html(html);
}

function atualizarStatus(userId, status) {
    const formData = new FormData();
    formData.append('status', status);
    
    $.ajax({
        url: `/rh/usuarios/api/gerenciar/atualizar-status/${userId}/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                // Atualizar badge na tabela
                const row = $(`tr[data-user-id="${userId}"]`);
                const label = row.find('.form-check-label');
                if (response.status) {
                    label.html('<span class="badge bg-success">Ativo</span>');
                } else {
                    label.html('<span class="badge bg-danger">Inativo</span>');
                }
                
                // Mostrar feedback visual
                mostrarFeedback('Status atualizado com sucesso!', 'success');
            } else {
                alert('Erro: ' + response.message);
                // Reverter checkbox
                carregarUsuarios();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao atualizar status'));
            // Reverter checkbox
            carregarUsuarios();
        }
    });
}

function copiarSenha(senha) {
    navigator.clipboard.writeText(senha).then(function() {
        mostrarFeedback('Senha copiada para a área de transferência!', 'success');
    }, function() {
        // Fallback para navegadores mais antigos
        const textarea = document.createElement('textarea');
        textarea.value = senha;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        mostrarFeedback('Senha copiada para a área de transferência!', 'success');
    });
}

function mostrarFeedback(mensagem, tipo) {
    // Criar elemento de feedback
    const feedback = $(`
        <div class="alert alert-${tipo === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('body').append(feedback);
    
    // Remover após 3 segundos
    setTimeout(function() {
        feedback.fadeOut(function() {
            $(this).remove();
        });
    }, 3000);
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

