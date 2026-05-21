// Variáveis globais
let tipoAtual = '';
let idEditando = null;
let modalForm = null;

document.addEventListener('DOMContentLoaded', function() {
    modalForm = new bootstrap.Modal(document.getElementById('modalForm'));
    
    // Carregar dados ao trocar de tab
    const tabs = document.querySelectorAll('#adminTabs button[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function() {
            // Pode adicionar lógica de recarregamento se necessário
        });
    });
});

function abrirModalCriar(tipo) {
    tipoAtual = tipo;
    idEditando = null;
    
    const titulo = getTituloModal(tipo, false);
    document.getElementById('modalFormTitle').textContent = titulo;
    
    const formHTML = gerarFormHTML(tipo);
    document.getElementById('modalFormBody').innerHTML = formHTML;
    
    // Se for cargo, carregar níveis
    if (tipo === 'cargo') {
        setTimeout(() => carregarNiveisNoSelect(), 100);
    }
    
    modalForm.show();
}

function abrirModalEditar(tipo, id) {
    tipoAtual = tipo;
    idEditando = id;
    
    const titulo = getTituloModal(tipo, true);
    document.getElementById('modalFormTitle').textContent = titulo;
    
    // Carregar dados via AJAX
    carregarDadosParaEdicao(tipo, id);
}

function carregarDadosParaEdicao(tipo, id) {
    const url = getUrlAPI(tipo, 'editar', id);
    
    $.ajax({
        url: url,
        method: 'GET',
        success: function(data) {
            const formHTML = gerarFormHTML(tipo, data);
            document.getElementById('modalFormBody').innerHTML = formHTML;
            
            // Se for cargo, carregar níveis com o selecionado
            if (tipo === 'cargo') {
                setTimeout(() => carregarNiveisNoSelect(data.nivel_hierarquico_id), 100);
            }
            
            modalForm.show();
        },
        error: function() {
            alert('Erro ao carregar dados para edição');
        }
    });
}

function getTituloModal(tipo, editar) {
    const tipos = {
        'empresa': 'Empresa',
        'loja': 'Loja',
        'departamento': 'Departamento',
        'setor': 'Setor',
        'cargo': 'Cargo',
        'equipe': 'Equipe',
        'nivel': 'Nível Hierárquico'
    };
    return (editar ? 'Editar ' : 'Criar ') + tipos[tipo];
}

function gerarFormHTML(tipo, dados = null) {
    const isEdit = dados !== null;
    
    switch(tipo) {
        case 'empresa':
            return `
                <form id="formItem">
                    <div class="mb-3">
                        <label class="form-label">Nome *</label>
                        <input type="text" class="form-control" name="nome" value="${dados?.nome || ''}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">CNPJ</label>
                        <input type="text" class="form-control" name="cnpj" value="${dados?.cnpj || ''}" placeholder="00.000.000/0000-00">
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="flg_parceira" ${dados?.flg_parceira ? 'checked' : ''}>
                            <label class="form-check-label">Empresa Parceira</label>
                        </div>
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="status" ${dados?.status !== false ? 'checked' : ''}>
                            <label class="form-check-label">Ativo</label>
                        </div>
                    </div>
                </form>
            `;
            
        case 'loja':
            return `
                <form id="formItem" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label class="form-label">Nome *</label>
                        <input type="text" class="form-control" name="nome" value="${dados?.nome || ''}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Endereço</label>
                        <input type="text" class="form-control" name="endereco" value="${dados?.endereco || ''}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Logo</label>
                        <input type="file" class="form-control" name="logo" accept="image/*">
                        ${dados?.logo ? `<div class="mt-2"><img src="${dados.logo}" alt="Logo" style="max-width: 200px;"><br><small><a href="#" onclick="removerLogo()">Remover logo</a></small></div>` : ''}
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Tipo</label>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="flg_sede" ${dados?.flg_sede ? 'checked' : ''}>
                            <label class="form-check-label">Sede</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="flg_filial" ${dados?.flg_filial ? 'checked' : ''}>
                            <label class="form-check-label">Filial</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="flg_franquia" ${dados?.flg_franquia ? 'checked' : ''}>
                            <label class="form-check-label">Franquia</label>
                        </div>
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="status" ${dados?.status !== false ? 'checked' : ''}>
                            <label class="form-check-label">Ativo</label>
                        </div>
                    </div>
                </form>
            `;
            
        case 'departamento':
        case 'setor':
        case 'equipe':
            return `
                <form id="formItem">
                    <div class="mb-3">
                        <label class="form-label">Nome *</label>
                        <input type="text" class="form-control" name="nome" value="${dados?.nome || ''}" required>
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="status" ${dados?.status !== false ? 'checked' : ''}>
                            <label class="form-check-label">Ativo</label>
                        </div>
                    </div>
                </form>
            `;
            
        case 'cargo':
            return `
                <form id="formItem">
                    <div class="mb-3">
                        <label class="form-label">Nome *</label>
                        <input type="text" class="form-control" name="nome" value="${dados?.nome || ''}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Nível Hierárquico *</label>
                        <select class="form-control" name="nivel_hierarquico_id" id="select-nivel" required>
                            <option value="">Carregando...</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="status" ${dados?.status !== false ? 'checked' : ''}>
                            <label class="form-check-label">Ativo</label>
                        </div>
                    </div>
                </form>
            `;
            
        case 'nivel':
            return `
                <form id="formItem">
                    <div class="mb-3">
                        <label class="form-label">Nome *</label>
                        <input type="text" class="form-control" name="nome" value="${dados?.nome || ''}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Importância *</label>
                        <input type="number" class="form-control" name="importancia" value="${dados?.importancia || ''}" required min="0">
                        <small class="form-text text-muted">Valor numérico (0 = menor, maior valor = maior hierarquia)</small>
                    </div>
                    <div class="mb-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="status" ${dados?.status !== false ? 'checked' : ''}>
                            <label class="form-check-label">Ativo</label>
                        </div>
                    </div>
                </form>
            `;
            
        default:
            return '<p>Formulário não encontrado</p>';
    }
}

