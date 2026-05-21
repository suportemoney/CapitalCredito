$(document).ready(function() {
    // Máscara para CPF
    $('#cpf').on('input', function() {
        let value = $(this).val().replace(/\D/g, '');
        if (value.length <= 11) {
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
            $(this).val(value);
        }
    });
    
    // Submissão do formulário
    $('#formNovoFuncionario').on('submit', function(e) {
        e.preventDefault();
        
        const form = this;
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const formData = new FormData(form);
        
        $.ajax({
            url: '/rh/funcionarios/api/novo/criar/',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if (response.success) {
                    alert(response.message);
                    window.location.href = '/rh/funcionarios/gerenciar/';
                } else {
                    alert('Erro: ' + response.message);
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                alert('Erro: ' + (response.message || 'Erro ao cadastrar funcionário'));
            }
        });
    });
});

