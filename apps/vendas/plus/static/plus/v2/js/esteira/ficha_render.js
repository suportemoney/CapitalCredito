/**
 * Renderizadores de ficha por tipo de campanha (SIAPE / INSS / Outros).
 */
window.EsteiraFichaRender = (function () {
  'use strict';

  function esc(v) {
    if (v === null || v === undefined || v === '') return '—';
    return String(v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function moeda(v) {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    if (Number.isNaN(n)) return esc(v);
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  /** Saldo disponível na esteira = margem 35 (saldo_35). */
  function saldoDisponivel(margens) {
    return (margens || {}).saldo_35;
  }

  /** Total utilizado = util_35 + util_5 + util_beneficio_5 (ou parcelas dos débitos visíveis). */
  function totalUtilizado(margens, debitos) {
    const m = margens || {};
    const porMargem = numMargem(m.util_35) + numMargem(m.util_5) + numMargem(m.util_beneficio_5);
    if (porMargem > 0) return porMargem;
    const porDebitos = (debitos || []).reduce(function (s, d) {
      return s + numMargem(d.parcela);
    }, 0);
    if (porDebitos > 0) return porDebitos;
    return numMargem(m.total_util);
  }

  function numMargem(v) {
    if (v === null || v === undefined || v === '') return 0;
    const n = Number(v);
    return Number.isNaN(n) ? 0 : n;
  }

  function isContratoCartao(tipo) {
    if (!tipo) return false;
    const t = String(tipo).toLowerCase();
    return t.includes('cart') || t.includes('rmc');
  }

  /**
   * Regras SIAPE: 40% da renda (35% consignado + 5% cartão).
   * Cartão pode ser margem 5 e/ou benefício 5.
   */
  function analisarMargensSiape(margens, debitos) {
    const m = margens || {};
    const listaDebitos = debitos || [];

    const saldo35 = numMargem(saldoDisponivel(m));
    const util35 = numMargem(m.util_35);
    const util5 = numMargem(m.util_5);
    const utilBen5 = numMargem(m.util_beneficio_5);
    const bruta5 = numMargem(m.bruta_5);
    const brutaBen5 = numMargem(m.bruta_beneficio_5);
    const bruta35 = numMargem(m.bruta_35);
    const renda = numMargem(m.renda_bruta);

    const temMargem5 = bruta5 > 0 || util5 > 0 || numMargem(m.saldo_5) > 0;
    const temBen5 = brutaBen5 > 0 || utilBen5 > 0 || numMargem(m.saldo_beneficio_5) > 0;
    const doisCartoes = temMargem5 && temBen5;

    const utilCartoesCampos = util5 + utilBen5;
    const utilCartoesDeb = listaDebitos
      .filter(function (d) { return isContratoCartao(d.tipo_contrato); })
      .reduce(function (s, d) { return s + numMargem(d.parcela); }, 0);
    const utilCartoes = utilCartoesCampos > 0 ? utilCartoesCampos : utilCartoesDeb;

    const limite40 = renda > 0 ? renda * 0.4 : bruta35 + bruta5 + brutaBen5;
    const utilTotal = util35 + util5 + utilBen5;
    const negativado = limite40 > 0 && utilTotal > limite40 + 0.009;

    return {
      saldo35: saldo35,
      utilCartoes: utilCartoes,
      doisCartoes: doisCartoes,
      temMargem5: temMargem5,
      temBen5: temBen5,
      negativado: negativado,
      utilTotal: utilTotal,
      limite40: limite40,
      saldoCartao5: numMargem(m.saldo_5) + numMargem(m.saldo_beneficio_5),
    };
  }

  function insightsMargemSiape(margens, debitos) {
    const a = analisarMargensSiape(margens, debitos);
    const linhas = [];

    if (a.negativado) {
      linhas.push({
        icon: '⚠️',
        text: 'Cliente negativado: utilização (' + moeda(a.utilTotal) + ') acima de 40% da renda bruta (' + moeda(a.limite40) + ').',
      });
      return linhas;
    }

    if (a.saldo35 > a.utilCartoes && a.utilCartoes > 0 && a.doisCartoes) {
      linhas.push({
        icon: '✨',
        text: 'Saldo 35 (' + moeda(a.saldo35) + ') cobre os dois cartões utilizados (' + moeda(a.utilCartoes) +
          ') — oportunidade de portabilidade/refin para taxa menor.',
      });
    } else if (a.saldo35 > a.utilCartoes && a.utilCartoes > 0 && !a.doisCartoes) {
      linhas.push({
        icon: '✨',
        text: 'Saldo 35 (' + moeda(a.saldo35) + ') cobre o cartão utilizado (' + moeda(a.utilCartoes) +
          ') — oportunidade de trocar taxa alta por consignado.',
      });
    } else if (!a.doisCartoes && (a.temMargem5 || a.temBen5) && a.saldoCartao5 > 0) {
      linhas.push({
        icon: '💳',
        text: 'Possui apenas 1 margem de cartão — oportunidade de operação de cartão (saldo ' + moeda(a.saldoCartao5) + ').',
      });
    } else if (a.saldo35 > 0) {
      linhas.push({
        icon: '✨',
        text: 'Margem 35 com saldo — oportunidade de empréstimo consignado.',
      });
    } else if (a.saldoCartao5 > 0) {
      linhas.push({
        icon: '💳',
        text: 'Margem de cartão com saldo disponível (' + moeda(a.saldoCartao5) + ').',
      });
    }

    return linhas;
  }

  function dataBr(iso) {
    if (!iso) return '—';
    const p = iso.split('-');
    if (p.length !== 3) return esc(iso);
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function idade(iso) {
    if (!iso) return '';
    const n = new Date(iso);
    if (Number.isNaN(n.getTime())) return '';
    const hoje = new Date();
    let i = hoje.getFullYear() - n.getFullYear();
    const m = hoje.getMonth() - n.getMonth();
    if (m < 0 || (m === 0 && hoje.getDate() < n.getDate())) i -= 1;
    return i >= 0 ? ' (' + i + ' anos)' : '';
  }

  function iniciais(nome) {
    if (!nome) return '?';
    return nome.split(/\s+/).slice(0, 2).map(p => p[0]).join('').toUpperCase();
  }

  function badgeTipoContrato(tipo) {
    if (!tipo) return '—';
    const t = String(tipo).toLowerCase();
    const cls = t.includes('cart') ? 'ficha-badge--cartao' : 'ficha-badge--consignado';
    return '<span class="ficha-badge ' + cls + '">' + esc(tipo) + '</span>';
  }

  function renderSiape(ficha) {
    const p = ficha.pessoal || {};
    const m = ficha.margens || {};
    const debitos = ficha.debitos || [];

    let html = '<div class="ficha-siape">';

    const orgaoExibir = (debitos[0] && debitos[0].orgao) ? debitos[0].orgao : '—';

    html += '<div class="ficha-siape-topo">';
    html += '<div class="ficha-secao ficha-secao--pessoal">';
    html += '<h4 class="ficha-secao__titulo">Dados pessoais</h4>';
    html += '<div class="dados-pessoais-nome">' + esc(p.nome) + '<span class="dados-pessoais-check" aria-hidden="true">✓</span></div>';
    html += '<div class="dados-pessoais-corpo">';
    html += '<div class="dados-pessoais-grid">';
    html += dadoItem('CPF', formatCpf(p.cpf));
    html += dadoItem('Data de nascimento', dataBr(p.data_nascimento) + idade(p.data_nascimento));
    html += dadoItem('UF', p.uf);
    html += dadoItem('RJur', p.rjur);
    html += '</div>';
    html += '<div class="dados-pessoais-extra">';
    html += dadoItem('Situação funcional', p.situacao_funcional);
    html += dadoItem('Órgão', orgaoExibir);
    html += '</div>';
    html += '</div></div>';

    html += '<div class="ficha-secao ficha-secao--financeiro">';
    html += '<h4 class="ficha-secao__titulo">Resumo financeiro</h4>';
    html += '<div class="ficha-resumo-financeiro">';
    html += finCard('Renda bruta', moeda(m.renda_bruta), 'renda');
    html += finCard('Saldo 5', moeda(m.saldo_5), 'saldo5');
    html += finCard('Saldo benefício 5', moeda(m.saldo_beneficio_5), 'saldo-ben5');
    html += finCard('Saldo 35', moeda(m.saldo_35), 'saldo35');
    html += finCard('Total utilizado', moeda(totalUtilizado(m, debitos)), 'total-util');
    html += '</div></div>';
    html += '</div>';

    html += '<div class="ficha-secao"><h4 class="ficha-secao__titulo">Detalhamento de Margens</h4>';
    html += '<div class="ficha-margens-row">';
    html += margemCol('Margem 5', m.bruta_5, m.util_5, m.saldo_5);
    html += margemCol('Benefício 5', m.bruta_beneficio_5, m.util_beneficio_5, m.saldo_beneficio_5);
    html += margemCol('Margem 35', m.bruta_35, m.util_35, m.saldo_35);
    html += '</div></div>';

    html += '<div class="ficha-secao"><h4 class="ficha-secao__titulo">Débitos do Cliente</h4>';
    if (!debitos.length) {
      html += '<p class="ficha-vazia">Nenhum débito registrado.</p>';
    } else {
      html += '<div class="ficha-debitos-wrap"><table class="ficha-debitos-table"><thead><tr>';
      html += '<th>Matrícula</th><th>Banco</th><th>Órgão</th><th>Rubrica</th><th>Parcela</th>';
      html += '<th>Prazo rest.</th><th>Tipo contrato</th><th>Nº contrato</th><th>Status</th>';
      html += '</tr></thead><tbody>';
      debitos.forEach(function (d) {
        html += '<tr>';
        html += '<td>' + esc(d.matricula) + '</td>';
        html += '<td>' + esc(d.banco) + '</td>';
        html += '<td>' + esc(d.orgao) + '</td>';
        html += '<td>' + esc(d.rebrica) + '</td>';
        html += '<td>' + moeda(d.parcela) + '</td>';
        html += '<td>' + esc(d.prazo_restante) + '</td>';
        html += '<td>' + badgeTipoContrato(d.tipo_contrato) + '</td>';
        html += '<td>' + esc(d.num_contrato) + '</td>';
        html += '<td><span class="ficha-badge ficha-badge--ativo">Ativo</span></td>';
        html += '</tr>';
      });
      html += '</tbody></table></div>';
    }
    html += '</div>';

    if (ficha.telefones && ficha.telefones.length) {
      html += '<div class="ficha-secao ficha-telefones"><h4 class="ficha-secao__titulo">Telefones</h4><ul>';
      ficha.telefones.forEach(function (t) {
        html += '<li>' + esc(t.numero) + (t.principal ? ' (Principal)' : '') + '</li>';
      });
      html += '</ul></div>';
    }

    html += '</div>';
    return html;
  }

  function formatCpf(cpf) {
    if (!cpf) return '—';
    const d = String(cpf).replace(/\D/g, '');
    if (d.length !== 11) return esc(cpf);
    return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }

  function dadoItem(label, val) {
    return '<div class="dado-item"><label>' + esc(label) + '</label><strong>' +
      (typeof val === 'string' && val.includes('<') ? val : esc(val)) + '</strong></div>';
  }

  function finCard(label, valor, variant) {
    const cls = variant ? ' ficha-fin-card--' + variant : '';
    return '<div class="ficha-fin-card' + cls + '"><span>' + esc(label) + '</span><strong>' + valor + '</strong></div>';
  }

  function margemCol(titulo, bruta, util, saldo) {
    return '<div class="ficha-margem-col"><h5>' + esc(titulo) + '</h5>' +
      linhaMargem('Bruta', moeda(bruta)) +
      linhaMargem('Utilizada', moeda(util)) +
      linhaMargem('Saldo', moeda(saldo)) +
      '</div>';
  }

  function linhaMargem(label, val) {
    return '<div class="ficha-margem-linha"><span>' + label + '</span><strong>' + val + '</strong></div>';
  }

  function renderInss(ficha) {
    const p = ficha.pessoal || {};
    const ag = ficha.ultimo_agendamento;
    const pr = ficha.ultima_presenca;

    let html = '<div class="ficha-inss">';
    html += '<div class="ficha-inss-header">';
    html += '<div class="ficha-inss-avatar">' + iniciais(p.nome_completo) + '</div>';
    html += '<div><h3 class="ficha-inss-nome">' + esc(p.nome_completo) + '</h3>';
    html += '<div class="ficha-inss-cpf">CPF: ' + esc(p.cpf) + '</div></div></div>';

    html += '<div class="ficha-inss-grid">';

    html += '<div class="ficha-inss-card ficha-inss-card--destaque"><h4>Contato</h4>';
    html += linhaInss('Telefone', p.numero);
    html += linhaInss('WhatsApp', p.flg_whatsapp ? 'Sim' : 'Não');
    html += linhaInss('Status cadastro', p.status_ativo ? 'Ativo' : 'Inativo');
    if (p.flg_whatsapp) {
      html += '<span class="ficha-inss-tag ficha-inss-tag--wa">WhatsApp disponível</span>';
    }
    html += '</div>';

    html += '<div class="ficha-inss-card"><h4>Último agendamento</h4>';
    if (ag) {
      html += linhaInss('Data', dataBr(ag.data));
      html += linhaInss('Loja', ag.loja);
      html += linhaInss('Tabulação', ag.tabulacao_atendente);
    } else {
      html += '<p class="ficha-vazia">Sem agendamento registrado.</p>';
    }
    html += '</div>';

    html += '<div class="ficha-inss-card"><h4>Última presença em loja</h4>';
    if (pr) {
      html += linhaInss('Data', dataBr(pr.data));
      html += linhaInss('Loja', pr.loja);
      html += linhaInss('Tabulação venda', pr.tabulacao_venda);
    } else {
      html += '<p class="ficha-vazia">Sem presença registrada.</p>';
    }
    html += '</div>';

    html += '<div class="ficha-inss-card"><h4>Resumo INSS</h4>';
    html += '<p style="margin:0;font-size:13px;color:#64748b;">Cliente vinculado à base INSS (agendamentos e presença em loja).</p>';
    if (ag && !pr) {
      html += '<span class="ficha-inss-tag" style="margin-top:8px;">Agendado — aguardando presença</span>';
    }
    html += '</div>';

    html += '</div></div>';
    return html;
  }

  function linhaInss(label, val) {
    return '<div class="ficha-inss-linha"><span>' + esc(label) + '</span><strong>' + esc(val) + '</strong></div>';
  }

  function renderOutros(ficha) {
    const campos = ficha.campos || {};
    const keys = Object.keys(campos);

    let html = '<div class="ficha-outros">';
    html += '<p class="ficha-outros-intro">Ficha genérica — dados importados via CSV/JSON.</p>';

    if (!keys.length) {
      html += '<p class="ficha-vazia">Nenhum campo disponível.</p>';
    } else {
      html += '<div class="ficha-outros-grid">';
      keys.forEach(function (k) {
        html += '<div class="ficha-outros-campo"><label>' + esc(k) + '</label><span>' + esc(campos[k]) + '</span></div>';
      });
      html += '</div>';
    }
    html += '</div>';
    return html;
  }

  function render(ficha, tipo) {
    if (!ficha || !ficha.encontrado) {
      return '<p class="ficha-vazia">Cliente não encontrado na base ' + esc(tipo) + '.</p>';
    }
    if (tipo === 'SIAPE' || ficha.schema === 'fixo_siape') return renderSiape(ficha);
    if (tipo === 'INSS' || ficha.schema === 'fixo_inss') return renderInss(ficha);
    return renderOutros(ficha);
  }

  function buildInsights(ficha, tipo, cliente) {
    const items = [];
    if (!ficha || !ficha.encontrado) {
      return ['Selecione um cliente para ver insights.'];
    }

    if (tipo === 'SIAPE') {
      const m = ficha.margens || {};
      const saldoDisp = saldoDisponivel(m);
      if (saldoDisp !== null && saldoDisp !== undefined && saldoDisp !== '') {
        items.push({ icon: '💰', text: 'Saldo disponível: ' + moeda(saldoDisp) });
      }
      const deb = (ficha.debitos || []).length;
      items.push({ icon: '📋', text: deb + ' contrato(s) ativo(s) na base.' });
      insightsMargemSiape(m, ficha.debitos).forEach(function (linha) {
        items.push(linha);
      });
    } else if (tipo === 'INSS') {
      const p = ficha.pessoal || {};
      if (p.flg_whatsapp) {
        items.push({ icon: '📱', text: 'Cliente com WhatsApp cadastrado.' });
      }
      if (ficha.ultimo_agendamento && !ficha.ultima_presenca) {
        items.push({ icon: '📅', text: 'Agendamento sem presença — retornar contato.' });
      }
      if (ficha.ultima_presenca) {
        items.push({ icon: '🏪', text: 'Última visita: ' + dataBr(ficha.ultima_presenca.data) });
      }
    } else {
      const n = Object.keys(ficha.campos || {}).length;
      items.push({ icon: '📄', text: n + ' campo(s) importados na ficha.' });
    }

    if (cliente && cliente.cpf) {
      items.push({ icon: '🔑', text: 'CPF campanha: ' + esc(cliente.cpf) });
    }

    return items.length ? items : [{ icon: 'ℹ️', text: 'Sem insights adicionais.' }];
  }

  return {
    render: render,
    buildInsights: buildInsights,
    esc: esc,
  };
})();