function carregarNiveisNoSelect(selecionado = null) {
    const select = document.getElementById('select-nivel');
    if (!select) return;
    
    $.ajax({
        url: '/rh/admin/api/niveis/listar/',
        method: 'GET',
        success: function(niveis) {
            let html = '<option value="">Selecione...</option>';
            niveis.forEach(nivel => {
                html += `<option value="${nivel.id}" ${nivel.id == selecionado ? 'selected' : ''}>${nivel.nome} (${nivel.importancia})</option>`;
            });
            select.innerHTML = html;
        },
        error: function() {
            select.innerHTML = '<option value="">Erro ao carregar níveis</option>';
        }
    });
}

function salvarForm() {
    const form = document.getElementById('formItem');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const formData = new FormData(form);
    const url = getUrlAPI(tipoAtual, idEditando ? 'editar' : 'criar', idEditando);
    
    $.ajax({
        url: url,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                alert(response.message);
                modalForm.hide();
                atualizarTabela(tipoAtual);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao salvar'));
        }
    });
}

function deletarItem(tipo, id, nome) {
    if (!confirm(`Tem certeza que deseja deletar "${nome}"?`)) {
        return;
    }
    
    const url = getUrlAPI(tipo, 'deletar', id);
    
    $.ajax({
        url: url,
        method: 'POST',
        success: function(response) {
            if (response.success) {
                alert(response.message);
                atualizarTabela(tipo);
            } else {
                alert('Erro: ' + response.message);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            alert('Erro: ' + (response.message || 'Erro ao deletar'));
        }
    });
}

function getUrlAPI(tipo, acao, id = null) {
    const baseUrl = '/rh/admin/api/';
    const tipos = {
        'empresa': 'empresas',
        'loja': 'lojas',
        'departamento': 'departamentos',
        'setor': 'setores',
        'cargo': 'cargos',
        'equipe': 'equipes',
        'nivel': 'niveis'
    };
    
    const tipoPlural = tipos[tipo];
    let url = baseUrl;
    
    if (acao === 'get') {
        url += 'get/' + tipoPlural + '/';
    } else {
        url += tipoPlural + '/';
        if (acao === 'criar') {
            url += 'criar/';
        } else if (acao === 'editar') {
            url += 'editar/' + id + '/';
        } else if (acao === 'deletar') {
            url += 'deletar/' + id + '/';
        }
    }
    
    return url;
}

function removerLogo() {
    // Adicionar checkbox oculto para remover logo
    const form = document.getElementById('formItem');
    if (!form.querySelector('input[name="remover_logo"]')) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'remover_logo';
        input.value = 'on';
        form.appendChild(input);
    }
    // Remover preview da imagem
    const imgPreview = form.querySelector('img');
    if (imgPreview) {
        imgPreview.parentElement.remove();
    }
}

