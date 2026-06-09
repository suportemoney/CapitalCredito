// Variáveis globais
let idEditandoAcesso = null;
let idEditandoGrupo = null;
let usuarioSelecionadoId = null;
let todosAcessos = [];
let todosGrupos = [];
let modalAcesso = null;
let modalGrupo = null;

$(document).ready(function() {
    modalAcesso = new bootstrap.Modal(document.getElementById('modalAcesso'));
    modalGrupo = new bootstrap.Modal(document.getElementById('modalGrupo'));
    
    // Carregar dados ao abrir cada tab
    $('#acessos-tab').on('shown.bs.tab', function() {
        carregarAcessos();
    });
    
    $('#grupos-tab').on('shown.bs.tab', function() {
        carregarGrupos();
        atualizarSeletorGrupos();
    });
    
    $('#usuarios-tab').on('shown.bs.tab', function() {
        atualizarSeletorGrupos();
        if (usuarioSelecionadoId) {
            carregarPermissoesUsuario();
        }
    });

    $('#lote-tab').on('shown.bs.tab', function() {
        carregarPermissoesLote();
        atualizarResumoLote();
    });
    
    // Carregar acessos e grupos na primeira vez
    carregarAcessos();
    carregarGrupos();
    atualizarSeletorGrupos();
    // Filtro em tempo real
    $('#search-acessos').on('input', aplicarFiltroAcessos);
    $('#search-grupos').on('input', aplicarFiltroGrupos);
    $('#search-lote-usuarios').on('input', aplicarFiltroLoteUsuarios);
    $('#search-lote-permissoes').on('input', aplicarFiltroLotePermissoes);

    $(document).on('change', '.lote-usuario-cb, .lote-permissao-cb', atualizarResumoLote);
});

function aplicarFiltroAcessos() {
    const termo = ($('#search-acessos').val() || '').trim().toLowerCase();
    const filtrado = termo === '' ? todosAcessos : todosAcessos.filter(function(a) {
        const cod = (a.codigo || '').toLowerCase();
        const nom = (a.nome || '').toLowerCase();
        return cod.indexOf(termo) !== -1 || nom.indexOf(termo) !== -1;
    });
    atualizarTabelaAcessos(filtrado);
}

function aplicarFiltroGrupos() {
    const termo = ($('#search-grupos').val() || '').trim().toLowerCase();
    const filtrado = termo === '' ? todosGrupos : todosGrupos.filter(function(g) {
        const tit = (g.titulo || '').toLowerCase();
        const desc = (g.descricao || '').toLowerCase();
        return tit.indexOf(termo) !== -1 || desc.indexOf(termo) !== -1;
    });
    atualizarTabelaGrupos(filtrado);
}

// ========== TAB 1: CRUD Acesso ==========

function carregarAcessos() {
    $.ajax({
        url: '/seguranca/permissoes/api/gerenciar/acessos/listar/',
        method: 'GET',
        success: function(dados) {
            todosAcessos = dados;
            aplicarFiltroAcessos();
        },
        error: function(xhr) {
            console.error('Erro ao carregar acessos:', xhr);
            $('#acessos-tbody').html('<tr><td colspan="7" class="text-center text-danger">Erro ao carregar permissões</td></tr>');
        }
    });
}

