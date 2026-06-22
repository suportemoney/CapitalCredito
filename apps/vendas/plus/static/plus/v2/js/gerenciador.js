(function () {
  'use strict';

  const root = document.getElementById('gerenciador-root');
  if (!root) return;

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  const TAB_TIPO = { siape: 'SIAPE', outros: 'OUTROS' };
  const DONUT_CORES = { SIAPE: '#D4AF37', OUTROS: '#6366f1', MISTA: '#94a3b8' };

  let tabAtual = 'siape';
  let campanhasCache = [];
  let clientesCache = [];
  let campanhaSelecionadaId = null;
  let arquivoOutros = null;
  let arquivoSiape = null;
  let cpfsPreviewSiape = [];
  let equipesCache = [];
  let filtrosEquipe = null;
  let participantesSelecionados = new Set();
  let equipeSelecionada = null;
  let equipeEmEdicao = null;

  /* --- Util --- */
  function postJson(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(body),
    }).then(r => r.json());
  }

  function postArquivo(url, arquivo) {
    const fd = new FormData();
    fd.append('arquivo', arquivo);
    return fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: fd })
      .then(async response => {
        const contentType = response.headers.get('content-type') || '';
        const text = await response.text();
        if (!response.ok) {
          let erro = 'Erro HTTP ' + response.status;
          if (contentType.includes('application/json')) {
            try { erro = JSON.parse(text).erro || erro; } catch (_) { /* resposta não JSON */ }
          } else if (response.status === 504) {
            erro = 'Tempo esgotado no servidor. Aguarde ou tente novamente.';
          }
          return { ok: false, erro: erro };
        }
        try {
          return JSON.parse(text);
        } catch (_) {
          return { ok: false, erro: 'Resposta inválida do servidor.' };
        }
      });
  }

  let sseReaderAtivo = null;

  function htmlProgressoSSE(titulo) {
    return '<div class="ger-preview-progress">' +
      '<p>' + titulo + '</p>' +
      '<div class="ger-progress-bar"><span style="width:0%"></span></div>' +
      '<p class="ger-preview-progress__meta">Aguardando início…</p>' +
      '</div>';
  }

  async function processarStreamSSE(response, el, handlers) {
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('text/event-stream') || !response.body) {
      const data = await response.json();
      if (handlers.onComplete && data.ok !== false) handlers.onComplete(data, el);
      else if (handlers.onError) handlers.onError(data, el);
      return;
    }

    const reader = response.body.getReader();
    sseReaderAtivo = reader;
    const decoder = new TextDecoder();
    let buffer = '';
    let bar = el.querySelector('.ger-progress-bar span');
    let meta = el.querySelector('.ger-preview-progress__meta');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;
        let eventType = 'message';
        let data = null;
        for (const line of block.split('\n')) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim();
          else if (line.startsWith('data: ')) {
            try { data = JSON.parse(line.slice(6)); } catch (_) { /* linha SSE inválida */ }
          }
        }
        if (!data) continue;

        if (eventType === 'start' && handlers.onStart) {
          handlers.onStart(data, el, meta);
          bar = el.querySelector('.ger-progress-bar span');
          meta = el.querySelector('.ger-preview-progress__meta');
        } else if (eventType === 'progress' && handlers.onProgress) {
          handlers.onProgress(data, el, bar, meta);
        } else if (eventType === 'complete' && handlers.onComplete) {
          handlers.onComplete(data, el);
        } else if (eventType === 'error' && handlers.onError) {
          handlers.onError(data, el);
        }
      }
    }
  }

  async function executarSSE(requestInit, el, handlers, botoes, tituloProgresso) {
    if (sseReaderAtivo) {
      try { await sseReaderAtivo.cancel(); } catch (_) { /* stream anterior cancelado */ }
      sseReaderAtivo = null;
    }

    const btns = (botoes || []).filter(Boolean);
    btns.forEach(btn => { btn.disabled = true; });
    el.innerHTML = htmlProgressoSSE(tituloProgresso || 'Processando…');

    try {
      const response = await fetch(requestInit.url, requestInit);
      if (!response.ok) {
        const text = await response.text();
        let erro = 'Erro HTTP ' + response.status;
        const ct = response.headers.get('content-type') || '';
        if (ct.includes('application/json')) {
          try { erro = JSON.parse(text).erro || erro; } catch (_) { /* resposta não JSON */ }
        } else if (response.status === 504) {
          erro = 'Tempo esgotado no gateway. O processamento continua em streaming — aguarde ou tente novamente.';
        }
        if (handlers.onError) handlers.onError({ erro: erro }, el);
        else el.innerHTML = '<p class="ger-erro">' + erro + '</p>';
        return;
      }
      await processarStreamSSE(response, el, handlers);
    } catch (err) {
      if (handlers.onError) handlers.onError({ erro: err.message }, el);
      else el.innerHTML = '<p class="ger-erro">' + (err.message || 'Falha na conexão.') + '</p>';
    } finally {
      if (!handlers.manterBotoesDesabilitados) {
        btns.forEach(btn => { btn.disabled = false; });
      }
      sseReaderAtivo = null;
    }
  }

  async function postArquivoPreviewSSE(url, arquivo, el, renderFn, btnPreview, btnConfirm) {
    await executarSSE(
      {
        url: url,
        method: 'POST',
        headers: { 'X-CSRFToken': csrf },
        body: (() => { const fd = new FormData(); fd.append('arquivo', arquivo); return fd; })(),
      },
      el,
      {
        onStart(data, _el, meta) {
          if (meta) {
            meta.textContent = '0 / ' + data.total + ' CPFs' +
              (data.invalidos_csv ? ' (' + data.invalidos_csv + ' inválidos no CSV)' : '');
          }
        },
        onProgress(data, _el, bar, meta) {
          const pct = data.total ? Math.round((data.processados / data.total) * 100) : 0;
          if (bar) bar.style.width = pct + '%';
          if (meta) {
            meta.textContent = data.processados + ' / ' + data.total + ' CPFs · OK: ' +
              data.encontrados + ' · Faltando: ' + data.nao_encontrados;
          }
        },
        onComplete(data, target) { renderFn(target, data); },
        onError(data, target) {
          target.innerHTML = '<p class="ger-erro">' + (data.erro || 'Erro no preview.') + '</p>';
        },
      },
      [btnPreview, btnConfirm],
      'Analisando CSV…'
    );
  }

  function renderCriarSucesso(el, data, modalId, tipoLabel) {
    el.innerHTML =
      '<div class="ger-preview-success">' +
      '<i class="ph ph-check-circle"></i>' +
      '<div>' +
      '<p><strong>Campanha ' + tipoLabel + ' criada com sucesso!</strong></p>' +
      '<p>' + (data.nome || 'Campanha') + ' — ' + (data.criados ?? 0) +
      ' clientes vinculados de ' + (data.total_cpfs ?? 0) + ' CPFs.</p>' +
      '<p class="ger-preview-success__hint">Atualizando painel…</p>' +
      '</div></div>';
    setTimeout(() => {
      fecharModal(modalId);
      carregarDashboard();
    }, 2200);
  }

  async function postCriarCampanhaSSE(url, payload, el, modalId, tipoLabel, btnCriar, btnPreview) {
    await executarSSE(
      {
        url: url,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify(payload),
      },
      el,
      {
        manterBotoesDesabilitados: true,
        onStart(data, _el, meta) {
          if (meta) meta.textContent = '0 / ' + data.total + ' CPFs · Criando campanha…';
        },
        onProgress(data, _el, bar, meta) {
          const pct = data.total ? Math.round((data.processados / data.total) * 100) : 0;
          if (bar) bar.style.width = pct + '%';
          if (meta) {
            meta.textContent = 'Vinculando clientes: ' + data.processados + ' / ' + data.total + ' CPFs';
          }
        },
        onComplete(data, target) {
          renderCriarSucesso(target, data, modalId, tipoLabel);
        },
        onError(data, target) {
          target.innerHTML = '<p class="ger-erro">' + (data.erro || 'Erro ao criar campanha.') + '</p>';
          if (btnCriar) btnCriar.disabled = false;
          if (btnPreview) btnPreview.disabled = false;
        },
      },
      [btnCriar, btnPreview],
      'Enviando campanha…'
    );
  }

  function abrirModal(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = false;
  }

  function fecharModal(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  }

  function formatCpf(cpf) {
    if (!cpf) return '—';
    const d = String(cpf).replace(/\D/g, '');
    if (d.length !== 11) return cpf;
    return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }

  function formatData(iso) {
    if (!iso) return '—';
    const p = iso.split('T')[0].split('-');
    if (p.length !== 3) return iso;
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function formatDataHora(iso) {
    if (!iso) return '—';
    const [d, t] = iso.split('T');
    return formatData(d) + (t ? ' ' + t.slice(0, 5) : '');
  }

  function badgeTipo(tipo) {
    const slug = (tipo || '').toLowerCase();
    return `<span class="ger-badge ger-badge--${slug}">${tipo || '—'}</span>`;
  }

  function badgeStatus(ativo) {
    return ativo
      ? '<span class="ger-badge ger-badge--success">Ativa</span>'
      : '<span class="ger-badge ger-badge--danger">Inativa</span>';
  }

  function statusToggleHtml(c) {
    const ativo = !!c.status;
    const cls = ativo ? 'is-active' : 'is-inactive';
    const label = ativo ? 'Ativa' : 'Inativa';
    return `<button type="button" class="ger-status-toggle ${cls} btn-toggle-status-campanha" ` +
      `data-id="${c.id}" data-status="${ativo ? '1' : '0'}" aria-pressed="${ativo}" title="Clique para alternar">` +
      `<span class="ger-status-toggle__track"><span class="ger-status-toggle__knob"></span></span>` +
      `<span class="ger-status-toggle__label">${label}</span>` +
      `</button>`;
  }

  function tipoAtual() {
    return TAB_TIPO[tabAtual] || 'SIAPE';
  }

  document.querySelectorAll('[data-fechar-modal]').forEach(btn => {
    btn.addEventListener('click', () => fecharModal(btn.dataset.fecharModal));
  });
  document.querySelectorAll('.ger-modal').forEach(modal => {
    modal.addEventListener('click', e => { if (e.target === modal) fecharModal(modal.id); });
  });

  /* --- Tabs --- */
  function trocarTab(tab) {
    tabAtual = tab;
    document.querySelectorAll('.ger-tabs__btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    const isEquipes = tab === 'equipes';
    document.getElementById('panel-produto').hidden = isEquipes;
    document.getElementById('panel-equipes').hidden = !isEquipes;
    if (isEquipes) {
      carregarEquipesTabela();
    } else {
      carregarDashboard();
    }
  }

  document.querySelectorAll('.ger-tabs__btn').forEach(btn => {
    btn.addEventListener('click', () => trocarTab(btn.dataset.tab));
  });

  /* --- KPIs --- */
  function carregarKpis() {
    fetch(root.dataset.urlKpis + '?tipo=' + encodeURIComponent(tipoAtual()))
      .then(r => r.json())
      .then(data => {
        if (!data.ok) return;
        const k = data.kpis;
        document.getElementById('kpi-campanhas-ativas').textContent = k.campanhas_ativas;
        document.getElementById('kpi-campanhas-total').textContent = k.campanhas_ativas + ' de ' + k.campanhas_total + ' no total';
        document.getElementById('kpi-clientes').textContent = k.clientes_vinculados.toLocaleString('pt-BR');
        document.getElementById('kpi-equipes').textContent = k.equipes_vinculadas;
        document.getElementById('kpi-agendamentos').textContent = k.agendamentos_pendentes;
        document.getElementById('kpi-importacoes').textContent = k.importacoes_recentes;
      });
  }

  /* --- Campanhas --- */
  function campanhasFiltradas() {
    const busca = (document.getElementById('filtro-busca-campanha').value || '').toLowerCase();
    const st = document.getElementById('filtro-status-campanha').value;
    return campanhasCache.filter(c => {
      if (busca && !c.nome.toLowerCase().includes(busca)) return false;
      if (st === '1' && !c.status) return false;
      if (st === '0' && c.status) return false;
      return true;
    });
  }

  function renderTabelaCampanhas() {
    const lista = campanhasFiltradas();
    const tbody = document.querySelector('#tabela-campanhas tbody');
    if (!lista.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="color:#64748b;font-style:italic">Nenhuma campanha encontrada.</td></tr>';
      return;
    }
    tbody.innerHTML = lista.map(c =>
      `<tr data-id="${c.id}" class="${campanhaSelecionadaId === c.id ? 'is-selected' : ''}">` +
      `<td><strong>${c.nome}</strong></td>` +
      `<td>${badgeTipo(c.tipo_campanha)}</td>` +
      `<td>${statusToggleHtml(c)}</td>` +
      `<td>${(c.equipes_nomes || []).join(', ') || '—'}</td>` +
      `<td>${formatData(c.data_criacao)}</td>` +
      `<td>${c.clientes_count}</td>` +
      `<td><div class="ger-table-actions">` +
      `<button type="button" class="ger-btn ger-btn--sm ger-btn--ghost btn-ver-campanha" data-id="${c.id}">Ver</button>` +
      `<button type="button" class="ger-btn ger-btn--sm ger-btn--ghost btn-editar-campanha" data-id="${c.id}">Editar</button>` +
      `</div></td>` +
      `</tr>`
    ).join('');

    tbody.querySelectorAll('tr[data-id]').forEach(row => {
      row.addEventListener('click', e => {
        if (e.target.closest('.btn-ver-campanha, .btn-editar-campanha, .btn-toggle-status-campanha')) return;
        selecionarCampanha(parseInt(row.dataset.id, 10));
      });
    });
    tbody.querySelectorAll('.btn-ver-campanha').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        selecionarCampanha(parseInt(btn.dataset.id, 10));
      });
    });
    tbody.querySelectorAll('.btn-editar-campanha').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        abrirModalEditarCampanha(parseInt(btn.dataset.id, 10));
      });
    });
    tbody.querySelectorAll('.btn-toggle-status-campanha').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        alternarStatusCampanha(parseInt(btn.dataset.id, 10), btn);
      });
    });

    preencherSelectOutros(lista);
  }

  function preencherSelectOutros(campanhas) {
    const sel = document.getElementById('outros-select-campanha');
    if (!sel) return;
    const val = sel.value;
    sel.innerHTML = '<option value="">Criar nova campanha OUTROS</option>';
    campanhas.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id;
      o.textContent = c.nome;
      sel.appendChild(o);
    });
    if (val) sel.value = val;
  }

  function carregarCampanhas() {
    return fetch(root.dataset.urlCampanhas + '?tipo=' + encodeURIComponent(tipoAtual()))
      .then(r => r.json())
      .then(data => {
        campanhasCache = data.campanhas || [];
        renderTabelaCampanhas();
        if (campanhaSelecionadaId && !campanhasCache.find(c => c.id === campanhaSelecionadaId)) {
          campanhaSelecionadaId = null;
          limparDetalhes();
        }
      });
  }

  function alternarStatusCampanha(id, btn) {
    const camp = campanhasCache.find(c => c.id === id);
    if (!camp || btn?.disabled) return;
    const novo = !camp.status;
    if (btn) {
      btn.disabled = true;
      btn.classList.add('is-loading');
    }
    postJson(root.dataset.urlCampanhaStatus, { campanha_id: id, status: novo })
      .then(data => {
        if (data.ok) {
          camp.status = novo;
          renderTabelaCampanhas();
          if (campanhaSelecionadaId === id) {
            carregarKpis();
            carregarDetalhe(id);
          }
        } else {
          alert(data.erro || 'Erro ao alterar status.');
        }
      })
      .finally(() => {
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('is-loading');
        }
      });
  }

  function preencherSelectEquipesEditar(selecionadas) {
    const sel = document.getElementById('editar-campanha-equipes');
    if (!sel) return;
    const ids = new Set((selecionadas || []).map(Number));
    sel.innerHTML = equipesCache.map(e =>
      `<option value="${e.id}"${ids.has(e.id) ? ' selected' : ''}>${e.nome}</option>`
    ).join('');
  }

  function abrirModalEditarCampanha(id) {
    const camp = campanhasCache.find(c => c.id === id);
    if (!camp) return;
    document.getElementById('editar-campanha-id').value = camp.id;
    document.getElementById('editar-campanha-nome').value = camp.nome || '';
    document.getElementById('editar-campanha-descricao').value = camp.descricao || '';
    carregarEquipes().then(() => {
      preencherSelectEquipesEditar(camp.equipes || []);
      abrirModal('modal-editar-campanha');
    });
  }

  function selecionarCampanha(id) {
    campanhaSelecionadaId = id;
    renderTabelaCampanhas();
    document.getElementById('btn-acao-toggle-status').disabled = false;
    document.getElementById('btn-acao-atualizar-detalhe').disabled = false;
    const camp = campanhasCache.find(c => c.id === id);
    document.getElementById('clientes-campanha-nome').textContent = camp ? camp.nome : '';
    carregarDetalhe(id);
    carregarClientes(id);
    carregarImportacao(id);
    carregarAgendamentos(id);
  }

  function limparDetalhes() {
    document.getElementById('detalhes-vazio').hidden = false;
    document.getElementById('detalhes-conteudo').hidden = true;
    document.getElementById('det-status-badge').hidden = true;
    document.getElementById('btn-acao-toggle-status').disabled = true;
    document.getElementById('btn-acao-atualizar-detalhe').disabled = true;
    document.getElementById('clientes-campanha-nome').textContent = 'Selecione uma campanha';
    document.querySelector('#tabela-clientes-campanha tbody').innerHTML = '';
    document.getElementById('import-vazio').hidden = false;
    document.getElementById('import-conteudo').hidden = true;
    document.getElementById('lista-agendamentos').innerHTML = '<li class="ger-agenda-empty">Selecione uma campanha.</li>';
  }

  /* --- Detalhes --- */
  function renderDonut(porTipo) {
    const entries = Object.entries(porTipo || {});
    const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
    let acc = 0;
    const parts = entries.map(([tipo, val]) => {
      const deg = (val / total) * 360;
      const cor = DONUT_CORES[tipo] || '#94a3b8';
      const slice = `${cor} ${acc}deg ${acc + deg}deg`;
      acc += deg;
      return slice;
    });
    document.getElementById('det-donut').style.background = parts.length
      ? `conic-gradient(${parts.join(', ')})`
      : 'conic-gradient(#e2e8f0 0deg 360deg)';
    document.getElementById('det-donut-legend').innerHTML = entries.map(([tipo, val]) =>
      `<li><span style="background:${DONUT_CORES[tipo] || '#94a3b8'}"></span>${tipo}: ${val}</li>`
    ).join('') || '<li>Sem dados</li>';
  }

  function renderProgressControles(ctrl) {
    const max = Math.max(ctrl.em_atendimento, ctrl.sem_tabulacao, ctrl.com_agendamento, ctrl.com_tabulacao, 1);
    const itens = [
      { label: 'Em atendimento', val: ctrl.em_atendimento, cor: '#2563eb' },
      { label: 'Sem tabulação', val: ctrl.sem_tabulacao, cor: '#d97706' },
      { label: 'Com agendamento', val: ctrl.com_agendamento, cor: '#0891b2' },
      { label: 'Tabulados', val: ctrl.com_tabulacao, cor: '#16a34a' },
    ];
    document.getElementById('det-progress-controles').innerHTML = itens.map(it =>
      `<div class="ger-progress-item">` +
      `<label><span>${it.label}</span><strong>${it.val}</strong></label>` +
      `<div class="ger-progress-bar"><span style="width:${(it.val / max) * 100}%;background:${it.cor}"></span></div>` +
      `</div>`
    ).join('');
  }

  function carregarDetalhe(id) {
    fetch(root.dataset.urlDetalhe + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        if (!data.ok) return;
        const d = data.detalhe;
        document.getElementById('detalhes-vazio').hidden = true;
        document.getElementById('detalhes-conteudo').hidden = false;
        document.getElementById('det-nome').textContent = d.nome;
        document.getElementById('det-descricao').textContent = d.descricao;
        document.getElementById('det-tipo').textContent = d.tipo_campanha;
        document.getElementById('det-criacao').textContent = formatData(d.data_criacao);
        document.getElementById('det-equipes').textContent = (d.equipes_nomes || []).join(', ') || '—';
        document.getElementById('det-clientes-total').textContent = d.clientes_total;
        const badge = document.getElementById('det-status-badge');
        badge.hidden = false;
        badge.textContent = d.status ? 'Ativa' : 'Inativa';
        badge.className = 'ger-badge ' + (d.status ? 'ger-badge--success' : 'ger-badge--danger');
        renderDonut(d.clientes_por_tipo);
        renderProgressControles(d.controles);
      });
  }

  /* --- Clientes --- */
  function clientesFiltrados() {
    const busca = (document.getElementById('filtro-busca-cliente').value || '').toLowerCase();
    if (!busca) return clientesCache;
    return clientesCache.filter(c =>
      c.cpf.includes(busca.replace(/\D/g, '')) ||
      (c.nome && c.nome.toLowerCase().includes(busca))
    );
  }

  function renderClientes() {
    const tbody = document.querySelector('#tabela-clientes-campanha tbody');
    const lista = clientesFiltrados();
    if (!lista.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="color:#64748b;font-style:italic">Nenhum cliente.</td></tr>';
      return;
    }
    tbody.innerHTML = lista.map(c => {
      const tabBadge = c.tabulacao !== '—'
        ? `<span class="ger-badge ger-badge--muted">${c.tabulacao}</span>`
        : '<span class="ger-badge ger-badge--warning">Pendente</span>';
      return `<tr>` +
        `<td>${formatCpf(c.cpf)}</td>` +
        `<td>${c.nome || '—'}</td>` +
        `<td>${badgeTipo(c.tipo)}</td>` +
        `<td>${c.usuario}</td>` +
        `<td>${tabBadge}</td>` +
        `<td>${c.status_ativo ? badgeStatus(true).replace('Ativa', 'Ativo') : badgeStatus(false).replace('Inativa', 'Inativo')}</td>` +
        `<td>${formatDataHora(c.ultima_atualizacao)}</td>` +
        `</tr>`;
    }).join('');
  }

  function carregarClientes(id) {
    fetch(root.dataset.urlClientes + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        clientesCache = data.clientes || [];
        renderClientes();
      });
  }

  /* --- Importação / Agendamentos --- */
  function carregarImportacao(id) {
    fetch(root.dataset.urlImportacao + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        const imp = data.importacao;
        if (!imp) {
          document.getElementById('import-vazio').hidden = false;
          document.getElementById('import-conteudo').hidden = true;
          return;
        }
        document.getElementById('import-vazio').hidden = true;
        document.getElementById('import-conteudo').hidden = false;
        document.getElementById('imp-arquivo').textContent = imp.arquivo_nome;
        document.getElementById('imp-linhas').textContent = imp.total_linhas + ' linhas importadas';
        document.getElementById('imp-colunas').textContent = (imp.colunas || []).join(', ') || '—';
        document.getElementById('imp-criador').textContent = imp.criado_por;
        document.getElementById('imp-data').textContent = formatDataHora(imp.data_criacao);
      });
  }

  function carregarAgendamentos(id) {
    fetch(root.dataset.urlAgendamentos + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        const ul = document.getElementById('lista-agendamentos');
        const lista = data.agendamentos || [];
        if (!lista.length) {
          ul.innerHTML = '<li class="ger-agenda-empty">Nenhum agendamento pendente.</li>';
          return;
        }
        ul.innerHTML = lista.map(a => {
          const p = a.dia.split('-');
          const dia = p[2];
          const mes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][parseInt(p[1], 10) - 1];
          return `<li class="ger-agenda-item">` +
            `<div class="ger-agenda-date"><strong>${dia}</strong><small>${mes}</small></div>` +
            `<div class="ger-agenda-info">` +
            `<strong>${a.hora} — ${a.nome || formatCpf(a.cpf)}</strong>` +
            `<span>${a.responsavel}${a.observacao ? ' · ' + a.observacao : ''}</span>` +
            `</div>` +
            `<span class="ger-badge ger-badge--warning">Em espera</span>` +
            `</li>`;
        }).join('');
      });
  }

  function carregarDashboard() {
    carregarKpis();
    carregarCampanhas().then(() => {
      if (campanhaSelecionadaId) selecionarCampanha(campanhaSelecionadaId);
    });
  }

  /* --- Ações rápidas --- */
  document.getElementById('btn-acao-nova-campanha').addEventListener('click', () => {
    const map = { siape: 'modal-siape', outros: 'modal-outros' };
    abrirModal(map[tabAtual] || 'modal-siape');
  });

  document.getElementById('btn-acao-importar').addEventListener('click', () => {
    abrirModal(tabAtual === 'outros' ? 'modal-outros' : 'modal-siape');
  });

  document.getElementById('btn-acao-equipe').addEventListener('click', () => trocarTab('equipes'));

  document.getElementById('btn-acao-toggle-status').addEventListener('click', () => {
    if (!campanhaSelecionadaId) return;
    const camp = campanhasCache.find(c => c.id === campanhaSelecionadaId);
    if (!camp) return;
    const novo = !camp.status;
    if (!confirm((novo ? 'Ativar' : 'Inativar') + ' esta campanha?')) return;
    postJson(root.dataset.urlCampanhaStatus, { campanha_id: campanhaSelecionadaId, status: novo })
      .then(data => {
        if (data.ok) {
          carregarDashboard();
          selecionarCampanha(campanhaSelecionadaId);
        } else {
          alert(data.erro || 'Erro ao alterar status.');
        }
      });
  });

  document.getElementById('btn-acao-atualizar-detalhe').addEventListener('click', () => {
    if (campanhaSelecionadaId) selecionarCampanha(campanhaSelecionadaId);
  });

  document.getElementById('btn-limpar-filtros').addEventListener('click', () => {
    document.getElementById('filtro-busca-campanha').value = '';
    document.getElementById('filtro-status-campanha').value = '';
    renderTabelaCampanhas();
  });

  document.getElementById('filtro-busca-campanha').addEventListener('input', renderTabelaCampanhas);
  document.getElementById('filtro-status-campanha').addEventListener('change', renderTabelaCampanhas);
  document.getElementById('filtro-busca-cliente').addEventListener('input', renderClientes);
  document.getElementById('btn-atualizar-campanhas').addEventListener('click', carregarDashboard);

  /* --- Equipes (mantido) --- */
  function carregarEquipes() {
    return fetch(root.dataset.urlEquipes)
      .then(r => r.json())
      .then(data => {
        equipesCache = data.equipes || [];
        const opts = equipesCache.map(e => `<option value="${e.id}">${e.nome}</option>`).join('');
        ['siape-equipes', 'editar-campanha-equipes'].forEach(id => {
          const sel = document.getElementById(id);
          if (sel && id !== 'editar-campanha-equipes') sel.innerHTML = opts;
        });
        return equipesCache;
      });
  }

  function carregarFiltrosEquipe() {
    if (filtrosEquipe) return Promise.resolve(filtrosEquipe);
    return fetch(root.dataset.urlEquipeFiltros)
      .then(r => r.json())
      .then(data => {
        if (!data.ok) throw new Error(data.erro || 'Erro ao carregar filtros.');
        filtrosEquipe = data;
        return filtrosEquipe;
      });
  }

  function preencherSelect(id, opcoes, placeholder, valor) {
    const sel = document.getElementById(id);
    sel.innerHTML = `<option value="">${placeholder}</option>` +
      opcoes.map(o => `<option value="${o.id}">${o.nome}</option>`).join('');
    if (valor) sel.value = String(valor);
    sel.disabled = opcoes.length === 0;
  }

  function checkboxFuncionarioHtml(f) {
    const checked = participantesSelecionados.has(f.user_id) ? 'checked' : '';
    const label = f.apelido ? f.nome + ' (' + f.apelido + ')' : f.nome;
    return `<label class="ger-check"><input type="checkbox" class="chk-funcionario" value="${f.user_id}" ${checked}> ${label}</label>`;
  }

  function vincularCheckboxesParticipantes(container) {
    container.querySelectorAll('.chk-funcionario').forEach(chk => {
      chk.addEventListener('change', () => {
        const id = parseInt(chk.value, 10);
        if (chk.checked) participantesSelecionados.add(id);
        else participantesSelecionados.delete(id);
        atualizarContadorSelecionados();
        sincronizarSelecionarTodos();
      });
    });
  }

  function inferirFiltrosParticipantes(participantesIds) {
    if (!filtrosEquipe || !participantesIds.length) return null;
    const funcs = filtrosEquipe.funcionarios.filter(f => participantesIds.includes(f.user_id));
    if (!funcs.length) return null;

    const contagemSetor = {};
    funcs.forEach(f => {
      if (f.setor_id) contagemSetor[f.setor_id] = (contagemSetor[f.setor_id] || 0) + 1;
    });
    const setorId = Number(
      Object.keys(contagemSetor).sort((a, b) => contagemSetor[b] - contagemSetor[a])[0]
    ) || funcs[0].setor_id;
    const func = funcs.find(f => f.setor_id === setorId) || funcs[0];
    return {
      empresa_id: func.empresa_id,
      departamento_id: func.departamento_id,
      setor_id: func.setor_id,
    };
  }

  function aplicarFiltrosCascade(filtros) {
    if (!filtrosEquipe || !filtros) {
      resetarFiltrosEquipe();
      return;
    }
    preencherSelect('filtro-empresa', filtrosEquipe.empresas, 'Empresa', filtros.empresa_id);
    const deps = filtrosEquipe.departamentos.filter(d => String(d.empresa_id) === String(filtros.empresa_id));
    preencherSelect('filtro-departamento', deps, 'Departamento', filtros.departamento_id);
    document.getElementById('filtro-departamento').disabled = !deps.length;
    const setores = filtrosEquipe.setores.filter(s => String(s.departamento_id) === String(filtros.departamento_id));
    preencherSelect('filtro-setor', setores, 'Setor', filtros.setor_id);
    document.getElementById('filtro-setor').disabled = !setores.length;
    document.getElementById('filtro-selecionar-todos').checked = false;
    document.getElementById('filtro-selecionar-todos').disabled = !filtros.setor_id;
  }

  function atualizarContadorSelecionados() {
    const el = document.getElementById('equipe-total-selecionados');
    if (el) el.textContent = participantesSelecionados.size + ' selecionado(s)';
  }

  function funcionariosDoSetorAtual() {
    if (!filtrosEquipe) return [];
    const setorId = document.getElementById('filtro-setor').value;
    if (!setorId) return [];
    return filtrosEquipe.funcionarios.filter(f => String(f.setor_id) === String(setorId));
  }

  function renderParticipantesFiltrados(modoEdicao) {
    const div = document.getElementById('equipe-participantes-list');
    const listaSetor = funcionariosDoSetorAtual();
    const idsSetor = new Set(listaSetor.map(f => f.user_id));
    const html = [];

    if (modoEdicao && participantesSelecionados.size && filtrosEquipe) {
      const foraSetor = filtrosEquipe.funcionarios.filter(f =>
        participantesSelecionados.has(f.user_id) && !idsSetor.has(f.user_id)
      );
      if (foraSetor.length) {
        html.push('<p class="ger-modal-hint">Membros atuais (outros setores)</p>');
        html.push(...foraSetor.map(checkboxFuncionarioHtml));
      }
    }

    if (!listaSetor.length) {
      if (html.length) {
        div.innerHTML = html.join('');
        vincularCheckboxesParticipantes(div);
        document.getElementById('filtro-selecionar-todos').checked = false;
        document.getElementById('filtro-selecionar-todos').disabled = true;
        return;
      }
      div.innerHTML = '<p class="ger-modal-hint">Selecione empresa, departamento e setor.</p>';
      document.getElementById('filtro-selecionar-todos').checked = false;
      document.getElementById('filtro-selecionar-todos').disabled = true;
      return;
    }

    document.getElementById('filtro-selecionar-todos').disabled = false;
    if (html.length) html.push('<p class="ger-modal-hint">Setor selecionado</p>');
    html.push(...listaSetor.map(checkboxFuncionarioHtml));
    div.innerHTML = html.join('');
    vincularCheckboxesParticipantes(div);
    sincronizarSelecionarTodos();
  }

  function sincronizarSelecionarTodos() {
    const lista = funcionariosDoSetorAtual();
    const chkTodos = document.getElementById('filtro-selecionar-todos');
    if (!lista.length) { chkTodos.checked = false; return; }
    chkTodos.checked = lista.every(f => participantesSelecionados.has(f.user_id));
  }

  function onFiltroEmpresaChange() {
    const empresaId = document.getElementById('filtro-empresa').value;
    const deps = empresaId ? filtrosEquipe.departamentos.filter(d => String(d.empresa_id) === String(empresaId)) : [];
    preencherSelect('filtro-departamento', deps, 'Departamento', '');
    preencherSelect('filtro-setor', [], 'Setor', '');
    document.getElementById('filtro-setor').disabled = true;
    renderParticipantesFiltrados(!!equipeEmEdicao);
  }

  function onFiltroDepartamentoChange() {
    const depId = document.getElementById('filtro-departamento').value;
    const setores = depId ? filtrosEquipe.setores.filter(s => String(s.departamento_id) === String(depId)) : [];
    preencherSelect('filtro-setor', setores, 'Setor', '');
    renderParticipantesFiltrados(!!equipeEmEdicao);
  }

  function renderParticipantesFallbackEquipe(equipe) {
    const div = document.getElementById('equipe-participantes-list');
    const participantes = equipe ? (equipe.participantes || []) : [];
    if (!participantes.length) {
      div.innerHTML = '<p class="ger-modal-hint">Nenhum participante vinculado.</p>';
      return;
    }
    div.innerHTML = participantes.map(p => {
      const checked = participantesSelecionados.has(p.id) ? 'checked' : '';
      const label = p.nome || p.username;
      return `<label class="ger-check"><input type="checkbox" class="chk-funcionario" value="${p.id}" ${checked}> ${label}</label>`;
    }).join('');
    vincularCheckboxesParticipantes(div);
    document.getElementById('filtro-selecionar-todos').checked = false;
    document.getElementById('filtro-selecionar-todos').disabled = true;
  }

  function limparFiltrosEquipeUI() {
    if (!filtrosEquipe) return;
    preencherSelect('filtro-empresa', filtrosEquipe.empresas, 'Empresa', '');
    preencherSelect('filtro-departamento', [], 'Departamento', '');
    preencherSelect('filtro-setor', [], 'Setor', '');
    document.getElementById('filtro-departamento').disabled = true;
    document.getElementById('filtro-setor').disabled = true;
    document.getElementById('filtro-selecionar-todos').checked = false;
    document.getElementById('filtro-selecionar-todos').disabled = true;
    renderParticipantesFiltrados(false);
  }

  function resetarFiltrosEquipe() {
    equipeEmEdicao = null;
    limparFiltrosEquipeUI();
  }

  function abrirModalEquipe(equipe) {
    document.getElementById('equipe-edit-id').value = equipe ? equipe.id : '';
    document.getElementById('ger-nome-equipe').value = equipe ? equipe.nome : '';
    document.getElementById('modal-equipe-titulo').textContent = equipe ? 'Gerenciar equipe' : 'Nova equipe';
    document.getElementById('equipe-status-wrap').hidden = !equipe;
    if (equipe) document.getElementById('equipe-status').checked = !!equipe.status;
    participantesSelecionados = new Set(equipe ? (equipe.participantes || []).map(p => p.id) : []);
    equipeEmEdicao = equipe || null;
    carregarFiltrosEquipe().then(() => {
      if (equipe && participantesSelecionados.size) {
        const ids = Array.from(participantesSelecionados);
        const filtros = inferirFiltrosParticipantes(ids);
        if (filtros) {
          aplicarFiltrosCascade(filtros);
          renderParticipantesFiltrados(true);
        } else {
          limparFiltrosEquipeUI();
          renderParticipantesFallbackEquipe(equipe);
        }
      } else if (equipe) {
        limparFiltrosEquipeUI();
        equipeEmEdicao = equipe;
      } else {
        resetarFiltrosEquipe();
      }
      atualizarContadorSelecionados();
      abrirModal('modal-equipe');
    });
  }

  function renderMembrosEquipe(equipe) {
    equipeSelecionada = equipe || null;
    document.getElementById('equipe-membros-titulo').textContent = equipe ? 'Membros — ' + equipe.nome : 'Membros da equipe';
    document.getElementById('equipe-membros-hint').hidden = !!equipe;
    const tbody = document.querySelector('#tabela-equipe-membros tbody');
    const membros = equipe ? (equipe.participantes || []) : [];
    tbody.innerHTML = membros.length
      ? membros.map(m =>
          `<tr><td>${m.username}</td><td>${m.nome}</td>` +
          `<td><button type="button" class="ger-btn ger-btn--sm ger-btn--danger btn-remover-membro" data-user-id="${m.id}">Remover</button></td></tr>`
        ).join('')
      : '<tr><td colspan="3">Nenhum participante</td></tr>';
    tbody.querySelectorAll('.btn-remover-membro').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        removerParticipanteEquipe(parseInt(btn.dataset.userId, 10));
      });
    });
  }

  function removerParticipanteEquipe(userId) {
    if (!equipeSelecionada || !confirm('Remover participante?')) return;
    postJson(root.dataset.urlPostEquipeAtualizar, {
      equipe_id: equipeSelecionada.id,
      participantes_ids: (equipeSelecionada.participantes || []).map(p => p.id).filter(id => id !== userId),
    }).then(data => {
      if (data.ok) {
        carregarEquipes().then(() => {
          carregarEquipesTabela();
          renderMembrosEquipe(equipesCache.find(x => x.id === equipeSelecionada.id));
        });
      }
    });
  }

  function carregarEquipesTabela() {
    carregarEquipes().then(equipes => {
      const tbody = document.querySelector('#tabela-equipes tbody');
      tbody.innerHTML = equipes.map(e =>
        `<tr data-equipe-id="${e.id}">` +
        `<td>${e.nome}</td><td>${e.participantes_count}</td>` +
        `<td>${e.status ? badgeStatus(true) : badgeStatus(false)}</td>` +
        `<td><button type="button" class="ger-btn ger-btn--sm btn-gerenciar-equipe" data-id="${e.id}">Gerenciar</button></td>` +
        `</tr>`
      ).join('');
      tbody.querySelectorAll('.btn-gerenciar-equipe').forEach(btn => {
        btn.addEventListener('click', () => {
          const eq = equipesCache.find(x => String(x.id) === btn.dataset.id);
          if (eq) { renderMembrosEquipe(eq); abrirModalEquipe(eq); }
        });
      });
      tbody.querySelectorAll('tr[data-equipe-id]').forEach(row => {
        row.addEventListener('click', e => {
          if (e.target.closest('.btn-gerenciar-equipe')) return;
          renderMembrosEquipe(equipesCache.find(x => String(x.id) === row.dataset.equipeId));
        });
      });
    });
  }

  document.getElementById('btn-abrir-modal-equipe-nova').addEventListener('click', () => abrirModalEquipe());

  /* --- Modais campanha --- */
  function equipesSelecionadas(selectId) {
    return Array.from(document.getElementById(selectId).selectedOptions).map(o => parseInt(o.value, 10));
  }

  function renderPreviewSiape(el, data) {
    if (!data.ok) { el.innerHTML = `<p class="ger-erro">${data.erro || 'Erro.'}</p>`; return; }
    cpfsPreviewSiape = data.cpfs || [];
    const inv = data.invalidos_csv ? ` | <strong>Inválidos CSV:</strong> ${data.invalidos_csv}` : '';
    el.innerHTML = `<p><strong>Total:</strong> ${data.total} | <strong>OK:</strong> ${data.encontrados} | <strong>Faltando:</strong> ${data.nao_encontrados}${inv}</p>` +
      '<table class="ger-table"><thead><tr><th>CPF</th><th>Nome</th><th>Status</th></tr></thead><tbody>' +
      (data.itens || []).slice(0, 20).map(r => `<tr><td>${r.cpf}</td><td>${r.nome}</td><td>${r.encontrado ? 'OK' : '—'}</td></tr>`).join('') +
      '</tbody></table>';
    document.getElementById('btn-siape-criar').disabled = !cpfsPreviewSiape.length;
  }

  function renderPreviewOutros(el, data) {
    if (!data.ok) { el.innerHTML = `<p class="ger-erro">${data.erro || 'Erro.'}</p>`; return; }
    el.innerHTML = `<p><strong>Total:</strong> ${data.total_preview ?? 0}</p>` +
      (data.schema ? `<p>Colunas: ${data.schema.join(', ')}</p>` : '');
    document.getElementById('btn-outros-confirm').disabled = !data.ok;
  }

  document.getElementById('siape-arquivo').addEventListener('change', function () {
    arquivoSiape = this.files[0] || null;
    cpfsPreviewSiape = [];
    document.getElementById('siape-preview').innerHTML = '';
    document.getElementById('btn-siape-criar').disabled = true;
  });
  document.getElementById('btn-siape-preview').addEventListener('click', () => {
    if (!arquivoSiape) return alert('Selecione o CSV.');
    postArquivoPreviewSSE(
      root.dataset.urlSiapePreview,
      arquivoSiape,
      document.getElementById('siape-preview'),
      renderPreviewSiape,
      document.getElementById('btn-siape-preview'),
      document.getElementById('btn-siape-criar')
    );
  });
  document.getElementById('btn-siape-criar').addEventListener('click', () => {
    const nome = document.getElementById('siape-nome').value.trim();
    const equipesIds = equipesSelecionadas('siape-equipes');
    if (!nome || !equipesIds.length || !cpfsPreviewSiape.length) return alert('Preencha nome, equipe e preview.');
    postCriarCampanhaSSE(
      root.dataset.urlSiapeCriar,
      { nome, equipes_ids: equipesIds, cpfs: cpfsPreviewSiape },
      document.getElementById('siape-preview'),
      'modal-siape',
      'SIAPE',
      document.getElementById('btn-siape-criar'),
      document.getElementById('btn-siape-preview')
    );
  });

  document.getElementById('outros-arquivo').addEventListener('change', function () {
    arquivoOutros = this.files[0] || null;
    document.getElementById('btn-outros-confirm').disabled = !arquivoOutros;
    document.getElementById('outros-preview').innerHTML = '';
  });
  document.getElementById('btn-outros-preview').addEventListener('click', () => {
    if (!arquivoOutros) return;
    postArquivo(root.dataset.urlImportPreview, arquivoOutros)
      .then(d => renderPreviewOutros(document.getElementById('outros-preview'), d))
      .catch(() => {
        document.getElementById('outros-preview').innerHTML = '<p class="ger-erro">Falha ao processar preview.</p>';
      });
  });
  document.getElementById('btn-outros-confirm').addEventListener('click', async () => {
    if (!arquivoOutros) return alert('Selecione CSV.');
    let campanhaId = document.getElementById('outros-select-campanha').value;
    const nomeCampanha = document.getElementById('outros-nome-campanha').value.trim();
    if (!campanhaId) {
      if (!nomeCampanha) return alert('Informe nome ou selecione campanha.');
      const criada = await postJson(root.dataset.urlPostCampanha, { nome: nomeCampanha, tipo_campanha: 'OUTROS' });
      if (!criada.ok) return alert(criada.erro || 'Erro.');
      campanhaId = criada.campanha_id;
    }
    const fd = new FormData();
    fd.append('arquivo', arquivoOutros);
    fd.append('campanha_id', campanhaId);
    fetch(root.dataset.urlImportConfirm, { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: fd })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          fecharModal('modal-outros');
          carregarDashboard();
          alert('Importados: ' + data.total + ' clientes.');
        } else alert(data.erro || 'Erro.');
      });
  });

  document.getElementById('filtro-empresa').addEventListener('change', onFiltroEmpresaChange);
  document.getElementById('filtro-departamento').addEventListener('change', onFiltroDepartamentoChange);
  document.getElementById('filtro-setor').addEventListener('change', () => renderParticipantesFiltrados(!!equipeEmEdicao));
  document.getElementById('filtro-selecionar-todos').addEventListener('change', function () {
    funcionariosDoSetorAtual().forEach(f => {
      if (this.checked) participantesSelecionados.add(f.user_id);
      else participantesSelecionados.delete(f.user_id);
    });
    renderParticipantesFiltrados(!!equipeEmEdicao);
    atualizarContadorSelecionados();
  });

  document.getElementById('btn-salvar-editar-campanha').addEventListener('click', () => {
    const campanhaId = parseInt(document.getElementById('editar-campanha-id').value, 10);
    const nome = document.getElementById('editar-campanha-nome').value.trim();
    const descricao = document.getElementById('editar-campanha-descricao').value.trim();
    const equipesIds = equipesSelecionadas('editar-campanha-equipes');
    if (!campanhaId || !nome) return alert('Informe o nome da campanha.');
    postJson(root.dataset.urlCampanhaAtualizar, {
      campanha_id: campanhaId,
      nome,
      descricao,
      equipes_ids: equipesIds,
    }).then(data => {
      if (data.ok) {
        fecharModal('modal-editar-campanha');
        carregarDashboard().then(() => {
          if (campanhaSelecionadaId === campanhaId) selecionarCampanha(campanhaId);
        });
      } else {
        alert(data.erro || 'Erro ao salvar campanha.');
      }
    });
  });

  document.getElementById('btn-salvar-equipe').addEventListener('click', () => {
    const equipeId = document.getElementById('equipe-edit-id').value;
    const nome = document.getElementById('ger-nome-equipe').value.trim();
    const participantesIds = Array.from(participantesSelecionados);
    if (!nome) return alert('Informe o nome.');
    const payload = equipeId
      ? { equipe_id: parseInt(equipeId, 10), nome, status: document.getElementById('equipe-status').checked, participantes_ids: participantesIds }
      : { nome, participantes_ids: participantesIds };
    postJson(equipeId ? root.dataset.urlPostEquipeAtualizar : root.dataset.urlPostEquipe, payload).then(data => {
      if (data.ok) {
        fecharModal('modal-equipe');
        carregarEquipes().then(() => {
          carregarEquipesTabela();
          if (data.equipe_id) renderMembrosEquipe(equipesCache.find(x => x.id === data.equipe_id));
        });
      } else alert(data.erro || 'Erro.');
    });
  });

  /* --- Init --- */
  carregarFiltrosEquipe();
  carregarEquipes();
  limparDetalhes();
  carregarDashboard();
})();
