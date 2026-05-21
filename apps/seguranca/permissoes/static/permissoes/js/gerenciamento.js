// Gerenciamento de Permissões - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Controle de Tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Remove active de todas as tabs
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');
            
            // Ativa a tab clicada
            this.classList.add('active');
            document.getElementById(`tab-${tabId}`).style.display = 'block';
            
            // Atualiza contadores
            updateTabCounts();
        });
    });
    
    // Ativa a primeira tab por padrão
    if (tabButtons.length > 0) {
        tabButtons[0].click();
    }
    
    // Função para atualizar contadores das tabs
    function updateTabCounts() {
        tabButtons.forEach(btn => {
            const tabId = btn.getAttribute('data-tab');
            const checked = document.querySelectorAll(`#tab-${tabId} .checkbox-permissao:checked`).length;
            const countElement = btn.querySelector('.tab-count');
            if (countElement) {
                countElement.textContent = checked;
            }
        });
        
        // Atualiza total de permissões
        const totalChecked = document.querySelectorAll('.checkbox-permissao:checked').length;
        const totalElement = document.getElementById('total-permissoes');
        if (totalElement) {
            totalElement.textContent = totalChecked;
        }
    }
    
    // Event listeners para checkboxes
    document.querySelectorAll('.checkbox-permissao').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateTabCounts();
        });
    });
    
    // Selecionar/Deselecionar Todos
    document.querySelectorAll('.btn-select-all').forEach(btn => {
        btn.addEventListener('click', function() {
            const tipo = this.getAttribute('data-tipo');
            document.querySelectorAll(`#tab-${tipo} .checkbox-permissao`).forEach(cb => {
                cb.checked = true;
            });
            updateTabCounts();
        });
    });
    
    document.querySelectorAll('.btn-deselect-all').forEach(btn => {
        btn.addEventListener('click', function() {
            const tipo = this.getAttribute('data-tipo');
            document.querySelectorAll(`#tab-${tipo} .checkbox-permissao`).forEach(cb => {
                cb.checked = false;
            });
            updateTabCounts();
        });
    });
    
    // Aplicar Grupo
    document.querySelectorAll('.btn-aplicar-grupo').forEach(btn => {
        btn.addEventListener('click', function() {
            const grupoId = this.getAttribute('data-grupo-id');
            const grupoNome = this.getAttribute('data-grupo-nome');
            
            if (confirm(`Deseja aplicar o grupo "${grupoNome}"? As permissões serão adicionadas às existentes.`)) {
                aplicarGrupo(grupoId);
            }
        });
    });
    
    // Salvar Todas as Permissões
    const btnSalvar = document.getElementById('btn-salvar');
    if (btnSalvar) {
        btnSalvar.addEventListener('click', function() {
            salvarTodasPermissoes();
        });
    }
    
    // Função para aplicar grupo
    function aplicarGrupo(grupoId) {
        showLoading();
        
        const formData = new FormData();
        formData.append('grupo_id', grupoId);
        
        fetch(API_URLS.aplicarGrupo, {
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
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            showMessage('Erro ao aplicar grupo: ' + error, 'error');
        });
    }
    
    // Função para salvar todas as permissões
    function salvarTodasPermissoes() {
        const checkedBoxes = document.querySelectorAll('.checkbox-permissao:checked');
        const acessoIds = Array.from(checkedBoxes).map(cb => cb.getAttribute('data-acesso-id'));
        
        if (acessoIds.length === 0) {
            if (!confirm('Nenhuma permissão selecionada. Deseja remover todas as permissões do usuário?')) {
                return;
            }
        }
        
        showLoading();
        
        const formData = new FormData();
        acessoIds.forEach(id => {
            formData.append('acesso_ids[]', id);
        });
        
        fetch(API_URLS.salvar, {
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
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            hideLoading();
            showMessage('Erro ao salvar permissões: ' + error, 'error');
        });
    }
    
    // Funções auxiliares
    function showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'flex';
    }
    
    function hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }
    
    function showMessage(message, type) {
        // Criar elemento de mensagem
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
        `;
        messageDiv.textContent = message;
        
        if (type === 'success') {
            messageDiv.style.background = '#4caf50';
            messageDiv.style.color = '#ffffff';
        } else {
            messageDiv.style.background = '#f44336';
            messageDiv.style.color = '#ffffff';
        }
        
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
    
    // Inicializar contadores
    updateTabCounts();
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
`;
document.head.appendChild(style);

