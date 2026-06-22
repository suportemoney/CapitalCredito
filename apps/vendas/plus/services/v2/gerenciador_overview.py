from django.db.models import Count
from django.utils import timezone

from apps.vendas.plus.models_v2 import (
    AgendamentoV2,
    CampanhaV2,
    ClienteCampanhaV2,
    ControleClienteV2,
    ImportacaoCsvV2,
)

from .distribuicao import extrair_nome_ficha
from .cliente_resolver import resolver_dados_cliente


def _qs_campanhas_tipo(tipo: str | None):
    qs = CampanhaV2.objects.all()
    if tipo:
        qs = qs.filter(tipo_campanha=tipo.upper())
    return qs


def _nome_rapido(cpf: str, tipo: str, dados_json: dict | None) -> str:
    tipo = (tipo or '').upper()
    if tipo == 'SIAPE':
        from apps.vendas.siape.models import Cliente
        nome = Cliente.objects.filter(cpf=cpf).values_list('nome', flat=True).first()
        if nome:
            return nome
    elif dados_json:
        for chave in ('nome', 'Nome', 'NOME', 'nome_completo'):
            if dados_json.get(chave):
                return str(dados_json[chave])
    ficha = resolver_dados_cliente(cpf, tipo, dados_json)
    return extrair_nome_ficha(ficha)


def build_gerenciador_kpis(tipo: str | None = None) -> dict:
    campanhas_qs = _qs_campanhas_tipo(tipo)
    campanha_ids = list(campanhas_qs.values_list('id', flat=True))
    ativas = campanhas_qs.filter(status=True).count()
    total_campanhas = campanhas_qs.count()

    clientes_total = ClienteCampanhaV2.objects.filter(campanha_id__in=campanha_ids).count()

    equipes_ids = set()
    for c in campanhas_qs.prefetch_related('equipes'):
        equipes_ids.update(c.equipes.values_list('id', flat=True))
    equipes_total = len(equipes_ids)

    agendamentos_pendentes = AgendamentoV2.objects.filter(
        controle__campanha_id__in=campanha_ids,
        status=AgendamentoV2.STATUS_EM_ESPERA,
    ).count()

    sete_dias = timezone.now() - timezone.timedelta(days=7)
    importacoes_recentes = ImportacaoCsvV2.objects.filter(
        campanha_id__in=campanha_ids,
        data_criacao__gte=sete_dias,
    ).count()

    return {
        'campanhas_ativas': ativas,
        'campanhas_total': total_campanhas,
        'clientes_vinculados': clientes_total,
        'equipes_vinculadas': equipes_total,
        'agendamentos_pendentes': agendamentos_pendentes,
        'importacoes_recentes': importacoes_recentes,
    }


def listar_campanhas_enriquecidas(tipo: str | None = None) -> list[dict]:
    qs = CampanhaV2.objects.prefetch_related('equipes').annotate(
        clientes_count=Count('clientes'),
    ).order_by('-data_criacao')
    if tipo:
        qs = qs.filter(tipo_campanha=tipo.upper())

    return [
        {
            'id': c.id,
            'nome': c.nome,
            'descricao': c.descricao or '',
            'status': c.status,
            'tipo_campanha': c.tipo_campanha,
            'equipes': list(c.equipes.values_list('id', flat=True)),
            'equipes_nomes': [e.nome for e in c.equipes.all()],
            'clientes_count': c.clientes_count,
            'data_criacao': c.data_criacao.isoformat() if c.data_criacao else None,
        }
        for c in qs
    ]


