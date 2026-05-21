(function() {
    var base = (window.CALC_BONIFICACOES_BASE || '').replace(/\/?$/, '') + '/';
    var urlCalculoMes = base + 'api/calculo/mes/';
    var urlVinculosFuncionarios = base + 'api/vinculos/funcionarios/';
    var urlVinculosRegras = base + 'api/vinculos/regras/';

    function formatarMoeda(v) {
        if (v === null || v === undefined) return '-';
        return 'R$ ' + parseFloat(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function buildMeses() {
        var $sel = $('#calc-mes');
        $sel.empty();
        var hoje = new Date();
        for (var i = 0; i < 24; i++) {
            var d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
            var y = d.getFullYear();
            var m = (d.getMonth() + 1);
            var val = y + '-' + (m < 10 ? '0' : '') + m;
            var label = (m < 10 ? '0' : '') + m + '/' + y;
            $sel.append('<option value="' + val + '">' + label + '</option>');
        }
    }

    function loadFuncionarios() {
        $.get(urlVinculosFuncionarios, { incluir_inativos: 'true' }).done(function(r) {
            var $sel = $('#calc-funcionario');
            $sel.find('option:not(:first)').remove();
            if (r.success && r.result) {
                r.result.forEach(function(f) {
                    $sel.append('<option value="' + f.id + '">' + (f.nome || '') + '</option>');
                });
            }
        });
    }

    function loadRegras() {
        $.get(urlVinculosRegras).done(function(r) {
            var $sel = $('#calc-regra');
            $sel.find('option:not(:first)').remove();
            if (r.success && r.result) {
                r.result.forEach(function(regra) {
                    $sel.append('<option value="' + regra.id + '">' + (regra.nome || '') + '</option>');
                });
            }
        });
    }

    function loadCalcMes() {
        var mes = $('#calc-mes').val();
        if (!mes) {
            $('#tabela-calc-mes').empty();
            return;
        }
        var params = { mes: mes };
        var funcId = $('#calc-funcionario').val();
        if (funcId) params.funcionario_id = funcId;
        var regraId = $('#calc-regra').val();
        if (regraId) params.regra_id = regraId;
        var v = $('#calc-valor-base-min').val();
        if (v) params.valor_base_min = v;
        v = $('#calc-valor-base-max').val();
        if (v) params.valor_base_max = v;
        v = $('#calc-bonificacao-min').val();
        if (v) params.bonificacao_min = v;
        v = $('#calc-bonificacao-max').val();
        if (v) params.bonificacao_max = v;
        v = $('#calc-valor-final-min').val();
        if (v) params.valor_final_min = v;
        v = $('#calc-valor-final-max').val();
        if (v) params.valor_final_max = v;
        var mesVal = $('#calc-mes').val();
            var mesReferenteStr = mesVal ? (mesVal.substring(5, 7) + '/' + mesVal.substring(0, 4)) : '';
            $.get(urlCalculoMes, params).done(function(r) {
                var $tb = $('#tabela-calc-mes');
                $tb.empty();
                if (r.success && r.result) {
                    var hasPagoCms = window.HAS_PAGO_CMS && window.FINANCEIRO_GERAL_CRIAR_JA_PAGA_URL;
                    r.result.forEach(function(row) {
                        var cls = (!row.funcionario_ativo) ? ' calc-row-inativo' : '';
                        var cells = '<td>' + (row.funcionario_nome || '') + '</td><td>' + (row.regra_nome || '') + '</td><td>' + formatarMoeda(row.valor_base) + '</td><td>' + (row.percentual_aplicado || '-') + '</td><td>' + (row.gatilho_valor || '-') + '</td><td>' + formatarMoeda(row.valor_bonificacao) + '</td><td>' + formatarMoeda(row.valor_bonificacao_final) + '</td>';
                        if (hasPagoCms) {
                            var vf = typeof row.valor_bonificacao_final === 'number' ? row.valor_bonificacao_final : parseFloat(row.valor_bonificacao_final) || 0;
                            cells += '<td><button type="button" class="btn btn-sm btn-success btn-pago-calc" data-funcionario-id="' + row.funcionario_id + '" data-valor-bonificacao="' + String(vf).replace('.', ',') + '" data-mes-referente="' + (mesReferenteStr || '').replace(/"/g, '&quot;') + '">Pago</button></td>';
                        }
                        $tb.append('<tr class="' + cls + '">' + cells + '</tr>');
                    });
                }
            });
    }

    function enviarPagoCalc(btn) {
        var $btn = $(btn);
        var url = window.FINANCEIRO_GERAL_CRIAR_JA_PAGA_URL;
        if (!url) return;
        var funcionarioId = $btn.attr('data-funcionario-id');
        var valorBonificacao = ($btn.attr('data-valor-bonificacao') || '').replace(',', '.');
        var mesReferente = $btn.attr('data-mes-referente') || '';
        $btn.prop('disabled', true);
        $.ajax({ url: url, type: 'POST', data: { funcionario_id: funcionarioId, valor_bonificacao: valorBonificacao, mes_referente: mesReferente } }).done(function(r) {
            if (r.success) {
                alert(r.message || 'Bonificação criada e marcada como paga.');
                // Atualiza a célula de ações da linha atual para mostrar apenas o status Pago
                var $td = $btn.closest('td');
                $td.html('<span class="badge bg-success">Pago</span>');
            } else {
                alert(r.message || 'Erro ao registrar.');
                $btn.prop('disabled', false);
            }
        }).fail(function(xhr) {
            var msg = (xhr.responseJSON && xhr.responseJSON.message) ? xhr.responseJSON.message : 'Erro ao enviar.';
            alert(msg);
            $btn.prop('disabled', false);
        });
    }

    $(function() {
        buildMeses();
        loadFuncionarios();
        loadRegras();
        loadCalcMes();
        $('#calc-mes, #calc-funcionario, #calc-regra, #calc-valor-base-min, #calc-valor-base-max, #calc-bonificacao-min, #calc-bonificacao-max, #calc-valor-final-min, #calc-valor-final-max').on('change input', function() {
            loadCalcMes();
        });
        $('#tabela-calc-mes').on('click', '.btn-pago-calc', function() { enviarPagoCalc(this); });
    });
})();
