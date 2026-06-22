(function () {
  'use strict';

  const root = document.getElementById('esteira-root');
  if (!root) return;

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  let clienteAtual = null;
  let statusChoices = [];
  let tipoCampanhaAtual = 'SIAPE';
  let campanhasMap = {};

  const btnProximo = document.getElementById('btn-proximo-cliente');
  const btnRecarregar = document.getElementById('btn-recarregar-ficha');
  const btnHistorico = document.getElementById('btn-historico');
  const modalHistorico = document.getElementById('modal-historico');

  const TITULOS = {
    SIAPE: { titulo: 'Esteira de Discagem SIAPE', subtitulo: 'Gestão ativa de leads e acompanhamento de campanhas SIAPE.' },
    INSS: { titulo: 'Esteira de Discagem INSS', subtitulo: 'Gestão de agendamentos, presença em loja e tabulação INSS.' },
    OUTROS: { titulo: 'Esteira de Discagem', subtitulo: 'Campanha genérica com dados importados via CSV.' },
  };

  function getCampanhaId() {
    return document.getElementById('esteira-campanha').value;
  }

  function formatCpf(cpf) {
    if (!cpf) return '—';
    const d = String(cpf).replace(/\D/g, '');
    if (d.length !== 11) return cpf;
    return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }

  function aplicarTema(tipo) {
    tipoCampanhaAtual = tipo || 'OUTROS';
    root.className = 'esteira-page esteira-page--' + tipoCampanhaAtual.toLowerCase();
    const cfg = TITULOS[tipoCampanhaAtual] || TITULOS.OUTROS;
    document.getElementById('esteira-titulo').textContent = cfg.titulo;
    document.getElementById('esteira-subtitulo').textContent = cfg.subtitulo;
  }

  function atualizarBotoesControle() {
    const temCliente = !!clienteAtual;
    const tabulado = temCliente && clienteAtual.tabulado;
    btnRecarregar.disabled = !temCliente;
    // Próximo: habilitado se não há cliente OU cliente já tabulado
    btnProximo.disabled = temCliente && !tabulado;
  }

  function aplicarCliente(cliente) {
    if (!cliente) {
      clienteAtual = null;
      document.getElementById('ficha-conteudo').innerHTML = '<p class="ficha-vazia">Selecione uma campanha e clique em Próximo cliente.</p>';
      document.getElementById('ficha-cliente-id').textContent = '—';
      document.getElementById('form-agendamento').hidden = true;
      document.getElementById('agendamento-hint').hidden = false;
      renderInsights(null, tipoCampanhaAtual);
      atualizarBotoesControle();
      return;
    }

    clienteAtual = cliente;
    aplicarTema(cliente.tipo || tipoCampanhaAtual);
    renderFicha(cliente.ficha, cliente.tipo);
    document.getElementById('ficha-cliente-id').textContent = 'ID Cliente: ' + formatCpf(cliente.cpf);
    document.getElementById('form-agendamento').hidden = false;
    document.getElementById('agendamento-hint').hidden = true;
    atualizarBotoesControle();
  }

  function carregarCampanhas() {
    fetch(root.dataset.urlCampanhas)
      .then(r => r.json())
      .then(data => {
        const sel = document.getElementById('esteira-campanha');
        sel.innerHTML = '';
        campanhasMap = {};
        (data.campanhas || []).forEach(c => {
          campanhasMap[c.id] = c;
          const o = document.createElement('option');
          o.value = c.id;
          o.textContent = c.nome;
          o.dataset.tipo = c.tipo_campanha;
          sel.appendChild(o);
        });
        if (sel.options.length) {
          onCampanhaChange();
        } else {
          aplicarTema('OUTROS');
          atualizarBotoesControle();
        }
      });
  }

  function carregarPendenteCampanha() {
    const id = getCampanhaId();
    if (!id) return;
    fetch(root.dataset.urlPendente + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        if (data.ok && data.cliente) {
          aplicarCliente(data.cliente);
        } else {
          aplicarCliente(null);
        }
      });
  }

  function onCampanhaChange() {
    const sel = document.getElementById('esteira-campanha');
    const opt = sel.options[sel.selectedIndex];
    const tipo = opt ? (opt.dataset.tipo || campanhasMap[sel.value]?.tipo_campanha) : 'OUTROS';
    aplicarTema(tipo);
    carregarKpis();
    carregarAgendamentos();
    carregarPendenteCampanha();
  }

  function carregarKpis() {
    const id = getCampanhaId();
    if (!id) return;
    fetch(root.dataset.urlKpis + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        if (!data.ok) return;
        const k = data.kpis;
        document.getElementById('kpi-tabulados').textContent = k.tabulados_hoje;
        document.getElementById('kpi-agendamentos').textContent = k.agendamentos_pendentes;
        document.getElementById('kpi-conversao').textContent = k.taxa_conversao + '%';
        document.getElementById('kpi-clientes').textContent = k.clientes_campanha;
        document.getElementById('kpi-campanhas').textContent = k.campanhas_ativas;
      });
  }

  function renderFicha(ficha, tipo) {
    const el = document.getElementById('ficha-conteudo');
    if (window.EsteiraFichaRender) {
      el.innerHTML = EsteiraFichaRender.render(ficha, tipo);
    } else {
      el.innerHTML = '<p class="ficha-vazia">Erro ao carregar renderizador de ficha.</p>';
    }
    renderInsights(ficha, tipo);
  }

  function renderInsights(ficha, tipo) {
    const ul = document.getElementById('insights-lista');
    const items = window.EsteiraFichaRender
      ? EsteiraFichaRender.buildInsights(ficha, tipo, clienteAtual)
      : ['Insights indisponíveis.'];

    if (typeof items[0] === 'string') {
      ul.innerHTML = '<li>' + items[0] + '</li>';
      return;
    }
    ul.innerHTML = items.map(it =>
      '<li><span class="insight-icon">' + it.icon + '</span><span>' + it.text + '</span></li>'
    ).join('');
  }

  function carregarStatus() {
    fetch(root.dataset.urlStatus)
      .then(r => r.json())
      .then(data => {
        statusChoices = data.status_choices || [];
        const grid = document.getElementById('tabulacao-botoes');
        grid.innerHTML = statusChoices.map(s => {
          const cor = s.cor_tag ? (s.cor_tag.startsWith('#') ? s.cor_tag : '#' + s.cor_tag) : '#64748b';
          return '<button type="button" class="tabulacao-btn" data-id="' + s.id + '" style="background:' + cor + '">' + s.nome + '</button>';
        }).join('');
        grid.querySelectorAll('.tabulacao-btn').forEach(btn => {
          btn.addEventListener('click', () => tabular(parseInt(btn.dataset.id, 10)));
        });
      });
  }

  function tabular(statusId) {
    if (!clienteAtual) return;
    fetch(root.dataset.urlTabulacao, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({
        controle_id: clienteAtual.controle_id,
        status_id: statusId,
      }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          clienteAtual.tabulado = true;
          clienteAtual.tabulacao_id = statusId;
          clienteAtual.tabulacao_nome = data.tabulacao?.nome || null;
          carregarKpis();
          document.getElementById('esteira-observacoes').value = '';
          document.getElementById('obs-count').textContent = '0';
          atualizarBotoesControle();
        }
      });
  }

  function proximoCliente() {
    const id = getCampanhaId();
    if (!id) return alert('Selecione uma campanha.');
    if (clienteAtual && !clienteAtual.tabulado) return;

    fetch(root.dataset.urlProximo + '?campanha_id=' + id + '&novo=1')
      .then(r => r.json().then(data => ({ status: r.status, data })))
      .then(({ status, data }) => {
        if (status === 409 && data.bloqueado) {
          if (data.cliente) aplicarCliente(data.cliente);
          alert(data.erro || 'Tabule o cliente atual antes de avançar.');
          return;
        }
        if (!data.cliente) {
          aplicarCliente(null);
          document.getElementById('ficha-conteudo').innerHTML =
            '<p class="ficha-vazia">' + (data.mensagem || 'Sem clientes disponíveis.') + '</p>';
          return;
        }
        aplicarCliente(data.cliente);
      });
  }

  function recarregarFicha() {
    if (!clienteAtual) return;

    if (clienteAtual.controle_id) {
      fetch(root.dataset.urlControle + '?controle_id=' + clienteAtual.controle_id)
        .then(r => r.json())
        .then(data => {
          if (data.ok && data.cliente) {
            aplicarCliente(data.cliente);
          }
        });
      return;
    }

    if (clienteAtual.cliente_id) {
      fetch(root.dataset.urlFicha + '?cliente_id=' + clienteAtual.cliente_id)
        .then(r => r.json())
        .then(data => {
          if (data.ok && data.ficha) {
            clienteAtual.ficha = data.ficha;
            renderFicha(data.ficha, data.ficha.tipo || clienteAtual.tipo);
          }
        });
    }
  }

  function abrirModal(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = false;
  }

  function fecharModal(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  }

  function carregarHistoricoModal() {
    const id = getCampanhaId();
    const tbody = document.getElementById('historico-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="ficha-vazia">Carregando…</td></tr>';

    const url = id
      ? root.dataset.urlHistorico + '?campanha_id=' + id
      : root.dataset.urlHistorico;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        const lista = data.historico || [];
        if (!lista.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="ficha-vazia">Nenhum registro encontrado.</td></tr>';
          return;
        }
        tbody.innerHTML = lista.map(h =>
          '<tr>' +
          '<td>' + formatCpf(h.cpf) + '</td>' +
          '<td>' + (h.nome || '—') + '</td>' +
          '<td>' + (h.agendamento || '—') + '</td>' +
          '<td>' + (h.tabulacao || '—') + '</td>' +
          '<td><button type="button" class="esteira-btn esteira-btn--primary esteira-btn--sm btn-puxar-ficha" data-controle="' + h.controle_id + '">Puxar ficha</button></td>' +
          '</tr>'
        ).join('');

        tbody.querySelectorAll('.btn-puxar-ficha').forEach(btn => {
          btn.addEventListener('click', () => puxarFicha(parseInt(btn.dataset.controle, 10)));
        });
      });
  }

  function puxarFicha(controleId) {
    fetch(root.dataset.urlControle + '?controle_id=' + controleId)
      .then(r => r.json())
      .then(data => {
        if (!data.ok || !data.cliente) {
          alert(data.erro || 'Não foi possível carregar a ficha.');
          return;
        }
        const campSel = document.getElementById('esteira-campanha');
        if (data.cliente.campanha_id && campSel.value !== String(data.cliente.campanha_id)) {
          campSel.value = String(data.cliente.campanha_id);
          const opt = campSel.options[campSel.selectedIndex];
          aplicarTema(opt ? (opt.dataset.tipo || campanhasMap[campSel.value]?.tipo_campanha) : 'OUTROS');
          carregarKpis();
          carregarAgendamentos();
        }
        aplicarCliente(data.cliente);
        fecharModal('modal-historico');
      });
  }

  function carregarAgendamentos() {
    const id = getCampanhaId();
    if (!id) return;
    fetch(root.dataset.urlAgendamentos + '?campanha_id=' + id)
      .then(r => r.json())
      .then(data => {
        const el = document.getElementById('agendamentos-lista');
        const lista = data.agendamentos || [];
        if (!lista.length) {
          el.innerHTML = '<p class="ficha-vazia">Nenhum agendamento pendente.</p>';
          return;
        }
        el.innerHTML = lista.map(a =>
          '<div class="ag-card">' +
          '<div class="ag-card__data">' + (a.dia || '') + ' ' + (a.hora || '') + '</div>' +
          '<div class="ag-card__nome">' + formatCpf(a.cpf) + '</div>' +
          '<div style="font-size:11px;color:#64748b;margin-top:4px;">' + (a.responsavel || '') + '</div>' +
          '<span class="ag-card__badge ag-card__badge--pendente">Pendente</span>' +
          '</div>'
        ).join('');
      });
  }

  btnProximo.addEventListener('click', proximoCliente);
  btnRecarregar.addEventListener('click', recarregarFicha);
  btnHistorico.addEventListener('click', () => {
    abrirModal('modal-historico');
    carregarHistoricoModal();
  });

  document.getElementById('esteira-campanha').addEventListener('change', onCampanhaChange);

  document.querySelectorAll('[data-fechar-modal]').forEach(btn => {
    btn.addEventListener('click', () => fecharModal(btn.dataset.fecharModal));
  });

  if (modalHistorico) {
    modalHistorico.addEventListener('click', e => {
      if (e.target === modalHistorico) fecharModal('modal-historico');
    });
  }

  document.getElementById('esteira-observacoes').addEventListener('input', function () {
    document.getElementById('obs-count').textContent = String(this.value.length);
  });

  document.getElementById('form-agendamento').addEventListener('submit', function (e) {
    e.preventDefault();
    if (!clienteAtual) return;
    fetch(root.dataset.urlAgendamentoPost, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({
        controle_id: clienteAtual.controle_id,
        dia_agendamento: document.getElementById('ag-dia').value,
        hora: document.getElementById('ag-hora').value,
        responsavel: document.getElementById('ag-responsavel').value,
        observacao: document.getElementById('ag-obs').value,
      }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          carregarAgendamentos();
          carregarKpis();
          this.reset();
        }
      });
  });

  carregarCampanhas();
  carregarStatus();
  atualizarBotoesControle();
})();