function atualizarTabelaAcessos(dados) {
    const tbody = $('#acessos-tbody');
    
    if (dados.length === 0) {
        tbody.html('<tr><td colspan="7" class="text-center">Nenhuma permissão cadastrada</td></tr>');
        return;
    }
    
    let html = '';
    dados.forEach(function(acesso) {
        html += `
            <tr>
                <td><code>${escapeHtml(acesso.codigo)}</code></td>
                <td>${escapeHtml(acesso.nome)}</td>
                <td>${escapeHtml(acesso.tipo_display)}</td>
                <td>${escapeHtml(acesso.descricao || '-')}</td>
                <td>${acesso.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                <td>${acesso.data_criacao}</td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="abrirModalEditarAcesso(${acesso.id})">
                        <i class='bx bx-edit'></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deletarAcesso(${acesso.id}, '${escapeHtml(acesso.nome)}')">
                        <i class='bx bx-trash'></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.html(html);
}

function abrirModalCriarAcesso() {
    idEditandoAcesso = null;
    $('#modalAcessoTitle').text('Criar Permissão');
    $('#formAcesso')[0].reset();
    $('#formAcesso input[name="status"]').prop('checked', true);
    modalAcesso.show();
}

function abrirModalEditarAcesso(acessoId) {
    idEditandoAcesso = acessoId;
    $('#modalAcessoTitle').text('Editar Permissão');
    
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/acessos/editar/${acessoId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const dados = response.data;
                $('#formAcesso input[name="nome"]').val(dados.nome);
                $('#formAcesso select[name="tipo"]').val(dados.tipo);
                $('#formAcesso textarea[name="descricao"]').val(dados.descricao);
                $('#formAcesso input[name="status"]').prop('checked', dados.status);
                modalAcesso.show();
            }
        },
        error: function() {
            alert('Erro ao carregar dados da permissão');
        }
    });
}

function salvarAcesso() {
    const form = $('#formAcesso')[0];
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    const url = idEditandoAcesso 
        ? `/seguranca/permissoes/api/gerenciar/acessos/editar/${idEditandoAcesso}/`
        : '/seguranca/permissoes/api/gerenciar/acessos/criar/';
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                modalAcesso.hide();
                // Atualizar todas as partes que dependem de acessos
                carregarAcessos();
                atualizarSeletorGrupos();
                // Se estiver na tab de usuários e tiver usuário selecionado, recarregar
                if (usuarioSelecionadoId) {
                    carregarPermissoesUsuario();
                }
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao salvar permissão'));
        }
    });
}

function deletarAcesso(acessoId, nome) {
    if (!confirm(`Tem certeza que deseja deletar a permissão "${nome}"?`)) {
        return;
    }
    
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/acessos/deletar/${acessoId}/`,
        method: 'POST',
        success: function(response) {
            if (response.success) {
                alert(response.message);
                // Atualizar todas as partes que dependem de acessos
                carregarAcessos();
                atualizarSeletorGrupos();
                // Se estiver na tab de usuários e tiver usuário selecionado, recarregar
                if (usuarioSelecionadoId) {
                    carregarPermissoesUsuario();
                }
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao deletar permissão'));
        }
    });
}

// ========== TAB 2: CRUD GroupsAcessos ==========

function carregarGrupos() {
    $.ajax({
        url: '/seguranca/permissoes/api/gerenciar/grupos/listar/',
        method: 'GET',
        success: function(dados) {
            todosGrupos = dados;
            aplicarFiltroGrupos();
            atualizarSeletorGrupos();
        },
        error: function(xhr) {
            console.error('Erro ao carregar grupos:', xhr);
            $('#grupos-tbody').html('<tr><td colspan="6" class="text-center text-danger">Erro ao carregar grupos</td></tr>');
        }
    });
}

function atualizarTabelaGrupos(dados) {
    const tbody = $('#grupos-tbody');
    
    if (dados.length === 0) {
        tbody.html('<tr><td colspan="6" class="text-center">Nenhum grupo cadastrado</td></tr>');
        return;
    }
    
    let html = '';
    dados.forEach(function(grupo) {
        html += `
            <tr>
                <td>${escapeHtml(grupo.titulo)}</td>
                <td>${escapeHtml(grupo.descricao || '-')}</td>
                <td><span class="badge bg-info">${grupo.acessos_count}</span></td>
                <td>${grupo.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                <td>${grupo.data_criacao}</td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="abrirModalEditarGrupo(${grupo.id})">
                        <i class='bx bx-edit'></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deletarGrupo(${grupo.id}, '${escapeHtml(grupo.titulo)}')">
                        <i class='bx bx-trash'></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.html(html);
}

function abrirModalCriarGrupo() {
    idEditandoGrupo = null;
    $('#modalGrupoTitle').text('Criar Grupo');
    $('#formGrupo')[0].reset();
    $('#formGrupo input[name="status"]').prop('checked', true);
    carregarCheckboxesPermissoesGrupo([]);
    modalGrupo.show();
}

function abrirModalEditarGrupo(grupoId) {
    idEditandoGrupo = grupoId;
    $('#modalGrupoTitle').text('Editar Grupo');
    
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/grupos/editar/${grupoId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const dados = response.data;
                $('#formGrupo input[name="titulo"]').val(dados.titulo);
                $('#formGrupo textarea[name="descricao"]').val(dados.descricao);
                $('#formGrupo input[name="status"]').prop('checked', dados.status);
                carregarCheckboxesPermissoesGrupo(dados.acessos_ids || []);
                modalGrupo.show();
            }
        },
        error: function() {
            alert('Erro ao carregar dados do grupo');
        }
    });
}

function carregarCheckboxesPermissoesGrupo(acessosSelecionados) {
    const container = $('#checkboxes-permissoes-grupo');
    
    if (todosAcessos.length === 0) {
        // Carregar acessos se ainda não foram carregados
        $.ajax({
            url: '/seguranca/permissoes/api/gerenciar/acessos/listar/',
            method: 'GET',
            success: function(dados) {
                todosAcessos = dados;
                renderizarCheckboxesPermissoes(dados, acessosSelecionados, container);
            }
        });
    } else {
        renderizarCheckboxesPermissoes(todosAcessos, acessosSelecionados, container);
    }
}

function renderizarCheckboxesPermissoes(acessos, selecionados, container) {
    let html = '';
    
    // Agrupar por tipo
    const porTipo = {};
    acessos.forEach(acesso => {
        if (!porTipo[acesso.tipo]) {
            porTipo[acesso.tipo] = [];
        }
        porTipo[acesso.tipo].push(acesso);
    });
    
    Object.keys(porTipo).forEach(tipo => {
        html += `<div class="mb-3"><strong>${porTipo[tipo][0].tipo_display}:</strong><br>`;
        porTipo[tipo].forEach(acesso => {
            const checked = selecionados.includes(acesso.id) ? 'checked' : '';
            html += `
                <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" name="acessos[]" value="${acesso.id}" id="perm-${acesso.id}" ${checked}>
                    <label class="form-check-label" for="perm-${acesso.id}">
                        ${escapeHtml(acesso.nome)} (<code>${escapeHtml(acesso.codigo)}</code>)
                    </label>
                </div>
            `;
        });
        html += '</div>';
    });
    
    container.html(html);
}

function salvarGrupo() {
    const form = $('#formGrupo')[0];
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    const acessosSelecionados = [];
    $('#checkboxes-permissoes-grupo input[type="checkbox"]:checked').each(function() {
        acessosSelecionados.push($(this).val());
    });
    
    acessosSelecionados.forEach(id => {
        formData.append('acessos[]', id);
    });
    
    const url = idEditandoGrupo 
        ? `/seguranca/permissoes/api/gerenciar/grupos/editar/${idEditandoGrupo}/`
        : '/seguranca/permissoes/api/gerenciar/grupos/criar/';
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                modalGrupo.hide();
                // Atualizar grupos e seletor
                carregarGrupos();
                atualizarSeletorGrupos();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao salvar grupo'));
        }
    });
}

function deletarGrupo(grupoId, titulo) {
    if (!confirm(`Tem certeza que deseja deletar o grupo "${titulo}"?`)) {
        return;
    }
    
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/grupos/deletar/${grupoId}/`,
        method: 'POST',
        success: function(response) {
            if (response.success) {
                alert(response.message);
                // Atualizar grupos e seletor
                carregarGrupos();
                atualizarSeletorGrupos();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao deletar grupo'));
        }
    });
}

// ========== TAB 3: CRUD ControleAcessos ==========

function carregarPermissoesUsuario() {
    const userId = $('#selectUsuario').val();
    
    if (!userId) {
        $('#container-permissoes-usuario').hide();
        $('#mensagem-sem-usuario').show();
        return;
    }
    
    usuarioSelecionadoId = userId;
    $('#container-permissoes-usuario').show();
    $('#mensagem-sem-usuario').hide();
    
    // Carregar controle do usuário
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/usuarios/get-controle/${userId}/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const dados = response.data;
                renderizarPermissoesUsuario(dados.acessos_ids || []);
            }
        },
        error: function() {
            // Se não tem controle, criar do zero
            renderizarPermissoesUsuario([]);
        }
    });
}

