(function() {
    var base = (window.BONIFICACOES_BASE || '').replace(/\/?$/, '') + '/';
    var urlRegras = base + 'api/regras/';
    var urlRegrasNova = base + 'api/regras/nova/';
    var urlRegrasEditar = base + 'api/regras/editar/';
    var urlRegrasDeletar = base + 'api/regras/deletar/';
    var urlGatilhos = base + 'api/gatilhos/';
    var urlGatilhosSalvar = base + 'api/gatilhos/salvar/';
    var urlGatilhosDeletar = base + 'api/gatilhos/deletar/';
    var urlVinculos = base + 'api/vinculos/';
    var urlSetoresEmpresas = base + 'api/vinculos/setores-empresas/';
    var urlVinculosFuncionarios = base + 'api/vinculos/funcionarios/';
    var urlVinculosRegras = base + 'api/vinculos/regras/';
    var urlVinculosSalvar = base + 'api/vinculos/salvar/';
    var urlVinculosLote = base + 'api/vinculos/lote/';
    var urlVinculosDeletar = base + 'api/vinculos/deletar/';
    var urlReducaoRegras = base + 'api/reducao-regras/';
    var urlReducaoRegrasSalvar = base + 'api/reducao-regras/salvar/';
    var urlReducaoRegrasDeletar = base + 'api/reducao-regras/deletar/';
    var urlReducoesFuncionario = base + 'api/reducoes-funcionario/';
    var urlReducaoFuncionarioNova = base + 'api/reducoes-funcionario/nova/';
    var urlReducaoFuncionarioDeletar = base + 'api/reducoes-funcionario/deletar/';
    var urlCalculoPreview = base + 'api/calculo/preview/';
    var urlCalculoListar = base + 'api/calculo/listar/';
    var urlCalcular = base + 'api/calculo/calcular/';
    var urlCalcularLote = base + 'api/calculo/calcular-lote/';
    var urlCalculoDeletar = base + 'api/calculo/deletar/';

    function formatarMoeda(v) {
        if (v === null || v === undefined) return '-';
        return 'R$ ' + parseFloat(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function loadRegras() {
        $.get(urlRegras, { ativos: 'false' }).done(function(r) {
            var $tb = $('#tabela-regras');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(regra) {
                    var gatilhoInfo = regra.tipo_regra === 'percentual' ? (regra.percentual_padrao ? regra.percentual_padrao + '%' : '-') : (regra.gatilhos && regra.gatilhos.length ? regra.gatilhos.length + ' gatilho(s)' : 'Sem gatilhos');
                    var btnGatilhos = (regra.tipo_regra === 'gatilho_percentual' || regra.tipo_regra === 'gatilho_valor_fixo') ? '<button type="button" class="btn btn-sm btn-outline-primary btn-gatilhos-regra" data-id="' + regra.id + '" data-nome="' + (regra.nome || '').replace(/"/g, '&quot;') + '" data-tipo="' + regra.tipo_regra + '"><i class="bx bx-plus-circle"></i> Gatilhos</button> ' : '';
                    $tb.append('<tr><td>' + (regra.nome || '') + '</td><td>' + (regra.tipo_regra_display || '') + '</td><td>' + (regra.campo_valor_display || '') + '</td><td>' + gatilhoInfo + '</td><td>' + (regra.ativo ? 'Ativo' : 'Inativo') + '</td><td>' + btnGatilhos + '<button type="button" class="btn btn-sm btn-outline-secondary btn-editar-regra" data-id="' + regra.id + '">Editar</button> <button type="button" class="btn btn-sm btn-outline-danger btn-deletar-regra" data-id="' + regra.id + '">Excluir</button></td></tr>');
                });
            }
        });
    }

    function loadVinculos() {
        var params = { setor_id: $('#filtro-vinculos-setor').val() || '', empresa_id: $('#filtro-vinculos-empresa').val() || '' };
        $.get(urlVinculos, params).done(function(r) {
            var $tb = $('#tabela-vinculos');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(v) {
                    var vig = (v.data_inicio || '-') + ' a ' + (v.data_fim || '-');
                    $tb.append('<tr><td>' + (v.funcionario_nome || '') + '</td><td>' + (v.regra_nome || '') + '</td><td>' + (v.setor_nome || '') + '</td><td>' + v.prioridade + '</td><td>' + vig + '</td><td>' + (v.ativo ? 'Ativo' : 'Inativo') + '</td><td><button type="button" class="btn btn-sm btn-outline-secondary btn-editar-vinculo" data-id="' + v.id + '">Editar</button> <button type="button" class="btn btn-sm btn-outline-danger btn-deletar-vinculo" data-id="' + v.id + '">Excluir</button></td></tr>');
                });
            }
        });
    }

    function loadReducaoRegras() {
        $.get(urlReducaoRegras, { ativos: 'false' }).done(function(r) {
            var $tb = $('#tabela-reducao-regras');
            $tb.empty();
            $('#nova-reducao-regra').find('option:not(:first)').remove();
            if (r.success && r.result) {
                r.result.forEach(function(regra) {
                    $tb.append('<tr><td>' + regra.ordem + '</td><td>' + (regra.titulo || '') + '</td><td>' + regra.percentual + '%</td><td>' + (regra.ativo ? 'Ativo' : 'Inativo') + '</td><td><button type="button" class="btn btn-sm btn-outline-danger btn-deletar-reducao-regra" data-id="' + regra.id + '">Excluir</button></td></tr>');
                    $('#nova-reducao-regra').append('<option value="' + regra.id + '">' + (regra.titulo || '') + ' (' + regra.percentual + '%)</option>');
                });
            }
        });
    }

    function loadReducoesFuncionario() {
        var funcId = $('#nova-reducao-funcionario').val();
        if (!funcId) {
            $('#tabela-reducoes-funcionario').empty();
            return;
        }
        $.get(urlReducoesFuncionario, { funcionario_id: funcId }).done(function(r) {
            var $tb = $('#tabela-reducoes-funcionario');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(red) {
                    $tb.append('<tr><td>' + (red.regra_titulo || '') + '</td><td>' + red.percentual + '%</td><td>' + (red.data_evento || '') + '</td><td><button type="button" class="btn btn-sm btn-outline-danger btn-deletar-reducao-func" data-id="' + red.id + '">Excluir</button></td></tr>');
                });
            }
        });
    }

    function loadCalculos() {
        var params = { periodo_inicio: $('#calculo-periodo-inicio').val() || '', periodo_fim: $('#calculo-periodo-fim').val() || '', funcionario_id: $('#calculo-funcionario').val() || '' };
        $.get(urlCalculoListar, params).done(function(r) {
            var $tb = $('#tabela-calculos');
            $tb.empty();
            if (r.success && r.result) {
                r.result.forEach(function(c) {
                    $tb.append('<tr><td>' + (c.funcionario_nome || '') + '</td><td>' + (c.regra_nome || '') + '</td><td>' + (c.periodo_inicio || '') + ' a ' + (c.periodo_fim || '') + '</td><td>' + formatarMoeda(c.valor_base) + '</td><td>' + formatarMoeda(c.valor_bonificacao) + '</td><td>' + formatarMoeda(c.valor_bonificacao_final) + '</td><td>' + (c.data_calculo || '') + '</td><td><button type="button" class="btn btn-sm btn-outline-danger btn-deletar-calculo" data-id="' + c.id + '">Excluir</button></td></tr>');
                });
            }
        });
    }

    function loadFuncionariosSimples(selectId, filtros) {
        var params = filtros || {};
        $.get(urlVinculosFuncionarios, params).done(function(r) {
            var $sel = $(selectId);
            $sel.find('option:not(:first)').remove();
            if (r.success && r.result) {
                r.result.forEach(function(f) {
                    $sel.append('<option value="' + f.id + '">' + (f.nome || '') + '</option>');
                });
            }
        });
    }

    function loadRegrasSimples(selectId) {
        $.get(urlVinculosRegras).done(function(r) {
            var $sel = $(selectId);
            $sel.find('option:not(:first)').remove();
            if (r.success && r.result) {
                r.result.forEach(function(regra) {
                    $sel.append('<option value="' + regra.id + '">' + (regra.nome || '') + '</option>');
                });
            }
        });
    }

    function abrirModalNovaRegra() {
        $('#modal-regra-id').val('');
        $('#modal-regra-nome').val('');
        $('#modal-regra-tipo').val('percentual');
        $('#modal-regra-percentual').val('');
        $('#modal-regra-campo').val('valor_repasse');
        $('#modal-regra-ativo').val('true');
        $('#modalRegraTitle').text('Nova Regra');
        $('#container-percentual-padrao').show();
        $('#container-gatilhos').hide();
        $('#lista-gatilhos').empty();
        new bootstrap.Modal(document.getElementById('modalRegra')).show();
    }

    function aplicarTipoRegraModal() {
        var tipo = $('#modal-regra-tipo').val();
        if (tipo === 'percentual') {
            $('#container-percentual-padrao').show();
            $('#container-gatilhos').hide();
        } else {
            $('#container-percentual-padrao').hide();
            $('#container-gatilhos').show();
            var regraId = $('#modal-regra-id').val();
            if (regraId) loadGatilhosNaModal(regraId);
        }
    }

    function loadGatilhosNaModal(regraId) {
        $.get(urlGatilhos, { regra_id: regraId }).done(function(r) {
            var $lista = $('#lista-gatilhos');
            $lista.empty();
            if (r.success && r.result) {
                r.result.forEach(function(g) {
                    var txt = g.percentual ? '≥ ' + formatarMoeda(g.valor_minimo) + ' → ' + g.percentual + '%' : '≥ ' + formatarMoeda(g.valor_minimo) + ' → ' + formatarMoeda(g.valor_fixo);
                    $lista.append('<div class="d-flex align-items-center gap-2 mb-1"><span class="small">' + txt + '</span><button type="button" class="btn btn-sm btn-outline-danger btn-deletar-gatilho-modal" data-id="' + g.id + '">Excluir</button></div>');
                });
            }
        });
    }

    function salvarRegra() {
        var id = $('#modal-regra-id').val();
        var nome = $('#modal-regra-nome').val().trim();
        var tipo = $('#modal-regra-tipo').val();
        var campo = $('#modal-regra-campo').val();
        var percentual = $('#modal-regra-percentual').val().trim();
        var ativo = $('#modal-regra-ativo').val();
        if (!nome) { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'warning', title: 'Atenção', text: 'Nome é obrigatório.' }) : alert('Nome é obrigatório.')); return; }
        var url = id ? urlRegrasEditar : urlRegrasNova;
        var data = id ? { regra_id: id, nome: nome, tipo_regra: tipo, campo_valor: campo, ativo: ativo } : { nome: nome, tipo_regra: tipo, campo_valor: campo, ativo: ativo };
        if (tipo === 'percentual' && percentual) data.percentual_padrao = percentual;
        $.ajax({ url: url, type: 'POST', data: data }).done(function(r) {
            if (r.success) { bootstrap.Modal.getInstance(document.getElementById('modalRegra')).hide(); loadRegras(); if (typeof Swal !== 'undefined') Swal.fire({ icon: 'success', title: 'Salvo!', timer: 1500, showConfirmButton: false }); } else { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'error', title: 'Erro', text: r.message }) : alert(r.message || 'Erro.')); }
        }).fail(function() { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'error', title: 'Erro', text: 'Falha ao salvar.' }) : alert('Erro ao salvar.')); });
    }

    function abrirModalEditarRegra(id) {
        $.get(urlRegras, { ativos: 'false' }).done(function(r) {
            if (!r.success || !r.result) return;
            var regra = r.result.find(function(x) { return x.id == id; });
            if (!regra) return;
            $('#modal-regra-id').val(regra.id);
            $('#modal-regra-nome').val(regra.nome);
            $('#modal-regra-tipo').val(regra.tipo_regra);
            $('#modal-regra-percentual').val(regra.percentual_padrao || '');
            $('#modal-regra-campo').val(regra.campo_valor);
            $('#modal-regra-ativo').val(regra.ativo ? 'true' : 'false');
            $('#modalRegraTitle').text('Editar Regra');
            aplicarTipoRegraModal();
            new bootstrap.Modal(document.getElementById('modalRegra')).show();
        });
    }

    function deletarRegra(id) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({ title: 'Excluir regra?', text: 'Esta ação não pode ser desfeita.', icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545', cancelButtonColor: '#6c757d', confirmButtonText: 'Sim, excluir' }).then(function(result) {
                if (result.isConfirmed) { $.ajax({ url: urlRegrasDeletar, type: 'POST', data: { regra_id: id } }).done(function(r) { if (r.success) { loadRegras(); Swal.fire({ icon: 'success', title: 'Excluído!', timer: 1500, showConfirmButton: false }); } else { Swal.fire({ icon: 'error', title: 'Erro', text: r.message }); } }).fail(function() { Swal.fire({ icon: 'error', title: 'Erro', text: 'Falha ao excluir.' }); }); }
            });
        } else {
            if (!confirm('Excluir esta regra?')) return;
            $.ajax({ url: urlRegrasDeletar, type: 'POST', data: { regra_id: id } }).done(function(r) { if (r.success) loadRegras(); else alert(r.message || 'Erro.'); }).fail(function() { alert('Erro.'); });
        }
    }

    function abrirModalGatilhosRegra(regraId, regraNome, tipoRegra) {
        $('#modal-gatilhos-regra-id').val(regraId);
        $('#modalGatilhosTitle').html('<i class="bx bx-plus-circle me-2"></i>Gerenciar Gatilhos');
        $('#modalGatilhosRegraNome').text('Regra: ' + (regraNome || ''));
        loadGatilhosStandalone(regraId);
        window._gatilhosRegraTipo = tipoRegra;
        new bootstrap.Modal(document.getElementById('modalGatilhos')).show();
    }

    function loadGatilhosStandalone(regraId) {
        $.get(urlGatilhos, { regra_id: regraId }).done(function(r) {
            var $lista = $('#lista-gatilhos-standalone');
            $lista.empty();
            if (r.success && r.result && r.result.length) {
                r.result.forEach(function(g) {
                    var txt = g.percentual ? '≥ ' + formatarMoeda(g.valor_minimo) + ' → ' + g.percentual + '%' : '≥ ' + formatarMoeda(g.valor_minimo) + ' → ' + formatarMoeda(g.valor_fixo);
                    $lista.append('<div class="bonificacoes-gatilho-item d-flex align-items-center justify-content-between py-2 px-3 mb-2 rounded"><span class="small">' + txt + '</span><button type="button" class="btn btn-sm btn-outline-danger btn-deletar-gatilho-standalone" data-id="' + g.id + '" data-regra-id="' + regraId + '"><i class="bx bx-trash"></i></button></div>');
                });
            } else {
                $lista.append('<p class="text-muted small mb-0">Nenhum gatilho cadastrado. Clique em "Adicionar Gatilho" para criar.</p>');
            }
        });
    }

    function abrirModalGatilho(regraId, gatilhoId) {
        $('#modal-gatilho-id').val(gatilhoId || '');
        $('#modal-gatilho-regra-id').val(regraId);
        $('#modal-gatilho-valor-min').val('');
        $('#modal-gatilho-percentual').val('');
        $('#modal-gatilho-valor-fixo').val('');
        $('#modal-gatilho-ordem').val('0');
        var tipoForcado = window._gatilhosRegraTipo;
        $.get(urlRegras, { ativos: 'false' }).done(function(r) {
            var regra = (r.success && r.result) ? r.result.find(function(x) { return x.id == regraId; }) : null;
            var tipo = tipoForcado || (regra ? regra.tipo_regra : 'gatilho_percentual');
            if (tipo === 'gatilho_valor_fixo') {
                $('#container-gatilho-percentual').hide();
                $('#container-gatilho-valor-fixo').show();
            } else {
                $('#container-gatilho-percentual').show();
                $('#container-gatilho-valor-fixo').hide();
            }
            if (gatilhoId) {
                $.get(urlGatilhos, { regra_id: regraId }).done(function(rg) {
                    if (rg.success && rg.result) {
                        var g = rg.result.find(function(x) { return x.id == gatilhoId; });
                        if (g) {
                            $('#modal-gatilho-valor-min').val(g.valor_minimo);
                            $('#modal-gatilho-percentual').val(g.percentual || '');
                            $('#modal-gatilho-valor-fixo').val(g.valor_fixo || '');
                            $('#modal-gatilho-ordem').val(g.ordem || 0);
                        }
                    }
                });
            }
            new bootstrap.Modal(document.getElementById('modalGatilho')).show();
        });
    }

    function salvarGatilho() {
        var regraId = $('#modal-gatilho-regra-id').val();
        var gatilhoId = $('#modal-gatilho-id').val();
        var valorMin = $('#modal-gatilho-valor-min').val().trim();
        var percentual = $('#modal-gatilho-percentual').val().trim();
        var valorFixo = $('#modal-gatilho-valor-fixo').val().trim();
        var ordem = $('#modal-gatilho-ordem').val() || '0';
        if (!valorMin) { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'warning', title: 'Atenção', text: 'Valor mínimo é obrigatório.' }) : alert('Valor mínimo é obrigatório.')); return; }
        var data = { regra_id: regraId, valor_minimo: valorMin, ordem: ordem };
        if (gatilhoId) data.gatilho_id = gatilhoId;
        var tipoForcado = window._gatilhosRegraTipo;
        $.get(urlRegras, { ativos: 'false' }).done(function(r) {
            var regra = (r.success && r.result) ? r.result.find(function(x) { return x.id == regraId; }) : null;
            var tipo = tipoForcado || (regra ? regra.tipo_regra : 'gatilho_percentual');
            if (tipo === 'gatilho_valor_fixo') data.valor_fixo = valorFixo;
            else data.percentual = percentual;
            $.ajax({ url: urlGatilhosSalvar, type: 'POST', data: data }).done(function(res) {
                if (res.success) {
                    bootstrap.Modal.getInstance(document.getElementById('modalGatilho')).hide();
                    loadGatilhosNaModal(regraId);
                    if ($('#modalGatilhos').hasClass('show')) loadGatilhosStandalone(regraId);
                    loadRegras();
                    if (typeof Swal !== 'undefined') Swal.fire({ icon: 'success', title: 'Gatilho salvo!', timer: 1500, showConfirmButton: false });
                } else { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'error', title: 'Erro', text: res.message }) : alert(res.message || 'Erro.')); }
            }).fail(function() { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'error', title: 'Erro', text: 'Falha ao salvar.' }) : alert('Erro.')); });
        });
    }

    function abrirModalVinculoLote() {
        var params = { setor_id: $('#filtro-vinculos-setor').val() || '', empresa_id: $('#filtro-vinculos-empresa').val() || '' };
        $.get(urlVinculosFuncionarios, params).done(function(rFunc) {
            $.get(urlVinculosRegras).done(function(rRegras) {
                var $cf = $('#container-checkbox-funcionarios');
                var $cr = $('#container-checkbox-regras');
                $cf.empty();
                $cr.empty();
                if (rFunc.success && rFunc.result) {
                    rFunc.result.forEach(function(f) {
                        $cf.append('<div class="form-check"><input class="form-check-input chk-func-lote" type="checkbox" value="' + f.id + '" id="chk-func-' + f.id + '"><label class="form-check-label small" for="chk-func-' + f.id + '">' + (f.nome || '') + '</label></div>');
                    });
                }
                if (rRegras.success && rRegras.result) {
                    rRegras.result.forEach(function(r) {
                        $cr.append('<div class="form-check"><input class="form-check-input chk-regra-lote" type="checkbox" value="' + r.id + '" id="chk-regra-' + r.id + '"><label class="form-check-label small" for="chk-regra-' + r.id + '">' + (r.nome || '') + '</label></div>');
                    });
                }
                $('#vinculo-lote-data-inicio').val('');
                $('#vinculo-lote-data-fim').val('');
                $('#vinculo-lote-prioridade').val('0');
                new bootstrap.Modal(document.getElementById('modalVinculoLote')).show();
            });
        });
    }

    function salvarVinculoLote() {
        var funcIds = [];
        $('.chk-func-lote:checked').each(function() { funcIds.push($(this).val()); });
        var regraIds = [];
        $('.chk-regra-lote:checked').each(function() { regraIds.push($(this).val()); });
        if (!funcIds.length || !regraIds.length) {
            (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'warning', title: 'Atenção', text: 'Selecione ao menos um funcionário e uma regra.' }) : alert('Selecione ao menos um funcionário e uma regra.'));
            return;
        }
        var formData = new FormData();
        formData.append('data_inicio', $('#vinculo-lote-data-inicio').val() || '');
        formData.append('data_fim', $('#vinculo-lote-data-fim').val() || '');
        formData.append('prioridade', $('#vinculo-lote-prioridade').val() || '0');
        funcIds.forEach(function(id) { formData.append('funcionario_ids[]', id); });
        regraIds.forEach(function(id) { formData.append('regra_ids[]', id); });
        $.ajax({ url: urlVinculosLote, type: 'POST', data: formData, processData: false, contentType: false }).done(function(r) {
            if (r.success) {
                bootstrap.Modal.getInstance(document.getElementById('modalVinculoLote')).hide();
                loadVinculos();
                (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'success', title: 'Concluído!', text: r.message }) : alert(r.message));
            } else { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'error', title: 'Erro', text: r.message }) : alert(r.message)); }
        }).fail(function() { (typeof Swal !== 'undefined' ? Swal.fire({ icon: 'error', title: 'Erro', text: 'Falha ao vincular.' }) : alert('Falha ao vincular.')); });
    }

    function abrirModalNovoVinculo() {
        $('#modal-vinculo-id').val('');
        $('#modal-vinculo-funcionario').val('');
        $('#modal-vinculo-regra').val('');
        $('#modal-vinculo-data-inicio').val('');
        $('#modal-vinculo-data-fim').val('');
        $('#modal-vinculo-prioridade').val('0');
        $('#modal-vinculo-ativo').val('true');
        $('#modalVinculoTitle').text('Novo Vínculo');
        loadFuncionariosSimples('#modal-vinculo-funcionario', { setor_id: $('#filtro-vinculos-setor').val(), empresa_id: $('#filtro-vinculos-empresa').val() });
        loadRegrasSimples('#modal-vinculo-regra');
        new bootstrap.Modal(document.getElementById('modalVinculo')).show();
    }

    function salvarVinculo() {
        var id = $('#modal-vinculo-id').val();
        var funcId = $('#modal-vinculo-funcionario').val();
        var regraId = $('#modal-vinculo-regra').val();
        var dataInicio = $('#modal-vinculo-data-inicio').val().trim();
        var dataFim = $('#modal-vinculo-data-fim').val().trim();
        var prioridade = $('#modal-vinculo-prioridade').val() || '0';
        var ativo = $('#modal-vinculo-ativo').val();
        if (!funcId || !regraId) { alert('Funcionário e regra são obrigatórios.'); return; }
        var data = { funcionario_id: funcId, regra_id: regraId, data_inicio: dataInicio || '', data_fim: dataFim || '', prioridade: prioridade, ativo: ativo };
        if (id) data.vinculo_id = id;
        $.ajax({ url: urlVinculosSalvar, type: 'POST', data: data }).done(function(r) {
            if (r.success) { bootstrap.Modal.getInstance(document.getElementById('modalVinculo')).hide(); loadVinculos(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro.'); });
    }

    function novaReducaoRegra() {
        var titulo = $('#nova-reducao-titulo').val().trim();
        var percentual = $('#nova-reducao-percentual').val().trim();
        var ordem = $('#nova-reducao-ordem').val() || '1';
        if (!titulo) { alert('Título é obrigatório.'); return; }
        if (!percentual) { alert('Percentual é obrigatório.'); return; }
        $.ajax({ url: urlReducaoRegrasSalvar, type: 'POST', data: { titulo: titulo, percentual: percentual, ordem: ordem } }).done(function(r) {
            if (r.success) { $('#nova-reducao-titulo').val(''); $('#nova-reducao-percentual').val(''); loadReducaoRegras(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro.'); });
    }

    function novaReducaoFuncionario() {
        var funcId = $('#nova-reducao-funcionario').val();
        var regraId = $('#nova-reducao-regra').val();
        var dataEvento = $('#nova-reducao-data').val().trim();
        if (!funcId || !regraId || !dataEvento) { alert('Funcionário, regra e data são obrigatórios.'); return; }
        $.ajax({ url: urlReducaoFuncionarioNova, type: 'POST', data: { funcionario_id: funcId, regra_reducao_id: regraId, data_evento: dataEvento } }).done(function(r) {
            if (r.success) { $('#nova-reducao-data').val(''); loadReducoesFuncionario(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro.'); });
    }

    function previewCalculo() {
        var periodoInicio = $('#calculo-periodo-inicio').val();
        var periodoFim = $('#calculo-periodo-fim').val();
        var funcId = $('#calculo-funcionario').val() || '';
        var setorId = $('#calculo-setor').val() || '';
        if (!periodoInicio || !periodoFim) { alert('Período início e fim são obrigatórios.'); return; }
        $.get(urlCalculoPreview, { periodo_inicio: periodoInicio, periodo_fim: periodoFim, funcionario_id: funcId, setor_id: setorId }).done(function(r) {
            var $tb = $('#preview-calculo-tbody');
            $tb.empty();
            $('#preview-calculo-container').show();
            if (r.success && r.result && r.result.length) {
                r.result.forEach(function(p) {
                    $tb.append('<tr><td>' + (p.funcionario_nome || '') + '</td><td>' + (p.regra_nome || '') + '</td><td>' + formatarMoeda(p.valor_base) + '</td><td>' + formatarMoeda(p.valor_bonificacao) + '</td><td>' + formatarMoeda(p.valor_bonificacao_final) + '</td></tr>');
                });
            } else {
                $tb.append('<tr><td colspan="5" class="text-muted">Nenhum resultado para o período.</td></tr>');
            }
        }).fail(function() { alert('Erro ao buscar preview.'); });
    }

    function calcularLote() {
        var periodoInicio = $('#calculo-periodo-inicio').val();
        var periodoFim = $('#calculo-periodo-fim').val();
        var setorId = $('#calculo-setor').val() || '';
        if (!periodoInicio || !periodoFim) { alert('Período início e fim são obrigatórios.'); return; }
        if (!confirm('Calcular bonificações em lote para o período selecionado?')) return;
        $.ajax({ url: urlCalcularLote, type: 'POST', data: { periodo_inicio: periodoInicio, periodo_fim: periodoFim, setor_id: setorId } }).done(function(r) {
            if (r.success) { alert(r.message); loadCalculos(); } else { alert(r.message || 'Erro.'); }
        }).fail(function() { alert('Erro.'); });
    }

    $(document).ready(function() {
        loadRegras();
        loadReducaoRegras();
        loadFuncionariosSimples('#nova-reducao-funcionario');
        loadFuncionariosSimples('#calculo-funcionario');
        $.get(urlSetoresEmpresas).done(function(r) {
            if (r.success && r.result) {
                (r.result.setores || []).forEach(function(s) {
                    $('#filtro-vinculos-setor, #calculo-setor').append('<option value="' + s.id + '">' + (s.nome || '') + '</option>');
                });
                (r.result.empresas || []).forEach(function(e) {
                    $('#filtro-vinculos-empresa').append('<option value="' + e.id + '">' + (e.nome || '') + '</option>');
                });
            }
        });
        var hoje = new Date().toISOString().slice(0, 10);
        var primeiroDia = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10);
        $('#calculo-periodo-inicio').val(primeiroDia);
        $('#calculo-periodo-fim').val(hoje);

        $('#btnNovaRegra').on('click', abrirModalNovaRegra);
        $('#btnSalvarRegra').on('click', salvarRegra);
        $('#modal-regra-tipo').on('change', aplicarTipoRegraModal);
        $('#btnAdicionarGatilho').on('click', function() {
            var regraId = $('#modal-regra-id').val();
            if (!regraId) { alert('Salve a regra primeiro para adicionar gatilhos.'); return; }
            abrirModalGatilho(regraId, null);
        });
        $('#btnSalvarGatilho').on('click', salvarGatilho);

        $('#btnNovoVinculo').on('click', abrirModalNovoVinculo);
        $('#btnVinculoLote').on('click', abrirModalVinculoLote);
        $('#btnSalvarVinculo').on('click', salvarVinculo);
        $('#btnSalvarVinculoLote').on('click', salvarVinculoLote);
        $('.btn-selecionar-todos-func').on('click', function() { $('.chk-func-lote').prop('checked', true); });
        $('.btn-limpar-func').on('click', function() { $('.chk-func-lote').prop('checked', false); });
        $('.btn-selecionar-todos-regras').on('click', function() { $('.chk-regra-lote').prop('checked', true); });
        $('.btn-limpar-regras').on('click', function() { $('.chk-regra-lote').prop('checked', false); });
        $('#btnFiltrarVinculos').on('click', loadVinculos);

        $('#btnNovaReducaoRegra').on('click', novaReducaoRegra);
        $('#btnNovaReducaoFuncionario').on('click', novaReducaoFuncionario);
        $('#nova-reducao-funcionario').on('change', loadReducoesFuncionario);

        $('#btnPreviewCalculo').on('click', previewCalculo);
        $('#btnCalcularLote').on('click', calcularLote);

        $(document).on('click', '.btn-editar-regra', function() { abrirModalEditarRegra($(this).data('id')); });
        $(document).on('click', '.btn-gatilhos-regra', function() { abrirModalGatilhosRegra($(this).data('id'), $(this).data('nome'), $(this).data('tipo')); });
        $(document).on('click', '.btn-deletar-regra', function() { deletarRegra($(this).data('id')); });
        $(document).on('click', '.btn-editar-vinculo', function() {
            var id = $(this).data('id');
            $.get(urlVinculos).done(function(r) {
                if (!r.success || !r.result) return;
                var v = r.result.find(function(x) { return x.id == id; });
                if (!v) return;
                $('#modal-vinculo-id').val(v.id);
                $('#modal-vinculo-funcionario').val(v.funcionario_id);
                $('#modal-vinculo-regra').val(v.regra_id);
                $('#modal-vinculo-data-inicio').val(v.data_inicio || '');
                $('#modal-vinculo-data-fim').val(v.data_fim || '');
                $('#modal-vinculo-prioridade').val(v.prioridade);
                $('#modal-vinculo-ativo').val(v.ativo ? 'true' : 'false');
                $('#modalVinculoTitle').text('Editar Vínculo');
                loadFuncionariosSimples('#modal-vinculo-funcionario');
                loadRegrasSimples('#modal-vinculo-regra');
                new bootstrap.Modal(document.getElementById('modalVinculo')).show();
            });
        });
        $(document).on('click', '.btn-deletar-vinculo', function() {
            if (!confirm('Excluir este vínculo?')) return;
            $.ajax({ url: urlVinculosDeletar, type: 'POST', data: { vinculo_id: $(this).data('id') } }).done(function(r) {
                if (r.success) loadVinculos(); else alert(r.message || 'Erro.');
            });
        });
        $(document).on('click', '.btn-deletar-reducao-regra', function() {
            if (!confirm('Excluir esta regra de redução?')) return;
            $.ajax({ url: urlReducaoRegrasDeletar, type: 'POST', data: { regra_id: $(this).data('id') } }).done(function(r) {
                if (r.success) loadReducaoRegras(); else alert(r.message || 'Erro.');
            });
        });
        $(document).on('click', '.btn-deletar-reducao-func', function() {
            if (!confirm('Excluir esta redução?')) return;
            $.ajax({ url: urlReducaoFuncionarioDeletar, type: 'POST', data: { reducao_id: $(this).data('id') } }).done(function(r) {
                if (r.success) loadReducoesFuncionario(); else alert(r.message || 'Erro.');
            });
        });
        $(document).on('click', '.btn-deletar-calculo', function() {
            if (!confirm('Excluir este cálculo?')) return;
            $.ajax({ url: urlCalculoDeletar, type: 'POST', data: { calculo_id: $(this).data('id') } }).done(function(r) {
                if (r.success) loadCalculos(); else alert(r.message || 'Erro.');
            });
        });
        $(document).on('click', '.btn-deletar-gatilho-modal', function() {
            var regraId = $('#modal-regra-id').val();
            var self = this;
            if (typeof Swal !== 'undefined') {
                Swal.fire({ title: 'Excluir gatilho?', icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545', cancelButtonColor: '#6c757d', confirmButtonText: 'Sim, excluir' }).then(function(result) {
                    if (result.isConfirmed) { $.ajax({ url: urlGatilhosDeletar, type: 'POST', data: { gatilho_id: $(self).data('id') } }).done(function(r) { if (r.success) { loadGatilhosNaModal(regraId); loadRegras(); Swal.fire({ icon: 'success', title: 'Excluído!', timer: 1500, showConfirmButton: false }); } }); }
                });
            } else { if (!confirm('Excluir este gatilho?')) return; $.ajax({ url: urlGatilhosDeletar, type: 'POST', data: { gatilho_id: $(self).data('id') } }).done(function(r) { if (r.success) { loadGatilhosNaModal(regraId); loadRegras(); } }); }
        });
        $('.btn-add-gatilho-standalone').on('click', function() {
            var regraId = $('#modal-gatilhos-regra-id').val();
            if (!regraId) return;
            var tipo = window._gatilhosRegraTipo || 'gatilho_percentual';
            abrirModalGatilho(regraId, null);
        });
        $(document).on('click', '.btn-deletar-gatilho-standalone', function() {
            var regraId = $(this).data('regra-id');
            var self = this;
            if (typeof Swal !== 'undefined') {
                Swal.fire({ title: 'Excluir gatilho?', icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545', cancelButtonColor: '#6c757d', confirmButtonText: 'Sim, excluir' }).then(function(result) {
                    if (result.isConfirmed) { $.ajax({ url: urlGatilhosDeletar, type: 'POST', data: { gatilho_id: $(self).data('id') } }).done(function(r) { if (r.success) { loadGatilhosStandalone(regraId); loadRegras(); Swal.fire({ icon: 'success', title: 'Excluído!', timer: 1500, showConfirmButton: false }); } }); }
                });
            } else { if (!confirm('Excluir este gatilho?')) return; $.ajax({ url: urlGatilhosDeletar, type: 'POST', data: { gatilho_id: $(self).data('id') } }).done(function(r) { if (r.success) { loadGatilhosStandalone(regraId); loadRegras(); } }); }
        });

        $('#tabsBonificacoes').on('shown.bs.tab', function(e) {
            if (e.target.getAttribute('data-bs-target') === '#tab-vinculos') loadVinculos();
            if (e.target.getAttribute('data-bs-target') === '#tab-calculos') loadCalculos();
        });
    });
})();
