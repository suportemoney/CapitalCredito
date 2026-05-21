$(document).ready(function() {
    carregarRanking();
});

function carregarRanking() {
    $.ajax({
        url: '/api/ranking/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                exibirRanking(response.data);
            } else {
                const podium = $('#podium-container');
                podium.html(`<div class="podium-placeholder text-center"><p class="text-danger">${response.message || 'Erro desconhecido'}</p></div>`);
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON || {};
            const podium = $('#podium-container');
            podium.html(`<div class="podium-placeholder text-center"><p class="text-danger">Erro ao carregar ranking: ${response.message || 'Erro desconhecido'}</p></div>`);
        }
    });
}

function exibirRanking(data) {
    const percentual = data.percentual_meta.toFixed(2);
    const valorAlcancado = formatarMoeda(data.valor_total_geral);
    const valorMeta = formatarMoeda(data.meta.valor_meta);
    
    $('#valor-percentual-meta').text(valorAlcancado);
    $('#percentual-meta').text(percentual + '%');
    $('#valor-total-meta').text(valorMeta);
    $('#cards-meta').show();
    
    const podium = $('#podium-container');
    podium.empty();
    
    if (data.ranking.length === 0) {
        podium.append('<div class="podium-placeholder text-center"><p class="text-muted">Nenhum vendedor encontrado no período</p></div>');
        return;
    }
    
    const podiumHtml = `
        <div class="podium-row">
            ${gerarPodiumCard(data.ranking[4], 5)}
            ${gerarPodiumCard(data.ranking[2], 3)}
            ${gerarPodiumCard(data.ranking[0], 1)}
            ${gerarPodiumCard(data.ranking[1], 2)}
            ${gerarPodiumCard(data.ranking[3], 4)}
        </div>
    `;
    
    podium.append(podiumHtml);
}

function gerarPodiumCard(vendedor, posicao) {
    if (!vendedor) {
        return `<div class="podium-card podium-empty podium-pos-${posicao}">
            <div class="podium-photo-container">
                <div class="podium-photo-placeholder">
                    <span>${posicao}º</span>
                </div>
            </div>
            <div class="podium-medal">
                <span class="podium-number">${posicao}º</span>
            </div>
            <div class="podium-info">
                <h5 class="podium-name">-</h5>
                <p class="podium-value">-</p>
            </div>
        </div>`;
    }
    
    const medalClass = posicao === 1 ? 'gold' : posicao === 2 ? 'silver' : posicao === 3 ? 'bronze' : '';
    const valorFormatado = formatarMoeda(vendedor.valor_total);
    
    let fotoHtml = '';
    if (vendedor.funcionario_foto) {
        const inicial = vendedor.funcionario_nome ? vendedor.funcionario_nome.charAt(0).toUpperCase() : vendedor.username.charAt(0).toUpperCase();
        fotoHtml = `<img src="${vendedor.funcionario_foto}" alt="${escapeHtml(vendedor.funcionario_nome)}" class="podium-photo" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'podium-photo-placeholder\\'>${inicial}</div>'">`;
    } else {
        const inicial = vendedor.funcionario_nome ? vendedor.funcionario_nome.charAt(0).toUpperCase() : vendedor.username.charAt(0).toUpperCase();
        fotoHtml = `<div class="podium-photo-placeholder">${inicial}</div>`;
    }
    
    return `
        <div class="podium-card podium-pos-${posicao}">
            <div class="podium-photo-container">
                ${fotoHtml}
            </div>
            <div class="podium-medal ${medalClass}">
                <span class="podium-number">${posicao}º</span>
            </div>
            <div class="podium-info">
                <h5 class="podium-name">${escapeHtml(vendedor.funcionario_nome)}</h5>
                <p class="podium-value">${valorFormatado}</p>
            </div>
        </div>
    `;
}

function formatarMoeda(valor) {
    if (!valor || valor === 0) return 'R$ 0,00';
    return 'R$ ' + parseFloat(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatarData(dataString) {
    if (!dataString) return '-';
    const [ano, mes, dia] = dataString.split('-');
    return `${dia}/${mes}/${ano}`;
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