function atualizarTabela(tipo) {
    const urlGet = getUrlAPI(tipo, 'get');
    const tbodyId = tipo + 's-tbody';
    
    $.ajax({
        url: urlGet,
        method: 'GET',
        success: function(dados) {
            const tbody = document.getElementById(tbodyId);
            if (!tbody) return;
            
            let html = '';
            if (dados.length === 0) {
                const colunas = getColunasCount(tipo);
                html = `<tr><td colspan="${colunas}" class="text-center">Nenhum registro cadastrado</td></tr>`;
            } else {
                dados.forEach(item => {
                    html += gerarLinhaTabela(tipo, item);
                });
            }
            
            tbody.innerHTML = html;
        },
        error: function() {
            console.error('Erro ao atualizar tabela:', tipo);
        }
    });
}

function getColunasCount(tipo) {
    const colunas = {
        'empresa': 6,
        'loja': 7,
        'departamento': 4,
        'setor': 4,
        'cargo': 5,
        'equipe': 4,
        'nivel': 5
    };
    return colunas[tipo] || 4;
}

function gerarLinhaTabela(tipo, item) {
    switch(tipo) {
        case 'empresa':
            return `
                <tr>
                    <td>${escapeHtml(item.nome)}</td>
                    <td>${item.cnpj || '-'}</td>
                    <td>${item.flg_parceira ? '<span class="badge bg-warning">Sim</span>' : '<span class="badge bg-secondary">Não</span>'}</td>
                    <td>${item.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                    <td>${item.data_criacao}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="abrirModalEditar('empresa', ${item.id})">
                            <i class='bx bx-edit'></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletarItem('empresa', ${item.id}, '${escapeHtml(item.nome)}')">
                            <i class='bx bx-trash'></i>
                        </button>
                    </td>
                </tr>
            `;
            
        case 'loja':
            const logoHtml = item.logo_url ? `<img src="${item.logo_url}" alt="${escapeHtml(item.nome)}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">` : '-';
            const tiposLoja = [];
            if (item.flg_sede) tiposLoja.push('<span class="badge bg-primary">Sede</span>');
            if (item.flg_filial) tiposLoja.push('<span class="badge bg-info">Filial</span>');
            if (item.flg_franquia) tiposLoja.push('<span class="badge bg-warning">Franquia</span>');
            
            return `
                <tr>
                    <td>${escapeHtml(item.nome)}</td>
                    <td>${logoHtml}</td>
                    <td>${tiposLoja.join(' ')}</td>
                    <td>${item.endereco || '-'}</td>
                    <td>${item.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                    <td>${item.data_criacao}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="abrirModalEditar('loja', ${item.id})">
                            <i class='bx bx-edit'></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletarItem('loja', ${item.id}, '${escapeHtml(item.nome)}')">
                            <i class='bx bx-trash'></i>
                        </button>
                    </td>
                </tr>
            `;
            
        case 'departamento':
        case 'setor':
        case 'equipe':
            return `
                <tr>
                    <td>${escapeHtml(item.nome)}</td>
                    <td>${item.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                    <td>${item.data_criacao}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="abrirModalEditar('${tipo}', ${item.id})">
                            <i class='bx bx-edit'></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletarItem('${tipo}', ${item.id}, '${escapeHtml(item.nome)}')">
                            <i class='bx bx-trash'></i>
                        </button>
                    </td>
                </tr>
            `;
            
        case 'cargo':
            return `
                <tr>
                    <td>${escapeHtml(item.nome)}</td>
                    <td>${escapeHtml(item.nivel_hierarquico_nome)} (${item.nivel_hierarquico_importancia})</td>
                    <td>${item.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                    <td>${item.data_criacao}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="abrirModalEditar('cargo', ${item.id})">
                            <i class='bx bx-edit'></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletarItem('cargo', ${item.id}, '${escapeHtml(item.nome)}')">
                            <i class='bx bx-trash'></i>
                        </button>
                    </td>
                </tr>
            `;
            
        case 'nivel':
            return `
                <tr>
                    <td>${escapeHtml(item.nome)}</td>
                    <td><span class="badge bg-primary">${item.importancia}</span></td>
                    <td>${item.status ? '<span class="badge bg-success">Ativo</span>' : '<span class="badge bg-danger">Inativo</span>'}</td>
                    <td>${item.data_criacao}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="abrirModalEditar('nivel', ${item.id})">
                            <i class='bx bx-edit'></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletarItem('nivel', ${item.id}, '${escapeHtml(item.nome)}')">
                            <i class='bx bx-trash'></i>
                        </button>
                    </td>
                </tr>
            `;
            
        default:
            return '';
    }
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

