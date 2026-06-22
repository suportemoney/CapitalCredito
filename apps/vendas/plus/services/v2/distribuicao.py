from django.db.models import Q

from apps.vendas.plus.models import Equipe, StatusChoice
from apps.vendas.plus.models_v2 import (
    AgendamentoV2,
    CampanhaV2,
    ClienteCampanhaV2,
    ControleClienteV2,
)

from .cliente_resolver import resolver_dados_cliente


def extrair_nome_ficha(ficha: dict) -> str:
    """Extrai nome exibível a partir do payload da ficha."""
    if not ficha or not ficha.get('encontrado'):
        return '—'
    pessoal = ficha.get('pessoal') or {}
    nome = pessoal.get('nome') or pessoal.get('nome_completo')
    if nome:
        return nome
    campos = ficha.get('campos') or {}
    for chave in ('nome', 'Nome', 'NOME', 'nome_completo'):
        if campos.get(chave):
            return str(campos[chave])
    return '—'


def campanhas_do_usuario(user) -> list[CampanhaV2]:
    equipes_ids = Equipe.objects.filter(participantes=user, status=True).values_list('id', flat=True)
    return list(
        CampanhaV2.objects.filter(status=True, equipes__id__in=equipes_ids)
        .distinct()
        .order_by('-data_criacao')
    )


def _montar_payload_cliente(controle: ControleClienteV2, cliente_ref: ClienteCampanhaV2) -> dict:
    ficha = resolver_dados_cliente(
        cliente_ref.cpf,
        cliente_ref.tipo,
        cliente_ref.dados_json,
    )
    tab = controle.tabulacao
    return {
        'controle_id': controle.id,
        'cliente_id': cliente_ref.id,
        'cpf': cliente_ref.cpf,
        'nome': extrair_nome_ficha(ficha),
        'tipo': cliente_ref.tipo,
        'campanha_id': controle.campanha_id,
        'campanha_nome': controle.campanha.nome,
        'tabulacao_id': tab.id if tab else None,
        'tabulacao_nome': tab.nome if tab else None,
        'tabulado': tab is not None,
        'ficha': ficha,
    }


def cliente_pendente_usuario(user, campanha_id: int) -> dict | None:
    """Retorna cliente em aberto (sem tabulação) do usuário na campanha."""
    campanha = CampanhaV2.objects.filter(pk=campanha_id, status=True).first()
    if not campanha:
        return None

    controle = (
        ControleClienteV2.objects.filter(
            campanha=campanha,
            user=user,
            tabulacao__isnull=True,
        )
        .select_related('cliente', 'campanha', 'tabulacao')
        .order_by('-updated_at')
        .first()
    )
    if not controle:
        return None
    return _montar_payload_cliente(controle, controle.cliente)


def carregar_controle(user, controle_id: int) -> dict | None:
    """Carrega ficha de um controle pertencente ao usuário."""
    controle = (
        ControleClienteV2.objects.filter(pk=controle_id, user=user)
        .select_related('cliente', 'campanha', 'tabulacao')
        .first()
    )
    if not controle:
        return None
    return _montar_payload_cliente(controle, controle.cliente)


def _cpfs_indisponiveis_para_usuario(user, campanha: CampanhaV2) -> set[str]:
    """
    CPFs que não podem ser entregues nesta campanha.

    Pendência (sem tabulação) em campanha ATIVA reserva o CPF só para o dono.
    Campanhas inativas não entram no bloqueio.
    """
    indisponiveis: set[str] = set()
    pendentes = ControleClienteV2.objects.filter(
        campanha__status=True,
        tabulacao__isnull=True,
    ).select_related('cliente')

    for controle in pendentes:
        cpf = controle.cliente.cpf
        if controle.user_id != user.id:
            indisponiveis.add(cpf)
            continue
        if controle.campanha_id != campanha.id:
            indisponiveis.add(cpf)
    return indisponiveis


