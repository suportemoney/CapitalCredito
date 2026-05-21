(function() {
    var base = (window.FINANCEIRO_GERAL_BASE || '').replace(/\/?$/, '') + '/';
    var urlDashboard = base + 'api/dashboard/';
    function formatarMoeda(v) {
        return 'R$ ' + (typeof v === 'number' ? v.toFixed(2) : parseFloat(v || 0).toFixed(2)).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }
    function carregar() {
        $.get(urlDashboard).done(function(r) {
            if (r.success && r.result) {
                $('#total-a-pagar').text(formatarMoeda(r.result.total_a_pagar));
                $('#total-a-receber').text(formatarMoeda(r.result.total_a_receber));
            }
        }).fail(function() {
            $('#total-a-pagar').text('R$ 0,00');
            $('#total-a-receber').text('R$ 0,00');
        });
    }
    $(document).ready(carregar);
})();
