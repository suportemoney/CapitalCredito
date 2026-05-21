// Gerenciamento de Comunicados - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Adicionar campo de arquivo
    const btnAdicionarArquivo = document.getElementById('btn-adicionar-arquivo');
    if (btnAdicionarArquivo) {
        btnAdicionarArquivo.addEventListener('click', function() {
            const container = document.getElementById('arquivos-container');
            const novoItem = document.createElement('div');
            novoItem.className = 'arquivo-item';
            novoItem.innerHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <input type="text" class="form-control" placeholder="Título do arquivo" name="titulos_arquivos[]">
                    </div>
                    <div class="col-md-7">
                        <input type="file" class="form-control" name="arquivos[]">
                    </div>
                    <div class="col-md-1">
                        <button type="button" class="btn-remover-arquivo" onclick="this.closest('.arquivo-item').remove()">
                            <i class='bx bx-x' style="color: #f44336;"></i>
                        </button>
                    </div>
                </div>
            `;
            container.appendChild(novoItem);
        });
    }
    
    // Formulário Criar
    const formCriar = document.getElementById('form-criar-comunicado');
    if (formCriar) {
        formCriar.addEventListener('submit', function(e) {
            e.preventDefault();
            criarComunicado();
        });
    }
    
    // Formulário Editar
    const formEditar = document.getElementById('form-editar-comunicado');
    if (formEditar) {
        formEditar.addEventListener('submit', function(e) {
            e.preventDefault();
            editarComunicado();
        });
    }
    
    // Toggle Status
    document.querySelectorAll('.btn-toggle-status').forEach(btn => {
        btn.addEventListener('click', function() {
            const comunicadoId = this.getAttribute('data-comunicado-id');
            toggleStatus(comunicadoId);
        });
    });
    
    // Deletar Comunicado
    document.querySelectorAll('.btn-deletar').forEach(btn => {
        btn.addEventListener('click', function() {
            const comunicadoId = this.getAttribute('data-comunicado-id');
            const comunicadoTitulo = this.getAttribute('data-comunicado-titulo');
            deletarComunicado(comunicadoId, comunicadoTitulo);
        });
    });
    
    // Deletar Arquivo
    document.querySelectorAll('.btn-deletar-arquivo').forEach(btn => {
        btn.addEventListener('click', function() {
            const arquivoId = this.getAttribute('data-arquivo-id');
            deletarArquivo(arquivoId);
        });
    });
    
    // Funções
    function criarComunicado() {
        const form = document.getElementById('form-criar-comunicado');
        const formData = new FormData(form);
        
        showLoading();
        
        fetch(API_URLS.criar, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(() => {
                    window.location.href = '/comunicados/gerenciar/';
                }, 1500);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            showMessage('Erro ao criar comunicado: ' + error, 'error');
        });
    }
    
    function editarComunicado() {
        const form = document.getElementById('form-editar-comunicado');
        const formData = new FormData(form);
        
        showLoading();
        
        fetch(API_URLS.editar, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(() => {
                    window.location.href = '/comunicados/gerenciar/';
                }, 1500);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            showMessage('Erro ao editar comunicado: ' + error, 'error');
        });
    }
    
    function toggleStatus(comunicadoId) {
        if (!confirm('Deseja alterar o status deste comunicado?')) return;
        
        fetch(`/comunicados/api/toggle-status/${comunicadoId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            showMessage('Erro ao alterar status: ' + error, 'error');
        });
    }
    
    function deletarComunicado(comunicadoId, comunicadoTitulo) {
        if (!confirm(`Tem certeza que deseja deletar o comunicado "${comunicadoTitulo}"? Esta ação não pode ser desfeita.`)) return;
        
        fetch(`/comunicados/api/deletar/${comunicadoId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            showMessage('Erro ao deletar comunicado: ' + error, 'error');
        });
    }
    
    function deletarArquivo(arquivoId) {
        if (!confirm('Tem certeza que deseja deletar este arquivo?')) return;
        
        const url = API_URLS.deletarArquivo.replace('0', arquivoId);
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            showMessage('Erro ao deletar arquivo: ' + error, 'error');
        });
    }
    
    // Funções auxiliares
    function showLoading() {
        // Criar overlay se não existir
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner">
                    <i class='bx bx-loader-alt bx-spin'></i>
                    <p>Processando...</p>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.style.display = 'flex';
    }
    
    function hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }
    
    function showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'}`;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideIn 0.3s;
            ${type === 'success' ? 'background: #4caf50; color: #ffffff;' : 'background: #f44336; color: #ffffff;'}
        `;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.style.animation = 'slideOut 0.3s';
            setTimeout(() => messageDiv.remove(), 300);
        }, 3000);
    }
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});

// Adicionar estilos de animação
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .loading-spinner {
        text-align: center;
        color: #FFD700;
    }
    
    .loading-spinner i {
        font-size: 48px;
        margin-bottom: 15px;
        display: block;
    }
    
    .loading-spinner p {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
    }
`;
document.head.appendChild(style);

