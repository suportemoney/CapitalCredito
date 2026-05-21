// Função para alternar o menu do usuário
function toggleUserMenu() {
    const menu = document.getElementById('user-menu-popup');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
}

// Prevenir clique em itens desabilitados
document.addEventListener('DOMContentLoaded', function() {
    const disabledItems = document.querySelectorAll('.user-menu-item--disabled');
    disabledItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
        });
    });
});

// Fechar menu ao clicar fora
document.addEventListener('click', function(event) {
    const menu = document.getElementById('user-menu-popup');
    const wrapper = document.querySelector('.user-profile-wrapper');
    if (menu && wrapper && !wrapper.contains(event.target) && !menu.contains(event.target)) {
        menu.style.display = 'none';
    }
});