def proximo_cliente(user, campanha_id: int, solicitar_novo: bool = False) -> dict | None:
    """
    Distribui cliente na esteira.

    - Cliente pendente (sem tabulação) do usuário continua voltando só para ele.
    - Pendência em campanha ativa reserva o CPF globalmente (outras campanhas/usuários).
    - Campanha inativada libera o CPF para distribuição nas demais campanhas ativas.
    - Após tabulação, o CPF não entra para nenhum usuário da mesma campanha.
    - CPF com tabulação de bloqueio (StatusChoice) não é reentregue ao mesmo user.
    """
    campanha = CampanhaV2.objects.filter(pk=campanha_id, status=True).first()
    if not campanha:
        return None

    pendente = (
        ControleClienteV2.objects.filter(
            campanha=campanha,
            user=user,
            tabulacao__isnull=True,
        )
        .select_related('cliente', 'campanha', 'tabulacao')
        .order_by('-updated_at')
        .first()
    )

    if pendente and not solicitar_novo:
        return _montar_payload_cliente(pendente, pendente.cliente)

    if pendente and solicitar_novo:
        return {
            '_bloqueio': True,
            'mensagem': 'Tabule o cliente atual antes de avançar para o próximo.',
            'cliente': _montar_payload_cliente(pendente, pendente.cliente),
        }

    tabulacoes_bloqueio = StatusChoice.objects.filter(
        status_booleano=True,
        comportamento__in=('NAO_ENTREGAR_MAIS', 'NAO_ENTREGAR_CAMPANHA'),
    ).values_list('id', flat=True)

    cpfs_bloqueados = set(
        ControleClienteV2.objects.filter(
            user=user,
            tabulacao_id__in=tabulacoes_bloqueio,
        ).values_list('cliente__cpf', flat=True)
    )

    cpfs_tabulados_campanha = set(
        ControleClienteV2.objects.filter(
            campanha=campanha,
            tabulacao__isnull=False,
        ).values_list('cliente__cpf', flat=True)
    )

    cpfs_indisponiveis = _cpfs_indisponiveis_para_usuario(user, campanha)

    clientes_campanha = ClienteCampanhaV2.objects.filter(campanha=campanha)

    for cliente_ref in clientes_campanha.order_by('id'):
        if cliente_ref.cpf in cpfs_bloqueados:
            continue
        if cliente_ref.cpf in cpfs_tabulados_campanha:
            continue
        if cliente_ref.cpf in cpfs_indisponiveis:
            continue

        controle, created = ControleClienteV2.objects.get_or_create(
            campanha=campanha,
            cliente=cliente_ref,
            user=user,
            defaults={'status': True},
        )

        if not created and controle.tabulacao_id:
            continue

        return _montar_payload_cliente(controle, cliente_ref)

    return None


def listar_historico_usuario(user, campanha_id: int | None = None) -> list[dict]:
    """CPFs com agendamento ou tabulação do usuário logado."""
    qs = (
        ControleClienteV2.objects.filter(user=user)
        .filter(
            Q(tabulacao__isnull=False)
            | Q(agendamentos__isnull=False)
        )
        .distinct()
        .select_related('cliente', 'tabulacao', 'campanha')
    )

    if campanha_id:
        qs = qs.filter(campanha_id=campanha_id)

    itens = []
    for controle in qs.order_by('-updated_at')[:200]:
        ficha = resolver_dados_cliente(
            controle.cliente.cpf,
            controle.cliente.tipo,
            controle.cliente.dados_json,
        )
        ag = (
            controle.agendamentos.filter(status=AgendamentoV2.STATUS_EM_ESPERA)
            .order_by('dia_agendamento', 'hora')
            .first()
        )
        if not ag:
            ag = controle.agendamentos.order_by('-dia_agendamento', '-hora').first()

        ag_texto = '—'
        if ag:
            ag_texto = f'{ag.dia_agendamento.strftime("%d/%m/%Y")} {ag.hora.strftime("%H:%M")}'

        itens.append({
            'controle_id': controle.id,
            'cliente_id': controle.cliente_id,
            'cpf': controle.cliente.cpf,
            'nome': extrair_nome_ficha(ficha),
            'agendamento': ag_texto,
            'tabulacao': controle.tabulacao.nome if controle.tabulacao else '—',
            'tabulado': controle.tabulacao_id is not None,
            'tipo': controle.cliente.tipo,
            'campanha_id': controle.campanha_id,
            'campanha_nome': controle.campanha.nome,
        })

    return itens


def listar_agendamentos_usuario(user, campanha_id: int | None = None) -> list[dict]:
    qs = AgendamentoV2.objects.filter(
        controle__user=user,
        status=AgendamentoV2.STATUS_EM_ESPERA,
    ).select_related('controle__cliente', 'controle__campanha')

    if campanha_id:
        qs = qs.filter(controle__campanha_id=campanha_id)

    return [
        {
            'id': a.id,
            'cpf': a.controle.cliente.cpf,
            'tipo': a.controle.cliente.tipo,
            'campanha': a.controle.campanha.nome,
            'dia': a.dia_agendamento.isoformat(),
            'hora': a.hora.strftime('%H:%M'),
            'responsavel': a.responsavel,
            'observacao': a.observacao,
        }
        for a in qs.order_by('dia_agendamento', 'hora')[:100]
    ]
