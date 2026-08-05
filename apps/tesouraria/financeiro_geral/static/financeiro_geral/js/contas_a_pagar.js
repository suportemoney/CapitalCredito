(function() {
    var base = (window.FINANCEIRO_GERAL_BASE || '').replace(/\/?$/, '') + '/';
    var urlListar = base + 'api/contas-pagar/listar/';
    var urlCriar = base + 'api/contas-pagar/criar/';
    var urlMarcarPago = base + 'api/contas-pagar/marcar-pago/';
    var urlEditar = base + 'api/contas-pagar/editar/';
    var urlDeletar = base + 'api/contas-pagar/deletar/';
    var urlSubcategorias = base + 'api/gerenciador/subcategorias/';
    var urlBonifListar = base + 'api/bonificacoes-pagar/listar/';
    var urlBonifCriar = base + 'api/bonificacoes-pagar/criar/';
    var urlBonifPagarAgora = base + 'api/bonificacoes-pagar/pagar-agora/';
    var urlBonifEditar = base + 'api/bonificacoes-pagar/editar/';
    var urlBonifInativar = base + 'api/bonificacoes-pagar/inativar/';
    var urlBonifComprovanteDownload = base + 'api/bonificacoes-pagar/comprovante-download/';
    var contaIdPago = null;
    var tipoAtual = 'CONTA';
    var filtroIdFromUrl = null;

    var EXTENSOES_PERMITIDAS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'];
    var TAMANHO_MAX_MB = 10;

    function formatarMoeda(v) {
        return 'R$ ' + (typeof v === 'number' ? v.toFixed(2) : parseFloat(v || 0).toFixed(2)).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
    function dataHoje() {
        var d = new Date();
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }
    function badgeStatus(pago) {
        if (pago) {
            return '<span class="badge-status badge-status-pago"><i class="bx bx-check-circle"></i> Pago</span>';
        }
        return '<span class="badge-status badge-status-pendente"><i class="bx bx-error-circle"></i> Pendente</span>';
    }
    function celulaArquivo(hasArquivo, url, titulo, iconePadrao) {
        if (hasArquivo && url) {
            var isPdf = (url || '').toLowerCase().indexOf('.pdf') !== -1;
            var icone = isPdf ? 'bxs-file-pdf' : (iconePadrao || 'bxs-file-image');
            return '<a href="' + url + '" target="_blank" rel="noopener" class="link-comprovante" title="' + titulo + '"><i class="bx ' + icone + '"></i></a>';
        }
        return '<span class="sem-comprovante">—</span>';
    }
    function celulaAnexo(item) {
        return celulaArquivo(item.has_anexo, item.anexo_url, 'Ver anexo', 'bx-paperclip');
    }
    function celulaComprovante(item) {
        return celulaArquivo(item.has_comprovante, item.comprovante_url, 'Ver comprovante de pagamento', 'bx-receipt');
    }
    function validarArquivo(file) {
        if (!file) return null;
        var nome = (file.name || '').toLowerCase();
        var ext = nome.split('.').pop();
        if (EXTENSOES_PERMITIDAS.indexOf(ext) === -1) {
            return 'Arquivo não permitido. Use imagem (JPG, PNG, GIF, WEBP) ou PDF.';
        }
        if (file.size > TAMANHO_MAX_MB * 1024 * 1024) {
            return 'Arquivo não pode exceder ' + TAMANHO_MAX_MB + ' MB.';
        }
        return null;
    }
    function atualizarPreviewArquivo(inputId, previewId, nomeId) {
        var input = document.getElementById(inputId);
        var preview = document.getElementById(previewId);
        var nomeEl = document.getElementById(nomeId);
        if (!input || !preview) return;
        if (input.files && input.files[0]) {
            var erro = validarArquivo(input.files[0]);
            if (erro) {
                alert(erro);
                input.value = '';
                preview.classList.remove('visivel');
                return;
            }
            var file = input.files[0];
            var isPdf = (file.name || '').toLowerCase().endsWith('.pdf');
            var icone = preview.querySelector('.preview-icon i');
            if (icone) icone.className = 'bx ' + (isPdf ? 'bxs-file-pdf' : 'bxs-file-image');
            if (nomeEl) nomeEl.textContent = file.name;
            preview.classList.add('visivel');
        } else {
            preview.classList.remove('visivel');
            if (nomeEl) nomeEl.textContent = '';
        }
    }
    function limparPreviewArquivo(inputId, previewId, nomeId) {
        var input = document.getElementById(inputId);
        if (input) input.value = '';
        var preview = document.getElementById(previewId);
        if (preview) preview.classList.remove('visivel');
        var nomeEl = document.getElementById(nomeId);
        if (nomeEl) nomeEl.textContent = '';
    }
    function initUploadArea(areaId, inputId, previewId, nomeId) {
        var area = document.getElementById(areaId);
        var input = document.getElementById(inputId);
        if (!area || !input) return;
        input.addEventListener('change', function() {
            atualizarPreviewArquivo(inputId, previewId, nomeId);
        });
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            area.classList.add('dragover');
        });
        area.addEventListener('dragleave', function() {
            area.classList.remove('dragover');
        });
        area.addEventListener('drop', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                input.files = e.dataTransfer.files;
                atualizarPreviewArquivo(inputId, previewId, nomeId);
            }
        });
    }
    function paramsFiltros(tipo) {
        var $filtros = $('.filtros-contas-pagar[data-tipo="' + tipo + '"]');
        var p = { tipo: tipo };
        if (!$filtros.length) return p;
        var desc = $filtros.find('.filtro-descricao').val();
        if (desc) p.descricao = desc;
        var cat = $filtros.find('.filtro-categoria').val();
        if (cat) p.categoria_id = cat;
        var sub = $filtros.find('.filtro-subcategoria').val();
        if (sub) p.subcategoria_id = sub;
        var vmin = $filtros.find('.filtro-valor-min').val();
        if (vmin) p.valor_min = vmin.replace(',', '.');
        var vmax = $filtros.find('.filtro-valor-max').val();
        if (vmax) p.valor_max = vmax.replace(',', '.');
        var vde = $filtros.find('.filtro-venc-de').val();
        if (vde) p.data_vencimento_de = vde;
        var vate = $filtros.find('.filtro-venc-ate').val();
        if (vate) p.data_vencimento_ate = vate;
        var st = $filtros.find('.filtro-status').val();
        if (st) p.status = st;
        var func = $filtros.find('.filtro-funcionario').val();
        if (func) p.funcionario_id = func;
        var tben = $filtros.find('.filtro-tipo-beneficio').val();
        if (tben) p.tipo_beneficio_id = tben;
        if (filtroIdFromUrl) {
            p.id = filtroIdFromUrl;
            filtroIdFromUrl = null;
        }
        return p;
    }
    function carregarSubcategoriasFiltro(categoriaId) {
        var $sub = $('#tab-conta .filtro-subcategoria');
        $sub.html('<option value="">Todas</option>');
        if (!categoriaId) return;
        $.get(urlSubcategorias, { categoria_id: categoriaId, ativos: 'true' }).done(function(r) {
            if (r.success && r.result) {
                r.result.forEach(function(s) {
                    $sub.append('<option value="' + s.id + '">' + (s.nome || '') + '</option>');
                });
            }
        });
    }
    function paramsFiltrosBonificacoes() {
        var p = {};
        var func = $('.filtros-bonificacoes .filtro-bonif-funcionario').val();
        if (func) p.funcionario_id = func;
        var mes = $('.filtros-bonificacoes .filtro-bonif-mes').val();
        if (mes) p.mes_referente = mes;
        var dataDe = $('.filtros-bonificacoes .filtro-bonif-data-de').val();
        if (dataDe) p.data_pagamento_de = dataDe;
        var dataAte = $('.filtros-bonificacoes .filtro-bonif-data-ate').val();
        if (dataAte) p.data_pagamento_ate = dataAte;
        var vmin = $('.filtros-bonificacoes .filtro-bonif-valor-min').val();
        if (vmin) p.valor_min = vmin.replace(',', '.');
        var vmax = $('.filtros-bonificacoes .filtro-bonif-valor-max').val();
        if (vmax) p.valor_max = vmax.replace(',', '.');
        var st = $('.filtros-bonificacoes .filtro-bonif-status').val();
        if (st) p.status = st;
        return p;
    }
    function linhaVazia(colspan) {
        return '<tr class="tabela-vazia"><td colspan="' + colspan + '"><i class="bx bx-info-circle"></i> Nenhum registro encontrado.</td></tr>';
    }
    function carregarTabelaBonificacoes() {
        $('#tabela-bonificacao').empty();
        var params = paramsFiltrosBonificacoes();
        $.get(urlBonifListar, params).done(function(r) {
            if (!r.success || !r.result) return;
            if (!r.result.length) {
                $('#tabela-bonificacao').append(linhaVazia(8));
                return;
            }
            r.result.forEach(function(b) {
                var statusPag = b.status_pagamento ? badgeStatus(true) : badgeStatus(false);
                var chavePixEsc = (b.chave_pix || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                var btnPagar = b.status_pagamento ? '' : '<button type="button" class="btn btn-sm btn-primary btn-acao-pagar me-1" onclick="window.financeiroGeralContasPagar.abrirModalBonifPagarAgora(' + b.id + ', \'' + (b.funcionario_nome || '').replace(/'/g, "\\'") + '\', ' + b.valor_bonificacao + ', \'' + (b.mes_referente || '').replace(/'/g, "\\'") + '\', \'' + chavePixEsc + '\')"><i class="bx bx-money"></i> Pagar Agora</button>';
                var btnEditar = '<button type="button" class="btn btn-sm btn-outline-secondary btn-acao-editar me-1" onclick="window.financeiroGeralContasPagar.abrirModalEditarBonif(' + b.id + ')"><i class="bx bx-edit"></i> Editar</button>';
                var btnInativar = '<button type="button" class="btn btn-sm btn-outline-danger" onclick="window.financeiroGeralContasPagar.inativarBonif(' + b.id + ')"><i class="bx bx-trash"></i> Inativar</button>';
                var acoes = '<span class="d-flex flex-wrap gap-1 td-acoes">' + btnPagar + btnEditar + btnInativar + '</span>';
                var urlDownload = urlBonifComprovanteDownload + '?id=' + encodeURIComponent(b.id);
                var comprovanteCell = b.has_comprovante ? '<a href="' + urlDownload + '" download class="link-comprovante" title="Baixar comprovante"><i class="bx bx-download"></i></a>' : '<span class="sem-comprovante">—</span>';
                var chavePixCell = (b.chave_pix || '-');
                var dataPag = b.data_pagamento || '-';
                var linha = '<tr><td>' + (b.funcionario_nome || '-') + '</td><td class="td-valor">' + formatarMoeda(b.valor_bonificacao) + '</td><td>' + (b.mes_referente || '-') + '</td><td>' + dataPag + '</td><td>' + statusPag + '</td><td>' + chavePixCell + '</td><td>' + comprovanteCell + '</td><td>' + acoes + '</td></tr>';
                $('#tabela-bonificacao').append(linha);
            });
        });
    }
    function carregarTabela(tipo) {
        tipoAtual = tipo;
        var $tbody = tipo === 'CONTA' ? $('#tabela-conta') : (tipo === 'SALARIO' ? $('#tabela-salario') : $('#tabela-beneficio'));
        var colspan = tipo === 'CONTA' ? 9 : 8;
        $tbody.empty();
        var params = paramsFiltros(tipo);
        $.get(urlListar, params).done(function(r) {
            if (!r.success || !r.result) return;
            if (!r.result.length) {
                $tbody.append(linhaVazia(colspan));
                return;
            }
            r.result.forEach(function(c) {
                var status = badgeStatus(c.pago);
                var podeEditar = !c.pago || (window.IS_SUPERUSER === true);
                var podeExcluir = window.HAS_PERM_DELET === true;
                var btnEditar = podeEditar ? '<button type="button" class="btn btn-sm btn-outline-secondary btn-acao-editar me-1" onclick="window.financeiroGeralContasPagar.abrirModalEditar(' + c.id + ', \'' + tipo + '\')"><i class="bx bx-edit"></i> Editar</button>' : '';
                var btnPagar = c.pago ? '' : '<button type="button" class="btn btn-sm btn-primary btn-acao-pagar me-1" onclick="window.financeiroGeralContasPagar.abrirModalPago(' + c.id + ', \'' + (c.descricao || '').replace(/'/g, "\\'") + '\', ' + c.valor + ', \'' + c.data_vencimento + '\')"><i class="bx bx-money"></i> Pagar</button>';
                var btnExcluir = podeExcluir ? '<button type="button" class="btn btn-sm btn-outline-danger btn-acao-excluir" onclick="window.financeiroGeralContasPagar.excluirConta(' + c.id + ', \'' + tipo + '\')" title="Excluir"><i class="bx bx-trash"></i></button>' : '';
                var acoes = '<span class="d-flex flex-wrap gap-1 td-acoes">' + btnEditar + btnPagar + btnExcluir + '</span>';
                var anexoCell = celulaAnexo(c);
                var comprovanteCell = celulaComprovante(c);
                var linha = '';
                if (tipo === 'CONTA') {
                    linha = '<tr><td>' + (c.descricao || '') + '</td><td>' + (c.categoria_nome || '-') + '</td><td>' + (c.subcategoria_nome || '-') + '</td><td class="td-valor">' + formatarMoeda(c.valor) + '</td><td>' + c.data_vencimento + '</td><td>' + status + '</td><td>' + anexoCell + '</td><td>' + comprovanteCell + '</td><td>' + acoes + '</td></tr>';
                } else if (tipo === 'SALARIO') {
                    linha = '<tr><td>' + (c.descricao || '') + '</td><td>' + (c.funcionario_nome || '-') + '</td><td class="td-valor">' + formatarMoeda(c.valor) + '</td><td>' + c.data_vencimento + '</td><td>' + status + '</td><td>' + anexoCell + '</td><td>' + comprovanteCell + '</td><td>' + acoes + '</td></tr>';
                } else {
                    linha = '<tr><td>' + (c.descricao || '') + '</td><td>' + (c.funcionario_nome || '-') + '</td><td>' + (c.tipo_beneficio_nome || '-') + '</td><td class="td-valor">' + formatarMoeda(c.valor) + '</td><td>' + c.data_vencimento + '</td><td>' + status + '</td><td>' + anexoCell + '</td><td>' + comprovanteCell + '</td><td>' + acoes + '</td></tr>';
                }
                $tbody.append(linha);
            });
        });
    }
    function abrirModalPago(id, descricao, valor, vencimento) {
        contaIdPago = id;
        $('#modalPagoDados').html('<p><strong>' + (descricao || '') + '</strong><br>Valor: ' + formatarMoeda(valor) + '<br>Vencimento: ' + (vencimento || '') + '</p>');
        $('#modalPagoData').val(dataHoje());
        limparPreviewArquivo('modalPagoComprovante', 'preview-pago', 'preview-pago-nome');
        new bootstrap.Modal(document.getElementById('modalConfirmarPago')).show();
    }
    function confirmarPago() {
        if (!contaIdPago) return;
        var dataPag = $('#modalPagoData').val() || dataHoje();
        var formData = new FormData();
        formData.append('tipo', tipoAtual);
        formData.append('conta_id', contaIdPago);
        formData.append('data_pagamento', dataPag);
        var fileInput = document.getElementById('modalPagoComprovante');
        if (fileInput.files && fileInput.files[0]) {
            var erro = validarArquivo(fileInput.files[0]);
            if (erro) { alert(erro); return; }
            formData.append('comprovante', fileInput.files[0]);
        }
        $.ajax({ url: urlMarcarPago, type: 'POST', data: formData, processData: false, contentType: false }).done(function(r) {
            if (r.success) {
                bootstrap.Modal.getInstance(document.getElementById('modalConfirmarPago')).hide();
                carregarTabela(tipoAtual);
            } else {
                alert(r.message || 'Erro ao marcar como pago.');
            }
        }).fail(function() { alert('Erro ao marcar como pago.'); });
    }
    function abrirModalEditar(contaId, tipo) {
        $('#editar-conta-id').val(contaId);
        $('#nova-conta-tipo').val(tipo);
        $('#nova-conta-tipo-select').val(tipo);
        $('#nova-conta-row-tipo').hide();
        $('#nova-anexo-row').hide();
        $('#editar-anexo-row').show();
        limparPreviewArquivo('editar-anexo', 'preview-editar-anexo', 'preview-editar-anexo-nome');
        limparPreviewArquivo('editar-comprovante', 'preview-editar-comprovante', 'preview-editar-comprovante-nome');
        if (window.IS_SUPERUSER === true) $('#editar-comprovante-row').show(); else $('#editar-comprovante-row').hide();
        toggleCamposNovaConta();
        var titulosEditar = { 'CONTA': 'Editar conta (empresa)', 'SALARIO': 'Editar salário', 'BENEFICIO': 'Editar benefício' };
        $('#modalNovaContaTitulo').html('<i class="bx bx-edit"></i> ' + (titulosEditar[tipo] || 'Editar'));
        var params = paramsFiltros(tipo);
        params.id = contaId;
        $.get(urlListar, params).done(function(r) {
            if (!r.success || !r.result || !r.result.length) { alert('Registro não encontrado.'); return; }
            var c = r.result[0];
            $('#nova-descricao').val(c.descricao || '');
            $('#nova-valor').val(typeof c.valor === 'number' ? c.valor.toFixed(2).replace('.', ',') : String(c.valor || '').replace('.', ','));
            $('#nova-data-vencimento').val(c.data_vencimento || '');
            $('#nova-observacao').val(c.observacao || '');
            if (tipo === 'CONTA') {
                $('#nova-categoria').val(c.categoria_id || '');
                var $sub = $('#nova-subcategoria');
                $sub.html('<option value="">Selecione...</option>');
                if (c.categoria_id) {
                    $.get(urlSubcategorias, { categoria_id: c.categoria_id, ativos: 'true' }).done(function(sr) {
                        if (sr.success && sr.result) { sr.result.forEach(function(s) { $sub.append('<option value="' + s.id + '">' + (s.nome || '') + '</option>'); }); }
                        $sub.val(c.subcategoria_id || '');
                        new bootstrap.Modal(document.getElementById('modalNovaConta')).show();
                    });
                } else {
                    new bootstrap.Modal(document.getElementById('modalNovaConta')).show();
                }
            } else {
                $('#nova-funcionario').val(c.funcionario_id || '');
                if (tipo === 'BENEFICIO') $('#nova-tipo-beneficio').val(c.tipo_beneficio_id || '');
                new bootstrap.Modal(document.getElementById('modalNovaConta')).show();
            }
        }).fail(function() { alert('Erro ao carregar dados.'); });
    }
    function salvarEdicao() {
        var tipo = $('#nova-conta-tipo-select').val();
        var contaId = $('#editar-conta-id').val();
        if (!contaId) return;
        var descricao = $('#nova-descricao').val().trim();
        var valor = $('#nova-valor').val().replace(',', '.').trim();
        var dataVenc = $('#nova-data-vencimento').val();
        var obs = $('#nova-observacao').val().trim() || '';
        if (!descricao) { alert('Informe a descrição.'); return; }
        if (!valor || isNaN(parseFloat(valor))) { alert('Valor inválido.'); return; }
        if (!dataVenc) { alert('Informe a data de vencimento.'); return; }
        var data = { tipo: tipo, conta_id: contaId, descricao: descricao, valor: valor, data_vencimento: dataVenc, observacao: obs };
        if (tipo === 'CONTA') {
            var catId = $('#nova-categoria').val();
            if (!catId) { alert('Selecione a categoria.'); return; }
            data.categoria_id = catId;
            data.subcategoria_id = $('#nova-subcategoria').val() || '';
        } else {
            var funcId = $('#nova-funcionario').val();
            if (!funcId) { alert('Selecione o funcionário.'); return; }
            data.funcionario_id = funcId;
            if (tipo === 'BENEFICIO') {
                var tipoBenId = $('#nova-tipo-beneficio').val();
                if (!tipoBenId) { alert('Selecione o tipo de benefício.'); return; }
                data.tipo_beneficio_id = tipoBenId;
            }
        }
        var anexoInput = document.getElementById('editar-anexo');
        var comprovanteInput = document.getElementById('editar-comprovante');
        var temAnexo = anexoInput && anexoInput.files && anexoInput.files[0];
        var temComprovante = window.IS_SUPERUSER === true && comprovanteInput && comprovanteInput.files && comprovanteInput.files[0];
        if (temAnexo || temComprovante) {
            var formData = new FormData();
            for (var k in data) { if (data.hasOwnProperty(k)) formData.append(k, data[k]); }
            if (temAnexo) {
                var erroAnexo = validarArquivo(anexoInput.files[0]);
                if (erroAnexo) { alert(erroAnexo); return; }
                formData.append('anexo', anexoInput.files[0]);
            }
            if (temComprovante) {
                var erroComp = validarArquivo(comprovanteInput.files[0]);
                if (erroComp) { alert(erroComp); return; }
                formData.append('comprovante', comprovanteInput.files[0]);
            }
            $.ajax({ url: urlEditar, type: 'POST', data: formData, processData: false, contentType: false }).done(function(r) {
                if (r.success) {
                    bootstrap.Modal.getInstance(document.getElementById('modalNovaConta')).hide();
                    $('#editar-conta-id').val('');
                    carregarTabela(tipo);
                } else {
                    alert(r.message || 'Erro ao atualizar.');
                }
            }).fail(function() { alert('Erro ao atualizar.'); });
        } else {
            $.ajax({ url: urlEditar, type: 'POST', data: data }).done(function(r) {
                if (r.success) {
                    bootstrap.Modal.getInstance(document.getElementById('modalNovaConta')).hide();
                    $('#editar-conta-id').val('');
                    carregarTabela(tipo);
                } else {
                    alert(r.message || 'Erro ao atualizar.');
                }
            }).fail(function() { alert('Erro ao atualizar.'); });
        }
    }
    var titulosModal = { 'CONTA': 'Adicionar conta (empresa)', 'SALARIO': 'Adicionar salário', 'BENEFICIO': 'Adicionar benefício' };
    function abrirModalNovaConta() {
        $('#editar-conta-id').val('');
        $('#editar-comprovante-row').hide();
        $('#editar-anexo-row').hide();
        $('#nova-anexo-row').show();
        $('#nova-conta-row-tipo').show();
        $('#nova-conta-tipo-select').val('CONTA');
        $('#modalNovaContaTitulo').html('<i class="bx bx-plus-circle"></i> Adicionar conta a pagar');
        toggleCamposNovaConta();
        limparFormNovaConta();
        new bootstrap.Modal(document.getElementById('modalNovaConta')).show();
    }
    function abrirModalNovaContaPorTab(tipo) {
        $('#editar-conta-id').val('');
        $('#editar-comprovante-row').hide();
        $('#editar-anexo-row').hide();
        $('#nova-anexo-row').show();
        $('#nova-conta-row-tipo').hide();
        $('#nova-conta-tipo-select').val(tipo);
        $('#modalNovaContaTitulo').html('<i class="bx bx-plus-circle"></i> ' + (titulosModal[tipo] || 'Adicionar conta a pagar'));
        toggleCamposNovaConta();
        limparFormNovaConta();
        new bootstrap.Modal(document.getElementById('modalNovaConta')).show();
    }
    function limparFormNovaConta() {
        $('#nova-descricao').val('');
        $('#nova-valor').val('');
        $('#nova-data-vencimento').val(dataHoje());
        $('#nova-observacao').val('');
        $('#nova-categoria').val('');
        $('#nova-subcategoria').html('<option value="">Selecione...</option>');
        $('#nova-funcionario').val('');
        $('#nova-tipo-beneficio').val('');
        limparPreviewArquivo('nova-anexo', 'preview-nova', 'preview-nova-nome');
        limparPreviewArquivo('editar-anexo', 'preview-editar-anexo', 'preview-editar-anexo-nome');
        limparPreviewArquivo('editar-comprovante', 'preview-editar-comprovante', 'preview-editar-comprovante-nome');
    }
    function toggleCamposNovaConta() {
        var t = $('#nova-conta-tipo-select').val();
        if (t === 'CONTA') {
            $('#nova-conta-campos-conta').show();
            $('#nova-conta-campos-funcionario').hide();
            $('#nova-conta-campos-tipo-beneficio').hide();
        } else if (t === 'SALARIO') {
            $('#nova-conta-campos-conta').hide();
            $('#nova-conta-campos-funcionario').show();
            $('#nova-conta-campos-tipo-beneficio').hide();
        } else {
            $('#nova-conta-campos-conta').hide();
            $('#nova-conta-campos-funcionario').show();
            $('#nova-conta-campos-tipo-beneficio').show();
        }
    }
    function carregarSubcategorias(categoriaId) {
        var $sub = $('#nova-subcategoria');
        $sub.html('<option value="">Selecione...</option>');
        if (!categoriaId) return;
        $.get(urlSubcategorias, { categoria_id: categoriaId, ativos: 'true' }).done(function(r) {
            if (r.success && r.result) {
                r.result.forEach(function(s) {
                    $sub.append('<option value="' + s.id + '">' + (s.nome || '') + '</option>');
                });
            }
        });
    }
    function salvarNovaConta() {
        var tipo = $('#nova-conta-tipo-select').val();
        var descricao = $('#nova-descricao').val().trim();
        var valor = $('#nova-valor').val().replace(',', '.').trim();
        var dataVenc = $('#nova-data-vencimento').val();
        var obs = $('#nova-observacao').val().trim() || '';
        if (!descricao) { alert('Informe a descrição.'); return; }
        if (!valor || isNaN(parseFloat(valor))) { alert('Valor inválido.'); return; }
        if (!dataVenc) { alert('Informe a data de vencimento.'); return; }
        var data = { tipo: tipo, descricao: descricao, valor: valor, data_vencimento: dataVenc, observacao: obs };
        if (tipo === 'CONTA') {
            var catId = $('#nova-categoria').val();
            if (!catId) { alert('Selecione a categoria.'); return; }
            data.categoria_id = catId;
            data.subcategoria_id = $('#nova-subcategoria').val() || '';
        } else {
            var funcId = $('#nova-funcionario').val();
            if (!funcId) { alert('Selecione o funcionário.'); return; }
            data.funcionario_id = funcId;
            if (tipo === 'BENEFICIO') {
                var tipoBenId = $('#nova-tipo-beneficio').val();
                if (!tipoBenId) { alert('Selecione o tipo de benefício.'); return; }
                data.tipo_beneficio_id = tipoBenId;
            }
        }
        var fileInput = document.getElementById('nova-anexo');
        var temArquivo = fileInput && fileInput.files && fileInput.files[0];
        if (temArquivo) {
            var erro = validarArquivo(fileInput.files[0]);
            if (erro) { alert(erro); return; }
            var formData = new FormData();
            for (var k in data) { if (data.hasOwnProperty(k)) formData.append(k, data[k]); }
            formData.append('anexo', fileInput.files[0]);
            $.ajax({ url: urlCriar, type: 'POST', data: formData, processData: false, contentType: false }).done(function(r) {
                if (r.success) {
                    bootstrap.Modal.getInstance(document.getElementById('modalNovaConta')).hide();
                    tipoAtual = tipo;
                    carregarTabela(tipo);
                } else {
                    alert(r.message || 'Erro ao criar.');
                }
            }).fail(function() { alert('Erro ao criar conta.'); });
        } else {
            $.ajax({ url: urlCriar, type: 'POST', data: data }).done(function(r) {
                if (r.success) {
                    bootstrap.Modal.getInstance(document.getElementById('modalNovaConta')).hide();
                    tipoAtual = tipo;
                    carregarTabela(tipo);
                } else {
                    alert(r.message || 'Erro ao criar.');
                }
            }).fail(function() { alert('Erro ao criar conta.'); });
        }
    }
    function salvarModalConta() {
        if ($('#editar-conta-id').val()) salvarEdicao();
        else salvarNovaConta();
    }
    function abrirModalBonificacaoForm() {
        $('#bonif-editar-id').val('');
        $('#modalBonificacaoFormTitulo').html('<i class="bx bx-gift"></i> Adicionar bonificação a pagar');
        $('#bonif-funcionario').val('');
        $('#bonif-chave-pix').val('');
        $('#bonif-valor').val('');
        $('#bonif-mes-referente').val('');
        $('#bonif-data-pagamento').val('');
        $('#bonif-comprovante').val('');
        $('#bonif-row-opcionais, #bonif-row-comprovante').show();
        new bootstrap.Modal(document.getElementById('modalBonificacaoForm')).show();
    }
    function abrirModalEditarBonif(id) {
        $('#bonif-editar-id').val(id);
        $('#modalBonificacaoFormTitulo').html('<i class="bx bx-edit"></i> Editar bonificação a pagar');
        $('#bonif-data-pagamento').val('');
        $('#bonif-comprovante').val('');
        $('#bonif-row-opcionais, #bonif-row-comprovante').hide();
        var params = paramsFiltrosBonificacoes();
        params.id = id;
        $.get(urlBonifListar, params).done(function(r) {
            if (!r.success || !r.result || !r.result.length) { alert('Registro não encontrado.'); return; }
            var b = r.result[0];
            $('#bonif-funcionario').val(b.funcionario_id || '');
            $('#bonif-chave-pix').val(b.chave_pix || '');
            $('#bonif-valor').val(typeof b.valor_bonificacao === 'number' ? b.valor_bonificacao.toFixed(2).replace('.', ',') : String(b.valor_bonificacao || '').replace('.', ','));
            $('#bonif-mes-referente').val(b.mes_referente || '');
            new bootstrap.Modal(document.getElementById('modalBonificacaoForm')).show();
        }).fail(function() { alert('Erro ao carregar dados.'); });
    }
    function salvarBonificacao() {
        var id = $('#bonif-editar-id').val();
        var funcId = $('#bonif-funcionario').val();
        var valor = $('#bonif-valor').val().replace(',', '.').trim();
        var mesRef = $('#bonif-mes-referente').val().trim();
        var chavePix = $('#bonif-chave-pix').val().trim();
        if (!funcId) { alert('Selecione o funcionário.'); return; }
        if (!chavePix) { alert('Chave PIX é obrigatória.'); return; }
        if (!valor || isNaN(parseFloat(valor))) { alert('Valor da bonificação inválido.'); return; }
        if (!mesRef) { alert('Informe o mês referente.'); return; }
        if (id) {
            var data = { id: id, funcionario_id: funcId, valor_bonificacao: valor, mes_referente: mesRef, chave_pix: chavePix };
            $.ajax({ url: urlBonifEditar, type: 'POST', data: data }).done(function(r) {
                if (r.success) {
                    bootstrap.Modal.getInstance(document.getElementById('modalBonificacaoForm')).hide();
                    $('#bonif-editar-id').val('');
                    carregarTabelaBonificacoes();
                } else { alert(r.message || 'Erro ao atualizar.'); }
            }).fail(function() { alert('Erro ao atualizar.'); });
        } else {
            var dataPag = $('#bonif-data-pagamento').val();
            var fileInput = document.getElementById('bonif-comprovante');
            var temArquivo = fileInput && fileInput.files && fileInput.files[0];
            if (dataPag || temArquivo) {
                var formData = new FormData();
                formData.append('funcionario_id', funcId);
                formData.append('valor_bonificacao', valor);
                formData.append('mes_referente', mesRef);
                formData.append('chave_pix', chavePix);
                if (dataPag) formData.append('data_pagamento', dataPag);
                if (temArquivo) {
                    var erro = validarArquivo(fileInput.files[0]);
                    if (erro) { alert(erro); return; }
                    formData.append('comprovante', fileInput.files[0]);
                }
                $.ajax({ url: urlBonifCriar, type: 'POST', data: formData, processData: false, contentType: false }).done(function(r) {
                    if (r.success) {
                        bootstrap.Modal.getInstance(document.getElementById('modalBonificacaoForm')).hide();
                        $('#bonif-editar-id').val('');
                        carregarTabelaBonificacoes();
                    } else { alert(r.message || 'Erro ao criar.'); }
                }).fail(function(xhr) {
                    var msg = (xhr.responseJSON && xhr.responseJSON.message) ? xhr.responseJSON.message : (xhr.responseText || 'Erro ao criar.');
                    if (typeof msg !== 'string' || msg.length > 500) msg = 'Erro ao criar.';
                    alert(msg);
                });
            } else {
                $.ajax({ url: urlBonifCriar, type: 'POST', data: { funcionario_id: funcId, valor_bonificacao: valor, mes_referente: mesRef, chave_pix: chavePix } }).done(function(r) {
                    if (r.success) {
                        bootstrap.Modal.getInstance(document.getElementById('modalBonificacaoForm')).hide();
                        $('#bonif-editar-id').val('');
                        carregarTabelaBonificacoes();
                    } else { alert(r.message || 'Erro ao criar.'); }
                }).fail(function(xhr) {
                    var msg = (xhr.responseJSON && xhr.responseJSON.message) ? xhr.responseJSON.message : (xhr.responseText || 'Erro ao criar.');
                    if (typeof msg !== 'string' || msg.length > 500) msg = 'Erro ao criar.';
                    alert(msg);
                });
            }
        }
    }
    function abrirModalBonifPagarAgora(id, funcionarioNome, valor, mesReferente, chavePix) {
        $('#bonif-pagar-id').val(id);
        var htmlDados = '<p><strong>' + (funcionarioNome || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') + '</strong><br>Valor: ' + formatarMoeda(valor) + '<br>Mês referente: ' + (mesReferente || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') + '</p>';
        htmlDados += '<p class="mb-0"><strong>Chave PIX:</strong> ' + (chavePix || '-').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') + '</p>';
        $('#bonifPagarDados').html(htmlDados);
        $('#bonif-pagar-data').val(dataHoje());
        $('#bonif-pagar-comprovante').val('');
        new bootstrap.Modal(document.getElementById('modalBonificacaoPagarAgora')).show();
    }
    function confirmarBonifPagar() {
        var id = $('#bonif-pagar-id').val();
        if (!id) return;
        var dataPag = $('#bonif-pagar-data').val();
        var fileInput = document.getElementById('bonif-pagar-comprovante');
        if (!dataPag) { alert('Data de pagamento é obrigatória.'); return; }
        if (!fileInput.files || !fileInput.files[0]) { alert('Comprovante é obrigatório.'); return; }
        var erro = validarArquivo(fileInput.files[0]);
        if (erro) { alert(erro); return; }
        var formData = new FormData();
        formData.append('id', id);
        formData.append('data_pagamento', dataPag);
        formData.append('comprovante', fileInput.files[0]);
        $.ajax({ url: urlBonifPagarAgora, type: 'POST', data: formData, processData: false, contentType: false }).done(function(r) {
            if (r.success) {
                bootstrap.Modal.getInstance(document.getElementById('modalBonificacaoPagarAgora')).hide();
                carregarTabelaBonificacoes();
            } else { alert(r.message || 'Erro ao registrar pagamento.'); }
        }).fail(function() { alert('Erro ao registrar pagamento.'); });
    }
    function inativarBonif(id) {
        if (!confirm('Inativar esta bonificação?')) return;
        $.ajax({ url: urlBonifInativar, type: 'POST', data: { id: id } }).done(function(r) {
            if (r.success) carregarTabelaBonificacoes();
            else alert(r.message || 'Erro ao inativar.');
        }).fail(function() { alert('Erro ao inativar.'); });
    }
    function excluirConta(id, tipo) {
        if (!window.HAS_PERM_DELET) {
            alert('Você não tem permissão para excluir.');
            return;
        }
        if (!confirm('Excluir esta conta a pagar?')) return;
        $.ajax({
            url: urlDeletar,
            type: 'POST',
            data: { tipo: tipo || tipoAtual, conta_id: id }
        }).done(function(r) {
            if (r.success) carregarTabela(tipo || tipoAtual);
            else alert(r.message || 'Erro ao excluir.');
        }).fail(function() { alert('Erro ao excluir.'); });
    }
    $(document).ready(function() {
        initUploadArea('upload-area-nova', 'nova-anexo', 'preview-nova', 'preview-nova-nome');
        initUploadArea('upload-area-editar-anexo', 'editar-anexo', 'preview-editar-anexo', 'preview-editar-anexo-nome');
        initUploadArea('upload-area-editar-comprovante', 'editar-comprovante', 'preview-editar-comprovante', 'preview-editar-comprovante-nome');
        initUploadArea('upload-area-pago', 'modalPagoComprovante', 'preview-pago', 'preview-pago-nome');
        $(document).on('click', '.btn-remover-anexo', function() {
            var target = $(this).data('target');
            var previewMap = {
                'nova-anexo': ['preview-nova', 'preview-nova-nome'],
                'editar-anexo': ['preview-editar-anexo', 'preview-editar-anexo-nome'],
                'editar-comprovante': ['preview-editar-comprovante', 'preview-editar-comprovante-nome'],
                'modalPagoComprovante': ['preview-pago', 'preview-pago-nome']
            };
            var map = previewMap[target];
            if (map) limparPreviewArquivo(target, map[0], map[1]);
        });
        var params = new URLSearchParams(window.location.search);
        var tipoUrl = (params.get('tipo') || '').toUpperCase();
        var idUrl = params.get('id') || '';
        if (tipoUrl === 'CONTA' || tipoUrl === 'SALARIO' || tipoUrl === 'BENEFICIO') {
            tipoAtual = tipoUrl;
            if (idUrl) filtroIdFromUrl = idUrl;
            $('#tabsContasPagar button[data-tipo="' + tipoUrl + '"]').tab('show');
            carregarTabela(tipoUrl);
        } else {
            carregarTabela('CONTA');
        }
        $('#tabsContasPagar button[data-bs-toggle="tab"]').on('show.bs.tab', function() {
            var t = $(this).data('tipo');
            if (t === 'BONIFICACAO') carregarTabelaBonificacoes();
            else if (t) carregarTabela(t);
        });
        $('#tab-conta .filtro-categoria').on('change', function() { carregarSubcategoriasFiltro($(this).val()); });
        $('.btn-aplicar-filtros').on('click', function() {
            var $f = $(this).closest('.filtros-contas-pagar');
            var t = $f.data('tipo');
            if (t) carregarTabela(t);
        });
        $('.btn-aplicar-filtros-bonif').on('click', function() { carregarTabelaBonificacoes(); });
        $('#btnAdicionarBonificacao').on('click', abrirModalBonificacaoForm);
        $('#bonif-funcionario').on('change', function() {
            var opt = $(this).find('option:selected');
            $('#bonif-chave-pix').val(opt.attr('data-chave-pix') || '');
        });
        $('#btnSalvarBonificacao').on('click', salvarBonificacao);
        $('#btnConfirmarBonifPagar').on('click', confirmarBonifPagar);
        $('#btnConfirmarPago').on('click', confirmarPago);
        $('#nova-conta-tipo-select').on('change', toggleCamposNovaConta);
        $('#nova-categoria').on('change', function() { carregarSubcategorias($(this).val()); });
        $('#btnSalvarNovaConta').on('click', salvarModalConta);
    });
    window.financeiroGeralContasPagar = { abrirModalPago: abrirModalPago, abrirModalNovaConta: abrirModalNovaConta, abrirModalNovaContaPorTab: abrirModalNovaContaPorTab, abrirModalEditar: abrirModalEditar, abrirModalBonifPagarAgora: abrirModalBonifPagarAgora, abrirModalEditarBonif: abrirModalEditarBonif, inativarBonif: inativarBonif, excluirConta: excluirConta };
    window.abrirModalNovaContaPorTab = abrirModalNovaContaPorTab;
})();
