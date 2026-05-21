// Criar partículas animadas
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    if (!particlesContainer) return;
    
    const particleCount = 30;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = (10 + Math.random() * 10) + 's';
        particlesContainer.appendChild(particle);
    }
}

// Toggle de senha
function initPasswordToggle() {
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    
    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            const icon = this.querySelector('i');
            if (type === 'password') {
                icon.classList.remove('bx-show');
                icon.classList.add('bx-hide');
            } else {
                icon.classList.remove('bx-hide');
                icon.classList.add('bx-show');
            }
        });
    }
}

// Loading state no submit
function initLoginForm() {
    const loginForm = document.getElementById('loginForm');
    const submitBtn = document.getElementById('submitBtn');
    
    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', function() {
            submitBtn.classList.add('loading');
            submitBtn.innerHTML = '<i class="bx bx-loader-alt"></i><span>Entrando...</span>';
        });
    }
}

// Validação em tempo real
function initInputValidation() {
    const usernameInput = document.getElementById('username');
    const passwordInputField = document.getElementById('password');
    
    if (usernameInput) {
        usernameInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                this.style.borderColor = '#FFD700';
            }
        });
    }
    
    if (passwordInputField) {
        passwordInputField.addEventListener('input', function() {
            if (this.value.length > 0) {
                this.style.borderColor = '#FFD700';
            }
        });
    }
}

// Inicializar tudo ao carregar
document.addEventListener('DOMContentLoaded', function() {
    createParticles();
    initPasswordToggle();
    initLoginForm();
    initInputValidation();
});

