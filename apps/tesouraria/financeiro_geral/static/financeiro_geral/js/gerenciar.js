(function() {
    var base = (window.FINANCEIRO_GERAL_BASE || '').replace(/\/?$/, '') + '/';
    var urlCategorias = base + 'api/gerenciador/categorias/';
    var urlCategoriasCriar = base + 'api/gerenciador/categorias/criar/';
    var urlCategoriasEditar = base + 'api/gerenciador/categorias/editar/';
    var urlCategoriasDeletar = base + 'api/gerenciador/categorias/deletar/';
    var urlSubcategorias = base + 'api/gerenciador/subcategorias/';
    var urlSubcategoriasCriar = base + 'api/gerenciador/subcategorias/criar/';
    var urlSubcategoriasEditar = base + 'api/gerenciador/subcategorias/editar/';
    var urlSubcategoriasDeletar = base + 'api/gerenciador/subcategorias/deletar/';
    var urlTiposBeneficio = base + 'api/gerenciador/tipos-beneficio/';
    var urlTiposBeneficioCriar = base + 'api/gerenciador/tipos-beneficio/criar/';
    var urlTiposBeneficioEditar = base + 'api/gerenciador/tipos-beneficio/editar/';
    var urlTiposBeneficioDeletar = base + 'api/gerenciador/tipos-beneficio/deletar/';
    function carregarCategorias() {
        $.get(urlCategorias, { ativos: 'false' }).done(function(r) {
            var $tb = $('#tabela-categorias');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(c) {
                    $tb.append('<tr><td>' + (c.nome || '') + '</td><td>' + (c.status ? 'Ativo' : 'Inativo') + '</td><td><button type="button" class="btn btn-sm btn-outline-secondary" onclick="window.financeiroGeralGerenciar.editarCategoria(' + c.id + ', \'' + (c.nome || '').replace(/'/g, "\\'") + '\', ' + c.status + ')">Editar</button> <button type="button" class="btn btn-sm btn-outline-danger" onclick="window.financeiroGeralGerenciar.deletarCategoria(' + c.id + ')">Inativar</button></td></tr>');
                });
            }
            $('#subcategoria-categoria').find('option:not(:first)').remove();
            if (r.success && r.result) {
                r.result.filter(function(c) { return c.status; }).forEach(function(c) {
                    $('#subcategoria-categoria').append('<option value="' + c.id + '">' + (c.nome || '') + '</option>');
                });
            }
        });
    }
    function carregarSubcategorias() {
        $.get(urlSubcategorias, { ativos: 'false' }).done(function(r) {
            var $tb = $('#tabela-subcategorias');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(s) {
                    $tb.append('<tr><td>' + (s.categoria_nome || '') + '</td><td>' + (s.nome || '') + '</td><td>' + (s.status ? 'Ativo' : 'Inativo') + '</td><td><button type="button" class="btn btn-sm btn-outline-secondary" onclick="window.financeiroGeralGerenciar.editarSubcategoria(' + s.id + ', \'' + (s.nome || '').replace(/'/g, "\\'") + '\', ' + s.status + ')">Editar</button> <button type="button" class="btn btn-sm btn-outline-danger" onclick="window.financeiroGeralGerenciar.deletarSubcategoria(' + s.id + ')">Inativar</button></td></tr>');
                });
            }
        });
    }
    function carregarTiposBeneficio() {
        $.get(urlTiposBeneficio, { ativos: 'false' }).done(function(r) {
            var $tb = $('#tabela-tipos-beneficio');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(t) {
                    $tb.append('<tr><td>' + (t.nome || '') + '</td><td>' + (t.status ? 'Ativo' : 'Inativo') + '</td><td><button type="button" class="btn btn-sm btn-outline-secondary" onclick="window.financeiroGeralGerenciar.editarTipoBeneficio(' + t.id + ', \'' + (t.nome || '').replace(/'/g, "\\'") + '\', ' + t.status + ')">Editar</button> <button type="button" class="btn btn-sm btn-outline-danger" onclick="window.financeiroGeralGerenciar.deletarTipoBeneficio(' + t.id + ')">Inativar</button></td></tr>');
                });
            }
        });
    }
    function criarCategoria() {
        var nome = $('#nova-categoria-nome').val().trim();
        if (!nome) { alert('Nome é obrigatório.'); return; }
        $.ajax({ url: urlCategoriasCriar, type: 'POST', data: { nome: nome } }).done(function(r) {
            if (r.success) { $('#nova-categoria-nome').val(''); carregarCategorias(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro ao criar.'); });
    }
    function editarCategoria(id, nome, status) {
        var n = prompt('Nome:', nome);
        if (n === null) return;
        $.ajax({ url: urlCategoriasEditar, type: 'POST', data: { categoria_id: id, nome: n, status: status ? 'true' : 'false' } }).done(function(r) {
            if (r.success) carregarCategorias(); else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }
    function deletarCategoria(id) {
        if (!confirm('Inativar esta categoria?')) return;
        $.ajax({ url: urlCategoriasDeletar, type: 'POST', data: { categoria_id: id } }).done(function(r) {
            if (r.success) carregarCategorias(); else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }
    function criarSubcategoria() {
        var catId = $('#subcategoria-categoria').val();
        var nome = $('#nova-subcategoria-nome').val().trim();
        if (!catId) { alert('Selecione a categoria.'); return; }
        if (!nome) { alert('Nome é obrigatório.'); return; }
        $.ajax({ url: urlSubcategoriasCriar, type: 'POST', data: { categoria_id: catId, nome: nome } }).done(function(r) {
            if (r.success) { $('#nova-subcategoria-nome').val(''); carregarSubcategorias(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro ao criar.'); });
    }
    function editarSubcategoria(id, nome, status) {
        var n = prompt('Nome:', nome);
        if (n === null) return;
        $.ajax({ url: urlSubcategoriasEditar, type: 'POST', data: { subcategoria_id: id, nome: n, status: status ? 'true' : 'false' } }).done(function(r) {
            if (r.success) carregarSubcategorias(); else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }
    function deletarSubcategoria(id) {
        if (!confirm('Inativar esta subcategoria?')) return;
        $.ajax({ url: urlSubcategoriasDeletar, type: 'POST', data: { subcategoria_id: id } }).done(function(r) {
            if (r.success) carregarSubcategorias(); else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }
    function criarTipoBeneficio() {
        var nome = $('#nova-tipo-beneficio-nome').val().trim();
        if (!nome) { alert('Nome é obrigatório.'); return; }
        $.ajax({ url: urlTiposBeneficioCriar, type: 'POST', data: { nome: nome } }).done(function(r) {
            if (r.success) { $('#nova-tipo-beneficio-nome').val(''); carregarTiposBeneficio(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro ao criar.'); });
    }
    function editarTipoBeneficio(id, nome, status) {
        var n = prompt('Nome:', nome);
        if (n === null) return;
        $.ajax({ url: urlTiposBeneficioEditar, type: 'POST', data: { tipo_id: id, nome: n, status: status ? 'true' : 'false' } }).done(function(r) {
            if (r.success) carregarTiposBeneficio(); else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }
    function deletarTipoBeneficio(id) {
        if (!confirm('Inativar este tipo de benefício?')) return;
        $.ajax({ url: urlTiposBeneficioDeletar, type: 'POST', data: { tipo_id: id } }).done(function(r) {
            if (r.success) carregarTiposBeneficio(); else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }
    $(document).ready(function() {
        carregarCategorias();
        carregarSubcategorias();
        carregarTiposBeneficio();
        $('#btnCriarCategoria').on('click', criarCategoria);
        $('#btnCriarSubcategoria').on('click', criarSubcategoria);
        $('#btnCriarTipoBeneficio').on('click', criarTipoBeneficio);
    });
    window.financeiroGeralGerenciar = {
        editarCategoria: editarCategoria, deletarCategoria: deletarCategoria,
        editarSubcategoria: editarSubcategoria, deletarSubcategoria: deletarSubcategoria,
        editarTipoBeneficio: editarTipoBeneficio, deletarTipoBeneficio: deletarTipoBeneficio
    };
})();
