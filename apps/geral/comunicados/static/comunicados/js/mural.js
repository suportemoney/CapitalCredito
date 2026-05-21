// Mural de Comunicados - Funcionalidades

document.addEventListener('DOMContentLoaded', function() {
    // Marcar comunicado como visualizado ao clicar
    const comunicadoCards = document.querySelectorAll('.comunicado-card');
    
    comunicadoCards.forEach(card => {
        card.addEventListener('click', function() {
            const comunicadoId = this.getAttribute('data-comunicado-id');
            if (comunicadoId && !this.querySelector('.comunicado-novo')) {
                // Remover badge "Novo" após visualizar
                const novoBadge = this.querySelector('.comunicado-novo');
                if (novoBadge) {
                    novoBadge.style.opacity = '0';
                    setTimeout(() => {
                        novoBadge.remove();
                    }, 300);
                }
            }
        });
    });
    
    // Animação de entrada dos cards
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    comunicadoCards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(card);
    });
});

