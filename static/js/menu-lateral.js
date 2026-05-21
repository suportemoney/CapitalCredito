// Menu lateral - Funcionalidades com submenu à direita
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    
    const toggleIcon = sidebar.querySelector('.sidebar-toggle i');
    const categoryToggles = sidebar.querySelectorAll('.category-toggle');
    const submenuPanel = document.getElementById('submenu-panel');
    const submenuContent = document.getElementById('submenu-content');
    const submenuClose = document.getElementById('submenu-close');
    const submenuTitle = submenuPanel?.querySelector('.submenu-title');

    // Função para aplicar configuração do menu
    function aplicarConfiguracaoMenu() {
        const manterMenuAberto = localStorage.getItem('manter_menu_aberto') === 'true';
        
        if (!manterMenuAberto) {
            sidebar.classList.add('collapsed');
            if (toggleIcon) {
                toggleIcon.classList.add('bx-menu-alt-right');
                toggleIcon.classList.remove('bx-menu');
            }
        } else {
            sidebar.classList.remove('collapsed');
            if (toggleIcon) {
                toggleIcon.classList.remove('bx-menu-alt-right');
                toggleIcon.classList.add('bx-menu');
            }
        }
    }
    
    // Aplicar configuração inicial
    aplicarConfiguracaoMenu();

    // Função para abrir o sidebar
    function openSidebar() {
        if (sidebar.classList.contains('collapsed')) {
            sidebar.classList.remove('collapsed');
            if (toggleIcon) {
                toggleIcon.classList.remove('bx-menu-alt-right');
                toggleIcon.classList.add('bx-menu');
            }
        }
    }

    // Função para fechar o submenu
    function closeSubmenu() {
        if (submenuPanel) {
            submenuPanel.classList.remove('active');
            document.body.classList.remove('submenu-active');
            sidebar.querySelectorAll('.sidebar-category.active').forEach(cat => {
                cat.classList.remove('active');
            });
        }
    }

    // Clique no ícone de toggle
    const sidebarToggle = sidebar.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            if (toggleIcon) {
                toggleIcon.classList.toggle('bx-menu-alt-right');
                toggleIcon.classList.toggle('bx-menu');
            }

            // Ao fechar, fecha todas as categorias abertas e o submenu
            if (sidebar.classList.contains('collapsed')) {
                sidebar.querySelectorAll('.sidebar-category.active')
                       .forEach(cat => cat.classList.remove('active'));
                closeSubmenu();
            }
        });
    }

    // Clique no botão de fechar submenu
    if (submenuClose) {
        submenuClose.addEventListener('click', closeSubmenu);
    }

    // Clique em cada categoria - abre submenu à direita
    categoryToggles.forEach(catToggle => {
        catToggle.addEventListener('click', e => {
            e.preventDefault();
            e.stopPropagation();

            // Se o sidebar estiver fechado, abre antes
            openSidebar();

            const category = catToggle.closest('.sidebar-category');
            const categoryName = category?.getAttribute('data-category');
            const subcategoryMenu = category?.querySelector('.subcategory-menu');

            console.log('[DEBUG MENU] Categoria clicada:', categoryName);
            console.log('[DEBUG MENU] Category element:', category);
            console.log('[DEBUG MENU] SubcategoryMenu element:', subcategoryMenu);
            console.log('[DEBUG MENU] SubmenuPanel:', submenuPanel);
            console.log('[DEBUG MENU] SubmenuContent:', submenuContent);

            if (!category || !subcategoryMenu || !submenuPanel || !submenuContent) {
                console.error('[DEBUG MENU] Elementos não encontrados!');
                return;
            }

            console.log('[DEBUG MENU] Conteúdo do subcategoryMenu:', subcategoryMenu.innerHTML);
            console.log('[DEBUG MENU] Número de subcategorias:', subcategoryMenu.querySelectorAll('.subcategory-item').length);

            // Se a categoria já está ativa, fecha o submenu
            if (category.classList.contains('active')) {
                closeSubmenu();
                return;
            }

            // Remove active de todas as outras categorias
            sidebar.querySelectorAll('.sidebar-category.active')
                   .forEach(cat => cat.classList.remove('active'));

            // Ativa a categoria clicada
            category.classList.add('active');

            // Define o título do submenu
            const categoryLabel = catToggle.querySelector('.menu-label')?.textContent || '';
            if (submenuTitle) {
                submenuTitle.textContent = categoryLabel;
            }

            // Copia o conteúdo do submenu para o painel
            const submenuClone = subcategoryMenu.cloneNode(true);
            submenuClone.style.display = 'block'; // Remove display none
            
            // Garantir que todos os links mantenham seus hrefs corretos
            const links = submenuClone.querySelectorAll('a');
            links.forEach(link => {
                const originalHref = link.getAttribute('href');
                // Se o link tem um href válido (não é javascript:void(0)), mantém
                if (originalHref && !originalHref.includes('javascript:void(0)')) {
                    // Garante que o href está correto e remove qualquer event listener que possa interferir
                    link.setAttribute('href', originalHref);
                    // Remove qualquer event listener que possa estar impedindo a navegação
                    const newLink = link.cloneNode(true);
                    link.parentNode.replaceChild(newLink, link);
                    console.log('[DEBUG MENU] Link preservado e clonado:', originalHref, '->', newLink.href, newLink.textContent.trim());
                } else {
                    console.log('[DEBUG MENU] Link sem href válido:', link.textContent.trim());
                }
            });
            
            console.log('[DEBUG MENU] Clone criado:', submenuClone);
            console.log('[DEBUG MENU] Conteúdo do clone:', submenuClone.innerHTML);
            console.log('[DEBUG MENU] Subcategorias no clone:', submenuClone.querySelectorAll('.subcategory-item').length);
            
            submenuContent.innerHTML = '';
            submenuContent.appendChild(submenuClone);
            
            console.log('[DEBUG MENU] Conteúdo após append:', submenuContent.innerHTML);
            console.log('[DEBUG MENU] Subcategorias após append:', submenuContent.querySelectorAll('.subcategory-item').length);

            // Abre o submenu
            submenuPanel.classList.add('active');
            document.body.classList.add('submenu-active');

            // Adiciona event listeners aos subcategorias dentro do submenu
            setupSubcategoryListeners();
        });
    });

    // Função para configurar listeners das subcategorias
    function setupSubcategoryListeners() {
        const subcategoryToggles = submenuContent.querySelectorAll('.subcategory-toggle');
        
        subcategoryToggles.forEach(subToggle => {
            // Remove listeners anteriores para evitar duplicação
            const newSubToggle = subToggle.cloneNode(true);
            subToggle.parentNode.replaceChild(newSubToggle, subToggle);
            
            newSubToggle.addEventListener('click', e => {
                e.preventDefault();
                e.stopPropagation();

                const subcategoryItem = newSubToggle.closest('.subcategory-item');
                if (!subcategoryItem) return;

                // Fecha todas as outras subcategorias
                submenuContent.querySelectorAll('.subcategory-item.expanded')
                       .forEach(item => {
                           if (item !== subcategoryItem) {
                               item.classList.remove('expanded');
                           }
                       });

                // Alterna a subcategoria clicada
                subcategoryItem.classList.toggle('expanded');
            });
        });
        
        // Garantir que os links dentro de .options-menu funcionem normalmente
        // Não adicionamos event listeners - deixamos os links funcionarem naturalmente
        const optionLinks = submenuContent.querySelectorAll('.options-menu a');
        optionLinks.forEach(link => {
            // Remove qualquer event listener que possa estar interferindo
            const originalHref = link.getAttribute('href');
            if (originalHref && !originalHref.includes('javascript:void(0)')) {
                // Cria um novo link limpo para garantir que não há interferência
                const newLink = document.createElement('a');
                newLink.href = originalHref;
                newLink.innerHTML = link.innerHTML;
                newLink.className = link.className;
                link.parentNode.replaceChild(newLink, link);
                console.log('[DEBUG MENU] Link limpo criado:', newLink.href, newLink.textContent.trim());
            } else {
                console.log('[DEBUG MENU] Link sem href válido:', link.textContent.trim());
            }
        });
    }

    // Fechar submenu ao clicar fora (opcional)
    document.addEventListener('click', (e) => {
        if (submenuPanel && submenuPanel.classList.contains('active')) {
            // Se o clique foi em um link dentro do submenu, permite navegação normal
            const clickedLink = e.target.closest('a');
            if (clickedLink && clickedLink.closest('.options-menu')) {
                // Permite que o link funcione normalmente - não fecha o submenu
                console.log('[DEBUG MENU] Link clicado, permitindo navegação:', clickedLink.href);
                return;
            }
            
            // Se o clique foi em um toggle de subcategoria, não fecha
            if (e.target.closest('.subcategory-toggle')) {
                return;
            }
            
            const isClickInsideSidebar = sidebar.contains(e.target);
            const isClickInsideSubmenu = submenuPanel.contains(e.target);
            
            if (!isClickInsideSidebar && !isClickInsideSubmenu) {
                closeSubmenu();
            }
        }
    });
});