def detalhes_campanha(campanha_id: int) -> dict | None:
    campanha = CampanhaV2.objects.filter(pk=campanha_id).prefetch_related('equipes').first()
    if not campanha:
        return None

    clientes_qs = ClienteCampanhaV2.objects.filter(campanha=campanha)
    por_tipo = {
        row['tipo']: row['total']
        for row in clientes_qs.values('tipo').annotate(total=Count('id'))
    }

    controles = ControleClienteV2.objects.filter(campanha=campanha)
    com_tabulacao = controles.filter(tabulacao__isnull=False).count()
    sem_tabulacao = controles.filter(tabulacao__isnull=True).count()
    com_agendamento = controles.filter(
        agendamentos__status=AgendamentoV2.STATUS_EM_ESPERA,
    ).distinct().count()
    em_atendimento = controles.filter(tabulacao__isnull=True).values('cliente_id').distinct().count()

    return {
        'id': campanha.id,
        'nome': campanha.nome,
        'descricao': campanha.descricao or '—',
        'tipo_campanha': campanha.tipo_campanha,
        'status': campanha.status,
        'data_criacao': campanha.data_criacao.isoformat() if campanha.data_criacao else None,
        'equipes_nomes': [e.nome for e in campanha.equipes.all()],
        'clientes_total': clientes_qs.count(),
        'clientes_por_tipo': por_tipo,
        'controles': {
            'em_atendimento': em_atendimento,
            'sem_tabulacao': sem_tabulacao,
            'com_agendamento': com_agendamento,
            'com_tabulacao': com_tabulacao,
        },
    }


def listar_clientes_campanha_detalhe(campanha_id: int, limite: int = 100) -> list[dict]:
    clientes = (
        ClienteCampanhaV2.objects.filter(campanha_id=campanha_id)
        .order_by('-data_criacao')[:limite]
    )

    itens = []
    for c in clientes:
        controle = (
            ControleClienteV2.objects.filter(cliente=c)
            .select_related('user', 'tabulacao')
            .order_by('-updated_at')
            .first()
        )
        ag_pendente = None
        if controle:
            ag = (
                controle.agendamentos.filter(status=AgendamentoV2.STATUS_EM_ESPERA)
                .order_by('dia_agendamento', 'hora')
                .first()
            )
            if ag:
                ag_pendente = ag.dia_agendamento.isoformat()

        itens.append({
            'id': c.id,
            'cpf': c.cpf,
            'nome': _nome_rapido(c.cpf, c.tipo, c.dados_json),
            'tipo': c.tipo,
            'tem_json': bool(c.dados_json),
            'usuario': controle.user.get_full_name() or controle.user.username if controle else '—',
            'tabulacao': controle.tabulacao.nome if controle and controle.tabulacao else '—',
            'tabulacao_cor': controle.tabulacao.cor_tag if controle and controle.tabulacao else None,
            'status_ativo': controle.status if controle else True,
            'ultima_atualizacao': controle.updated_at.isoformat() if controle else None,
            'agendamento_pendente': ag_pendente,
        })
    return itens


def ultima_importacao_campanha(campanha_id: int) -> dict | None:
    imp = (
        ImportacaoCsvV2.objects.filter(campanha_id=campanha_id)
        .select_related('criado_por')
        .order_by('-data_criacao')
        .first()
    )
    if not imp:
        return None
    criador = '—'
    if imp.criado_por:
        criador = imp.criado_por.get_full_name() or imp.criado_por.username
    return {
        'arquivo_nome': imp.arquivo_nome,
        'total_linhas': imp.total_linhas,
        'colunas': imp.colunas_schema or [],
        'criado_por': criador,
        'data_criacao': imp.data_criacao.isoformat() if imp.data_criacao else None,
        'status': 'Concluída',
    }


def proximos_agendamentos_campanha(campanha_id: int, limite: int = 8) -> list[dict]:
    ags = (
        AgendamentoV2.objects.filter(
            controle__campanha_id=campanha_id,
            status=AgendamentoV2.STATUS_EM_ESPERA,
        )
        .select_related('controle__cliente', 'controle__user')
        .order_by('dia_agendamento', 'hora')[:limite]
    )
    resultado = []
    for ag in ags:
        cliente = ag.controle.cliente
        resultado.append({
            'id': ag.id,
            'cpf': cliente.cpf,
            'nome': _nome_rapido(cliente.cpf, cliente.tipo, cliente.dados_json),
            'dia': ag.dia_agendamento.isoformat(),
            'hora': ag.hora.strftime('%H:%M'),
            'responsavel': ag.responsavel,
            'observacao': ag.observacao or '',
            'status': ag.status,
        })
    return resultado