function renderizarPermissoesUsuario(acessosSelecionados) {
    const container = $('#permissoes-usuario-container');
    
    if (todosAcessos.length === 0) {
        // Carregar acessos se ainda não foram carregados
        $.ajax({
            url: '/seguranca/permissoes/api/gerenciar/acessos/listar/',
            method: 'GET',
            success: function(dados) {
                todosAcessos = dados;
                renderizarCheckboxesPermissoes(dados, acessosSelecionados, container);
            }
        });
    } else {
        renderizarCheckboxesPermissoes(todosAcessos, acessosSelecionados, container);
    }
}

function aplicarGrupoUsuario() {
    const grupoId = $('#selectGrupoUsuario').val();
    
    if (!grupoId || !usuarioSelecionadoId) {
        return;
    }
    
    if (!confirm('Aplicar este grupo substituirá todas as permissões atuais do usuário. Deseja continuar?')) {
        $('#selectGrupoUsuario').val('');
        return;
    }
    
    const formData = new FormData();
    formData.append('aplicar_grupo', grupoId);
    
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/usuarios/salvar/${usuarioSelecionadoId}/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                $('#selectGrupoUsuario').val('');
                // Recarregar permissões do usuário
                carregarPermissoesUsuario();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao aplicar grupo'));
        }
    });
}

