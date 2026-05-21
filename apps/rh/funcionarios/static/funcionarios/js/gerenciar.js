$(document).ready(function() {
    // Carregar funcionários ao carregar a página (com filtro de status = ativo)
    aplicarFiltros();
    
    // Aplicar filtros ao pressionar Enter no campo de busca
    $('#filtroBusca').on('keypress', function(e) {
        if (e.which === 13) {
            e.preventDefault();
            aplicarFiltros();
        }
    });
});

function aplicarFiltros() {
    const formData = {
        status: $('#filtroStatus').val(),
        empresa: $('#filtroEmpresa').val(),
        departamento: $('#filtroDepartamento').val(),
        setor: $('#filtroSetor').val(),
        loja: $('#filtroLoja').val(),
        equipe: $('#filtroEquipe').val(),
        cargo: $('#filtroCargo').val(),
        busca: $('#filtroBusca').val()
    };
    
    $.ajax({
        url: '/rh/funcionarios/api/gerenciar/listar/',
        method: 'GET',
        data: formData,
        success: function(dados) {
            atualizarTabela(dados);
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            console.error('Erro ao listar funcionários:', response);
            $('#funcionarios-tbody').html('<tr><td colspan="14" class="text-center text-danger">Erro ao carregar funcionários</td></tr>');
        }
    });
}

function limparFiltros() {
    $('#filtroStatus').val('ativo');
    $('#filtroEmpresa').val('');
    $('#filtroDepartamento').val('');
    $('#filtroSetor').val('');
    $('#filtroLoja').val('');
    $('#filtroEquipe').val('');
    $('#filtroCargo').val('');
    $('#filtroBusca').val('');
    aplicarFiltros();
}

