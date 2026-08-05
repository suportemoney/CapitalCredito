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

    function badgeStatus(ativo) {
        if (ativo) {
            return $('<span class="badge-status badge-status-ativo"></span>').html('<i class="bx bx-check-circle"></i> Ativo');
        }
        return $('<span class="badge-status badge-status-inativo"></span>').html('<i class="bx bx-minus-circle"></i> Inativo');
    }

    function linhaVazia(colspan, msg) {
        return $('<tr class="linha-vazia"></tr>').append(
            $('<td></td>').attr('colspan', colspan).html('<i class="bx bx-info-circle"></i> ' + (msg || 'Nenhum registro encontrado.'))
        );
    }

    function linhaLoading(colspan) {
        return $('<tr class="linha-loading"></tr>').append(
            $('<td></td>').attr('colspan', colspan).html('<i class="bx bx-loader-alt bx-spin"></i> Carregando...')
        );
    }

    function btnAcao(classe, texto, icone) {
        return $('<button type="button" class="btn btn-sm"></button>')
            .addClass(classe)
            .html('<i class="bx ' + icone + '"></i> ' + texto);
    }

    function atualizarSelectCategoriasAtivas(lista) {
        var $sel = $('#subcategoria-categoria');
        var atual = $sel.val();
        $sel.find('option:not(:first)').remove();
        (lista || []).filter(function(c) { return c.status; }).forEach(function(c) {
            $sel.append($('<option></option>').val(c.id).text(c.nome || ''));
        });
        if (atual) $sel.val(atual);
    }

    function carregarCategorias() {
        var $tb = $('#tabela-categorias');
        $tb.empty().append(linhaLoading(3));
        $.get(urlCategorias, { ativos: 'false' }).done(function(r) {
            $tb.empty();
            if (!r.success || !r.result || !r.result.length) {
                $tb.append(linhaVazia(3));
                atualizarSelectCategoriasAtivas([]);
                return;
            }
            r.result.forEach(function(c) {
                var $tr = $('<tr></tr>');
                $tr.append($('<td></td>').text(c.nome || ''));
                $tr.append($('<td></td>').append(badgeStatus(!!c.status)));
                var $acoes = $('<td></td>').append($('<span class="td-acoes"></span>'));
                var $span = $acoes.find('.td-acoes');
                $span.append(
                    btnAcao('btn-outline-secondary btn-editar-cat', 'Editar', 'bx-edit')
                        .attr('data-id', c.id)
                        .attr('data-nome', c.nome || '')
                        .attr('data-status', c.status ? 'true' : 'false')
                );
                if (c.status) {
                    $span.append(
                        btnAcao('btn-outline-danger btn-inativar-cat', 'Inativar', 'bx-trash')
                            .attr('data-id', c.id)
                    );
                } else {
                    $span.append(
                        btnAcao('btn-outline-success btn-reativar-cat', 'Reativar', 'bx-refresh')
                            .attr('data-id', c.id)
                            .attr('data-nome', c.nome || '')
                    );
                }
                $tr.append($acoes);
                $tb.append($tr);
            });
            atualizarSelectCategoriasAtivas(r.result);
        }).fail(function() {
            $tb.empty().append(linhaVazia(3, 'Erro ao carregar categorias.'));
        });
    }

    function carregarSubcategorias() {
        var $tb = $('#tabela-subcategorias');
        $tb.empty().append(linhaLoading(4));
        $.get(urlSubcategorias, { ativos: 'false' }).done(function(r) {
            $tb.empty();
            if (!r.success || !r.result || !r.result.length) {
                $tb.append(linhaVazia(4));
                return;
            }
            r.result.forEach(function(s) {
                var $tr = $('<tr></tr>');
                $tr.append($('<td></td>').text(s.categoria_nome || ''));
                $tr.append($('<td></td>').text(s.nome || ''));
                $tr.append($('<td></td>').append(badgeStatus(!!s.status)));
                var $acoes = $('<td></td>').append($('<span class="td-acoes"></span>'));
                var $span = $acoes.find('.td-acoes');
                $span.append(
                    btnAcao('btn-outline-secondary btn-editar-sub', 'Editar', 'bx-edit')
                        .attr('data-id', s.id)
                        .attr('data-nome', s.nome || '')
                        .attr('data-status', s.status ? 'true' : 'false')
                );
                if (s.status) {
                    $span.append(
                        btnAcao('btn-outline-danger btn-inativar-sub', 'Inativar', 'bx-trash')
                            .attr('data-id', s.id)
                    );
                } else {
                    $span.append(
                        btnAcao('btn-outline-success btn-reativar-sub', 'Reativar', 'bx-refresh')
                            .attr('data-id', s.id)
                            .attr('data-nome', s.nome || '')
                    );
                }
                $tr.append($acoes);
                $tb.append($tr);
            });
        }).fail(function() {
            $tb.empty().append(linhaVazia(4, 'Erro ao carregar subcategorias.'));
        });
    }

    function carregarTiposBeneficio() {
        var $tb = $('#tabela-tipos-beneficio');
        $tb.empty().append(linhaLoading(3));
        $.get(urlTiposBeneficio, { ativos: 'false' }).done(function(r) {
            $tb.empty();
            if (!r.success || !r.result || !r.result.length) {
                $tb.append(linhaVazia(3));
                return;
            }
            r.result.forEach(function(t) {
                var $tr = $('<tr></tr>');
                $tr.append($('<td></td>').text(t.nome || ''));
                $tr.append($('<td></td>').append(badgeStatus(!!t.status)));
                var $acoes = $('<td></td>').append($('<span class="td-acoes"></span>'));
                var $span = $acoes.find('.td-acoes');
                $span.append(
                    btnAcao('btn-outline-secondary btn-editar-tipo', 'Editar', 'bx-edit')
                        .attr('data-id', t.id)
                        .attr('data-nome', t.nome || '')
                        .attr('data-status', t.status ? 'true' : 'false')
                );
                if (t.status) {
                    $span.append(
                        btnAcao('btn-outline-danger btn-inativar-tipo', 'Inativar', 'bx-trash')
                            .attr('data-id', t.id)
                    );
                } else {
                    $span.append(
                        btnAcao('btn-outline-success btn-reativar-tipo', 'Reativar', 'bx-refresh')
                            .attr('data-id', t.id)
                            .attr('data-nome', t.nome || '')
                    );
                }
                $tr.append($acoes);
                $tb.append($tr);
            });
        }).fail(function() {
            $tb.empty().append(linhaVazia(3, 'Erro ao carregar tipos de benefício.'));
        });
    }

    function abrirModalEdicao(tipo, id, nome, status) {
        $('#edit-tipo-entidade').val(tipo);
        $('#edit-entidade-id').val(id);
        $('#edit-nome').val(nome || '');
        $('#edit-status').val(status ? 'true' : 'false');
        var titulos = { categoria: 'Editar categoria', subcategoria: 'Editar subcategoria', tipo: 'Editar tipo de benefício' };
        $('#modalEditarGerenciadorTitulo').html('<i class="bx bx-edit"></i> ' + (titulos[tipo] || 'Editar'));
        new bootstrap.Modal(document.getElementById('modalEditarGerenciador')).show();
    }

    function salvarEdicaoModal() {
        var tipo = $('#edit-tipo-entidade').val();
        var id = $('#edit-entidade-id').val();
        var nome = $('#edit-nome').val().trim();
        var status = $('#edit-status').val();
        if (!nome) { alert('Nome é obrigatório.'); return; }
        var $btn = $('#btnSalvarEdicaoGerenciador').prop('disabled', true);
        var url, data, reload;
        if (tipo === 'categoria') {
            url = urlCategoriasEditar;
            data = { categoria_id: id, nome: nome, status: status };
            reload = function() { carregarCategorias(); carregarSubcategorias(); };
        } else if (tipo === 'subcategoria') {
            url = urlSubcategoriasEditar;
            data = { subcategoria_id: id, nome: nome, status: status };
            reload = carregarSubcategorias;
        } else {
            url = urlTiposBeneficioEditar;
            data = { tipo_id: id, nome: nome, status: status };
            reload = carregarTiposBeneficio;
        }
        $.ajax({ url: url, type: 'POST', data: data }).done(function(r) {
            if (r.success) {
                bootstrap.Modal.getInstance(document.getElementById('modalEditarGerenciador')).hide();
                reload();
            } else {
                alert(r.message || 'Erro ao salvar.');
            }
        }).fail(function() {
            alert('Erro ao salvar.');
        }).always(function() {
            $btn.prop('disabled', false);
        });
    }

    function criarCategoria() {
        var nome = $('#nova-categoria-nome').val().trim();
        if (!nome) { alert('Nome é obrigatório.'); return; }
        var $btn = $('#btnCriarCategoria').prop('disabled', true);
        $.ajax({ url: urlCategoriasCriar, type: 'POST', data: { nome: nome } }).done(function(r) {
            if (r.success) {
                $('#nova-categoria-nome').val('');
                carregarCategorias();
            } else {
                alert(r.message || 'Erro.');
            }
        }).fail(function() {
            alert('Erro ao criar.');
        }).always(function() {
            $btn.prop('disabled', false);
        });
    }

    function criarSubcategoria() {
        var catId = $('#subcategoria-categoria').val();
        var nome = $('#nova-subcategoria-nome').val().trim();
        if (!catId) { alert('Selecione a categoria.'); return; }
        if (!nome) { alert('Nome é obrigatório.'); return; }
        var $btn = $('#btnCriarSubcategoria').prop('disabled', true);
        $.ajax({ url: urlSubcategoriasCriar, type: 'POST', data: { categoria_id: catId, nome: nome } }).done(function(r) {
            if (r.success) {
                $('#nova-subcategoria-nome').val('');
                carregarSubcategorias();
            } else {
                alert(r.message || 'Erro.');
            }
        }).fail(function() {
            alert('Erro ao criar.');
        }).always(function() {
            $btn.prop('disabled', false);
        });
    }

    function criarTipoBeneficio() {
        var nome = $('#nova-tipo-beneficio-nome').val().trim();
        if (!nome) { alert('Nome é obrigatório.'); return; }
        var $btn = $('#btnCriarTipoBeneficio').prop('disabled', true);
        $.ajax({ url: urlTiposBeneficioCriar, type: 'POST', data: { nome: nome } }).done(function(r) {
            if (r.success) {
                $('#nova-tipo-beneficio-nome').val('');
                carregarTiposBeneficio();
            } else {
                alert(r.message || 'Erro.');
            }
        }).fail(function() {
            alert('Erro ao criar.');
        }).always(function() {
            $btn.prop('disabled', false);
        });
    }

    function inativarCategoria(id) {
        if (!confirm('Inativar esta categoria? As subcategorias vinculadas também serão inativadas.')) return;
        $.ajax({ url: urlCategoriasDeletar, type: 'POST', data: { categoria_id: id } }).done(function(r) {
            if (r.success) {
                carregarCategorias();
                carregarSubcategorias();
            } else {
                alert(r.message || 'Erro.');
            }
        }).fail(function() { alert('Erro.'); });
    }

    function reativarCategoria(id, nome) {
        $.ajax({
            url: urlCategoriasEditar,
            type: 'POST',
            data: { categoria_id: id, nome: nome || '', status: 'true' }
        }).done(function(r) {
            if (r.success) carregarCategorias();
            else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }

    function inativarSubcategoria(id) {
        if (!confirm('Inativar esta subcategoria?')) return;
        $.ajax({ url: urlSubcategoriasDeletar, type: 'POST', data: { subcategoria_id: id } }).done(function(r) {
            if (r.success) carregarSubcategorias();
            else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }

    function reativarSubcategoria(id, nome) {
        $.ajax({
            url: urlSubcategoriasEditar,
            type: 'POST',
            data: { subcategoria_id: id, nome: nome || '', status: 'true' }
        }).done(function(r) {
            if (r.success) carregarSubcategorias();
            else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }

    function inativarTipo(id) {
        if (!confirm('Inativar este tipo de benefício?')) return;
        $.ajax({ url: urlTiposBeneficioDeletar, type: 'POST', data: { tipo_id: id } }).done(function(r) {
            if (r.success) carregarTiposBeneficio();
            else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }

    function reativarTipo(id, nome) {
        $.ajax({
            url: urlTiposBeneficioEditar,
            type: 'POST',
            data: { tipo_id: id, nome: nome || '', status: 'true' }
        }).done(function(r) {
            if (r.success) carregarTiposBeneficio();
            else alert(r.message || 'Erro.');
        }).fail(function() { alert('Erro.'); });
    }

    $(document).ready(function() {
        carregarCategorias();
        carregarSubcategorias();
        carregarTiposBeneficio();

        $('#btnCriarCategoria').on('click', criarCategoria);
        $('#btnCriarSubcategoria').on('click', criarSubcategoria);
        $('#btnCriarTipoBeneficio').on('click', criarTipoBeneficio);
        $('#btnSalvarEdicaoGerenciador').on('click', salvarEdicaoModal);

        $('#nova-categoria-nome').on('keydown', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); criarCategoria(); }
        });
        $('#nova-subcategoria-nome').on('keydown', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); criarSubcategoria(); }
        });
        $('#nova-tipo-beneficio-nome').on('keydown', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); criarTipoBeneficio(); }
        });

        $(document).on('click', '.btn-editar-cat', function() {
            var $b = $(this);
            abrirModalEdicao('categoria', $b.data('id'), $b.attr('data-nome'), $b.data('status') === true || $b.attr('data-status') === 'true');
        });
        $(document).on('click', '.btn-inativar-cat', function() {
            inativarCategoria($(this).data('id'));
        });
        $(document).on('click', '.btn-reativar-cat', function() {
            reativarCategoria($(this).data('id'), $(this).attr('data-nome'));
        });

        $(document).on('click', '.btn-editar-sub', function() {
            var $b = $(this);
            abrirModalEdicao('subcategoria', $b.data('id'), $b.attr('data-nome'), $b.data('status') === true || $b.attr('data-status') === 'true');
        });
        $(document).on('click', '.btn-inativar-sub', function() {
            inativarSubcategoria($(this).data('id'));
        });
        $(document).on('click', '.btn-reativar-sub', function() {
            reativarSubcategoria($(this).data('id'), $(this).attr('data-nome'));
        });

        $(document).on('click', '.btn-editar-tipo', function() {
            var $b = $(this);
            abrirModalEdicao('tipo', $b.data('id'), $b.attr('data-nome'), $b.data('status') === true || $b.attr('data-status') === 'true');
        });
        $(document).on('click', '.btn-inativar-tipo', function() {
            inativarTipo($(this).data('id'));
        });
        $(document).on('click', '.btn-reativar-tipo', function() {
            reativarTipo($(this).data('id'), $(this).attr('data-nome'));
        });
    });
})();