function salvarPermissoesUsuario() {
    if (!usuarioSelecionadoId) {
        alert('Selecione um usuário primeiro');
        return;
    }
    
    const acessosSelecionados = [];
    $('#permissoes-usuario-container input[type="checkbox"]:checked').each(function() {
        acessosSelecionados.push($(this).val());
    });
    
    const formData = new FormData();
    acessosSelecionados.forEach(id => {
        formData.append('acessos[]', id);
    });
    
    $.ajax({
        url: `/seguranca/permissoes/api/gerenciar/usuarios/salvar/${usuarioSelecionadoId}/`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao salvar permissões'));
        }
    });
}

function atualizarSeletorGrupos() {
    // Atualizar seletor de grupos na tab de usuários
    $.ajax({
        url: '/seguranca/permissoes/api/gerenciar/grupos/listar/',
        method: 'GET',
        success: function(dados) {
            todosGrupos = dados;
            const select = $('#selectGrupoUsuario');
            let html = '<option value="">Selecione um grupo...</option>';
            dados.forEach(function(grupo) {
                if (grupo.status) {
                    html += `<option value="${grupo.id}">${escapeHtml(grupo.titulo)}</option>`;
                }
            });
            select.html(html);
        },
        error: function() {
            console.error('Erro ao atualizar seletor de grupos');
        }
    });
}

// ========== TAB 4: Permissões em Lote ==========

function carregarPermissoesLote() {
    const container = $('#lote-permissoes-container');

    if (todosAcessos.length === 0) {
        $.ajax({
            url: '/seguranca/permissoes/api/gerenciar/acessos/listar/',
            method: 'GET',
            success: function(dados) {
                todosAcessos = dados;
                renderizarPermissoesLote(dados);
            },
            error: function() {
                container.html('<p class="text-danger text-center">Erro ao carregar permissões</p>');
            }
        });
    } else {
        renderizarPermissoesLote(todosAcessos);
    }
}

function renderizarPermissoesLote(acessos) {
    const container = $('#lote-permissoes-container');
    const ativos = acessos.filter(function(a) { return a.status; });

    if (ativos.length === 0) {
        container.html('<p class="text-center text-muted">Nenhuma permissão disponível</p>');
        return;
    }

    const porTipo = {};
    ativos.forEach(function(acesso) {
        if (!porTipo[acesso.tipo]) {
            porTipo[acesso.tipo] = [];
        }
        porTipo[acesso.tipo].push(acesso);
    });

    let html = '';
    Object.keys(porTipo).forEach(function(tipo) {
        html += '<div class="mb-3 lote-tipo-grupo"><strong>' + escapeHtml(porTipo[tipo][0].tipo_display) + ':</strong><br>';
        porTipo[tipo].forEach(function(acesso) {
            const busca = ((acesso.nome || '') + ' ' + (acesso.codigo || '')).toLowerCase();
            html += `
                <div class="form-check lote-permissao-item" data-busca="${escapeHtml(busca)}">
                    <input class="form-check-input lote-permissao-cb" type="checkbox" value="${acesso.id}" id="lote-perm-${acesso.id}">
                    <label class="form-check-label" for="lote-perm-${acesso.id}">
                        ${escapeHtml(acesso.nome)} (<code>${escapeHtml(acesso.codigo)}</code>)
                    </label>
                </div>
            `;
        });
        html += '</div>';
    });

    container.html(html);
    aplicarFiltroLotePermissoes();
    atualizarResumoLote();
}