function atualizarTabela(dados) {
    const tbody = $('#funcionarios-tbody');
    
    if (dados.length === 0) {
        tbody.html('<tr><td colspan="14" class="text-center">Nenhum funcionário encontrado</td></tr>');
        return;
    }
    
    let html = '';
    dados.forEach(function(func) {
        html += `
            <tr>
                <td>${escapeHtml(func.apelido || '-')}</td>
                <td>${escapeHtml(func.nome_completo)}</td>
                <td>${formatarCPF(func.cpf)}</td>
                <td>${func.data_nascimento || '-'}</td>
                <td>${escapeHtml(func.empresa)}</td>
                <td>${escapeHtml(func.departamento)}</td>
                <td>${escapeHtml(func.setor)}</td>
                <td>${escapeHtml(func.lojas)}</td>
                <td>${escapeHtml(func.equipe)}</td>
                <td>${escapeHtml(func.cargo)}</td>
                <td>${escapeHtml(func.horario)}</td>
                <td>${func.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                <td>${func.data_criacao}</td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="editarFuncionario(${func.id})" title="Editar">
                        <i class='bx bx-edit'></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.html(html);
}

function formatarCPF(cpf) {
    if (!cpf) return '-';
    cpf = cpf.replace(/\D/g, '');
    if (cpf.length === 11) {
        return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }
    return cpf;
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

function editarFuncionario(id) {
    $.ajax({
        url: `/rh/funcionarios/api/gerenciar/buscar/${id}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                popularFormulario(response.data);
                abrirModalFuncionario();
            } else {
                alert('Erro ao buscar funcionário: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao buscar funcionário: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function abrirModalFuncionario() {
    $('#modalFuncionario').fadeIn(300);
    $('body').css('overflow', 'hidden');
}

function fecharModalFuncionario() {
    $('#modalFuncionario').fadeOut(300);
    $('body').css('overflow', 'auto');
    limparFormulario();
}

function popularFormulario(dados) {
    $('#funcionario_id').val(dados.id);
    $('#apelido').val(dados.apelido || '');
    $('#nome_completo').val(dados.nome_completo || '');
    const cpfFormatado = formatarCPF(dados.cpf);
    $('#cpf').val(cpfFormatado).trigger('input');
    $('#rg').val(dados.rg || '');
    $('#data_nascimento').val(dados.data_nascimento || '');
    $('#chave_pix').val(dados.chave_pix || '');
    $('#status').prop('checked', dados.status);
    $('#grupo_permissões').val('');
    if (dados.foto) {
        $('#fotoPreview').attr('src', dados.foto).show();
        $('#btnRemoverFoto').show();
    } else {
        $('#fotoPreview').hide();
        $('#btnRemoverFoto').hide();
    }
    
    if (dados.dados_pessoais) {
        $('#genero').val(dados.dados_pessoais.genero_id || '');
        $('#estado_civil').val(dados.dados_pessoais.estado_civil || '');
        $('#nacionalidade').val(dados.dados_pessoais.nacionalidade || '');
        $('#naturalidade').val(dados.dados_pessoais.naturalidade || '');
    }
    
    if (dados.contato) {
        $('#email_pessoa').val(dados.contato.email_pessoa || '');
        $('#celular_1').val(dados.contato.celular_1 || '');
        $('#celular_2').val(dados.contato.celular_2 || '');
    }
    
    if (dados.localizacao) {
        $('#cep').val(dados.localizacao.cep || '');
        $('#endereco').val(dados.localizacao.endereco || '');
        $('#numero').val(dados.localizacao.numero || '');
        $('#complemento').val(dados.localizacao.complemento || '');
        $('#bairro').val(dados.localizacao.bairro || '');
        $('#cidade').val(dados.localizacao.cidade || '');
        $('#estado').val(dados.localizacao.estado || '');
    }
    
    if (dados.dados_profissionais) {
        $('#pis').val(dados.dados_profissionais.pis || '');
        $('#matricula').val(dados.dados_profissionais.matricula || '');
        $('#tipo_contrato').val(dados.dados_profissionais.tipo_contrato_id || '');
        $('#empresa').val(dados.dados_profissionais.empresa_id || '');
        $('#departamento').val(dados.dados_profissionais.departamento_id || '');
        $('#setor').val(dados.dados_profissionais.setor_id || '');
        $('#equipe').val(dados.dados_profissionais.equipe_id || '');
        $('#cargo').val(dados.dados_profissionais.cargo_id || '');
        $('#horario').val(dados.dados_profissionais.horario_id || '');
        $('#data_admissao').val(dados.dados_profissionais.data_admissao || '');
        $('#data_demissao').val(dados.dados_profissionais.data_demissao || '');
        
        if (dados.dados_profissionais.lojas_ids && dados.dados_profissionais.lojas_ids.length > 0) {
            $('#lojas').val(dados.dados_profissionais.lojas_ids);
        } else {
            $('#lojas').val([]);
        }
    }
    
    carregarDocumentos(dados.id);
}

function limparFormulario() {
    $('#formEditarFuncionario')[0].reset();
    $('#funcionario_id').val('');
    $('#chave_pix').val('');
    $('#fotoPreview').hide();
    $('#btnRemoverFoto').hide();
    $('#foto').val('');
    $('#formAdicionarDocumento')[0].reset();
    $('#documentos-tbody').html('<tr><td colspan="4" class="text-center">Nenhum documento cadastrado</td></tr>');
}

function previewFoto(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            $('#fotoPreview').attr('src', e.target.result).show();
            $('#btnRemoverFoto').show();
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function removerFoto() {
    $('#fotoPreview').hide();
    $('#btnRemoverFoto').hide();
    $('#foto').val('');
    $('#remover_foto_flag').remove();
    $('#formEditarFuncionario').append('<input type="hidden" id="remover_foto_flag" name="remover_foto" value="true">');
}

function salvarFuncionario() {
    const form = $('#formEditarFuncionario')[0];
    const formData = new FormData(form);
    
    const funcionarioId = $('#funcionario_id').val();
    if (!funcionarioId) {
        alert('ID do funcionário não encontrado');
        return;
    }
    
    const cpfValue = $('#cpf').val().replace(/\D/g, '');
    formData.set('cpf', cpfValue);
    
    if ($('#remover_foto_flag').length > 0) {
        formData.append('remover_foto', 'true');
    }
    
    $.ajax({
        url: `/rh/funcionarios/api/gerenciar/editar/${funcionarioId}/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message || 'Funcionário atualizado com sucesso!');
                fecharModalFuncionario();
                aplicarFiltros();
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao salvar funcionário: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

$(document).ready(function() {
    aplicarFiltros();
    $('#filtroBusca').on('keypress', function(e) {
        if (e.which === 13) {
            e.preventDefault();
            aplicarFiltros();
        }
    });
    
    $(document).on('click', function(e) {
        if ($(e.target).hasClass('modal-funcionario')) {
            fecharModalFuncionario();
        }
    });
    
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $('#modalFuncionario').is(':visible')) {
            fecharModalFuncionario();
        }
    });
});

function carregarDocumentos(funcionarioId) {
    if (!funcionarioId) {
        $('#documentos-tbody').html('<tr><td colspan="4" class="text-center">Nenhum documento cadastrado</td></tr>');
        return;
    }
    $.ajax({
        url: `/rh/funcionarios/api/gerenciar/documentos/${funcionarioId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                atualizarTabelaDocumentos(response.data);
            } else {
                $('#documentos-tbody').html('<tr><td colspan="4" class="text-center text-danger">Erro ao carregar documentos</td></tr>');
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            $('#documentos-tbody').html('<tr><td colspan="4" class="text-center text-danger">Erro ao carregar documentos</td></tr>');
        }
    });
}

function atualizarTabelaDocumentos(documentos) {
    const tbody = $('#documentos-tbody');
    if (documentos.length === 0) {
        tbody.html('<tr><td colspan="4" class="text-center">Nenhum documento cadastrado</td></tr>');
        return;
    }
    let html = '';
    documentos.forEach(function(doc) {
        html += `
            <tr>
                <td>${escapeHtml(doc.titulo)}</td>
                <td>${escapeHtml(doc.arquivo_nome)}</td>
                <td>${doc.data_criacao}</td>
                <td>
                    <a href="${doc.arquivo_url}" target="_blank" class="btn btn-sm btn-info" title="Download">
                        <i class='bx bx-download'></i>
                    </a>
                    <button class="btn btn-sm btn-danger" onclick="deletarDocumento(${doc.id})" title="Deletar">
                        <i class='bx bx-trash'></i>
                    </button>
                </td>
            </tr>
        `;
    });
    tbody.html(html);
}

function popularTituloArquivo(input) {
    if (input.files && input.files[0]) {
        const nomeArquivo = input.files[0].name;
        const nomeSemExtensao = nomeArquivo.replace(/\.[^/.]+$/, '');
        $('#documento_titulo').val(nomeSemExtensao);
    }
}

function adicionarDocumento() {
    const funcionarioId = $('#funcionario_id').val();
    const titulo = $('#documento_titulo').val().trim();
    const arquivo = $('#documento_arquivo')[0].files[0];
    if (!funcionarioId) {
        alert('ID do funcionário não encontrado');
        return;
    }
    if (!titulo) {
        alert('Título do documento é obrigatório');
        return;
    }
    if (!arquivo) {
        alert('Selecione um arquivo');
        return;
    }
    const formData = new FormData();
    formData.append('funcionario_id', funcionarioId);
    formData.append('titulo', titulo);
    formData.append('arquivo', arquivo);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    $.ajax({
        url: '/rh/funcionarios/api/gerenciar/documentos/adicionar/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message || 'Documento adicionado com sucesso!');
                $('#formAdicionarDocumento')[0].reset();
                carregarDocumentos(funcionarioId);
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao adicionar documento: ' + (response.message || 'Erro desconhecido'));
        }
    });
}

function deletarDocumento(documentoId) {
    if (!confirm('Tem certeza que deseja deletar este documento?')) {
        return;
    }
    const formData = new FormData();
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    $.ajax({
        url: `/rh/funcionarios/api/gerenciar/documentos/deletar/${documentoId}/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message || 'Documento removido com sucesso!');
                const funcionarioId = $('#funcionario_id').val();
                carregarDocumentos(funcionarioId);
            } else {
                alert('Erro: ' + (response.message || 'Erro desconhecido'));
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro ao deletar documento: ' + (response.message || 'Erro desconhecido'));
        }
    });
}
