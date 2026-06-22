from django.db import transaction

from apps.vendas.plus.models import Equipe, StatusChoice
from apps.vendas.plus.models_v2 import CampanhaV2, ClienteCampanhaV2

from .utils import normalizar_cpf


def listar_equipes() -> list[dict]:
    return [
        {
            'id': e.id,
            'nome': e.nome,
            'status': e.status,
            'participantes_count': e.participantes.count(),
            'participantes': [
                {
                    'id': p.id,
                    'username': p.username,
                    'nome': (f'{p.first_name} {p.last_name}'.strip() or p.username),
                }
                for p in e.participantes.all()
            ],
        }
        for e in Equipe.objects.prefetch_related('participantes').order_by('-data_criacao')
    ]


def listar_campanhas(tipo: str | None = None) -> list[dict]:
    qs = CampanhaV2.objects.prefetch_related('equipes').order_by('-data_criacao')
    if tipo:
        qs = qs.filter(tipo_campanha=tipo.upper())
    return [
        {
            'id': c.id,
            'nome': c.nome,
            'descricao': c.descricao,
            'status': c.status,
            'tipo_campanha': c.tipo_campanha,
            'equipes': list(c.equipes.values_list('id', flat=True)),
            'clientes_count': c.clientes.count(),
        }
        for c in qs
    ]


def listar_status_choices() -> list[dict]:
    return list(
        StatusChoice.objects.filter(status_booleano=True)
        .order_by('order', 'nome')
        .values('id', 'nome', 'cor_tag', 'impacto', 'conversao', 'order')
    )


def listar_clientes_campanha(campanha_id: int) -> list[dict]:
    return [
        {
            'id': c.id,
            'cpf': c.cpf,
            'tipo': c.tipo,
            'tem_json': bool(c.dados_json),
        }
        for c in ClienteCampanhaV2.objects.filter(campanha_id=campanha_id).order_by('cpf')
    ]


@transaction.atomic
def criar_campanha(dados: dict) -> CampanhaV2:
    campanha = CampanhaV2.objects.create(
        nome=dados['nome'],
        descricao=dados.get('descricao', ''),
        tipo_campanha=dados.get('tipo_campanha', 'MISTA'),
        status=dados.get('status', True),
    )
    equipes_ids = dados.get('equipes_ids', [])
    if equipes_ids:
        campanha.equipes.set(equipes_ids)
    return campanha


@transaction.atomic
def adicionar_clientes_campanha(campanha_id: int, clientes: list[dict]) -> dict:
    campanha = CampanhaV2.objects.get(pk=campanha_id)
    criados = 0
    for item in clientes:
        cpf = normalizar_cpf(item.get('cpf', ''))
        tipo = (item.get('tipo') or campanha.tipo_campanha).upper()
        if tipo == 'MISTA':
            tipo = item.get('tipo', 'OUTROS').upper()
        if not cpf or len(cpf) != 11:
            continue
        _, created = ClienteCampanhaV2.objects.get_or_create(
            campanha=campanha,
            cpf=cpf,
            defaults={'tipo': tipo},
        )
        if created:
            criados += 1
    return {'criados': criados}


@transaction.atomic
def criar_equipe(nome: str, participantes_ids: list[int] | None = None) -> Equipe:
    equipe = Equipe.objects.create(nome=nome, status=True)
    if participantes_ids:
        equipe.participantes.set(participantes_ids)
    return equipe


@transaction.atomic
def atualizar_equipe(
    equipe_id: int,
    nome: str | None = None,
    status: bool | None = None,
    participantes_ids: list[int] | None = None,
) -> Equipe | None:
    equipe = Equipe.objects.filter(pk=equipe_id).first()
    if not equipe:
        return None
    if nome is not None:
        equipe.nome = nome.strip()
    if status is not None:
        equipe.status = status
    equipe.save()
    if participantes_ids is not None:
        equipe.participantes.set(participantes_ids)
    return equipe


def alterar_status_campanha(campanha_id: int, status: bool) -> bool:
    updated = CampanhaV2.objects.filter(pk=campanha_id).update(status=status)
    return updated > 0


@transaction.atomic
def atualizar_campanha(campanha_id: int, dados: dict) -> CampanhaV2 | None:
    campanha = CampanhaV2.objects.filter(pk=campanha_id).first()
    if not campanha:
        return None
    if dados.get('nome') is not None:
        nome = str(dados['nome']).strip()
        if nome:
            campanha.nome = nome
    if 'descricao' in dados:
        campanha.descricao = dados.get('descricao') or ''
    if 'equipes_ids' in dados:
        campanha.equipes.set(dados['equipes_ids'] or [])
    campanha.save()
    return campanha