function aplicarFiltroLoteUsuarios() {
    const termo = ($('#search-lote-usuarios').val() || '').trim().toLowerCase();
    $('.lote-usuario-item').each(function() {
        const username = $(this).data('username') || '';
        const texto = $(this).text().toLowerCase();
        const visivel = termo === '' || username.indexOf(termo) !== -1 || texto.indexOf(termo) !== -1;
        $(this).toggleClass('hidden', !visivel);
    });
}

function aplicarFiltroLotePermissoes() {
    const termo = ($('#search-lote-permissoes').val() || '').trim().toLowerCase();
    $('.lote-permissao-item').each(function() {
        const busca = ($(this).data('busca') || '').toString();
        const visivel = termo === '' || busca.indexOf(termo) !== -1;
        $(this).toggleClass('hidden', !visivel);
    });
}

function selecionarTodosLote(tipo, selecionar) {
    if (tipo === 'usuarios') {
        $('.lote-usuario-item:not(.hidden) .lote-usuario-cb').prop('checked', selecionar);
    } else {
        $('.lote-permissao-item:not(.hidden) .lote-permissao-cb').prop('checked', selecionar);
    }
    atualizarResumoLote();
}

function atualizarResumoLote() {
    const qtdUsuarios = $('.lote-usuario-cb:checked').length;
    const qtdPermissoes = $('.lote-permissao-cb:checked').length;
    const resumo = $('#lote-resumo');

    if (qtdUsuarios === 0 && qtdPermissoes === 0) {
        resumo.hide();
        return;
    }

    resumo.html(
        '<i class="bx bx-check-square"></i> ' +
        qtdUsuarios + ' usuário(s) e ' + qtdPermissoes + ' permissão(ões) selecionado(s)'
    ).show();
}

function aplicarPermissoesLote(acao) {
    const usuariosSelecionados = [];
    const permissoesSelecionadas = [];

    $('.lote-usuario-cb:checked').each(function() {
        usuariosSelecionados.push($(this).val());
    });

    $('.lote-permissao-cb:checked').each(function() {
        permissoesSelecionadas.push($(this).val());
    });

    if (usuariosSelecionados.length === 0) {
        alert('Selecione pelo menos um usuário');
        return;
    }

    if (permissoesSelecionadas.length === 0) {
        alert('Selecione pelo menos uma permissão');
        return;
    }

    const verbo = acao === 'adicionar' ? 'adicionar' : 'remover';
    const msg = 'Deseja ' + verbo + ' ' + permissoesSelecionadas.length +
        ' permissão(ões) para ' + usuariosSelecionados.length + ' usuário(s)?';

    if (acao === 'remover' && !confirm(msg + '\n\nAs demais permissões de cada usuário serão mantidas.')) {
        return;
    }

    if (acao === 'adicionar' && !confirm(msg + '\n\nAs permissões já existentes de cada usuário serão mantidas.')) {
        return;
    }

    const formData = new FormData();
    formData.append('acao', acao);
    usuariosSelecionados.forEach(function(id) {
        formData.append('usuarios[]', id);
    });
    permissoesSelecionadas.forEach(function(id) {
        formData.append('acessos[]', id);
    });

    $.ajax({
        url: '/seguranca/permissoes/api/gerenciar/lote/aplicar/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                $('.lote-usuario-cb, .lote-permissao-cb').prop('checked', false);
                atualizarResumoLote();
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao aplicar permissões em lote'));
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

