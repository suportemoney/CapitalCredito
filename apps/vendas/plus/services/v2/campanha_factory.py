from django.db import transaction

from apps.vendas.plus.models_v2 import ClienteCampanhaV2

from .gerador_siape import coletar_cpfs_siape
from .gerenciador import criar_campanha
from .utils import normalizar_cpf

BATCH_CRIAR_CPFS = 500


def _normalizar_cpfs_unicos(cpfs: list[str]) -> list[str]:
    vistos: set[str] = set()
    resultado: list[str] = []
    for cpf_raw in cpfs:
        cpf = normalizar_cpf(cpf_raw)
        if len(cpf) != 11 or cpf in vistos:
            continue
        vistos.add(cpf)
        resultado.append(cpf)
    return resultado


def _persistir_cpfs(nome: str, tipo: str, cpfs: set[str], equipes_ids: list[int]) -> dict:
    campanha = criar_campanha({
        'nome': nome,
        'tipo_campanha': tipo,
        'equipes_ids': equipes_ids or [],
    })
    cpfs_lista = _normalizar_cpfs_unicos(list(cpfs))
    criados = 0
    for i in range(0, len(cpfs_lista), BATCH_CRIAR_CPFS):
        lote = cpfs_lista[i:i + BATCH_CRIAR_CPFS]
        objs = [
            ClienteCampanhaV2(campanha=campanha, cpf=cpf, tipo=tipo)
            for cpf in lote
        ]
        criados += len(ClienteCampanhaV2.objects.bulk_create(objs, ignore_conflicts=True))
    if criados == 0 and cpfs_lista:
        criados = ClienteCampanhaV2.objects.filter(campanha=campanha).count()
    return {'campanha_id': campanha.id, 'criados': criados, 'total_cpfs': len(cpfs_lista)}


def iter_criar_campanha_com_cpfs(nome: str, cpfs: list[str], equipes_ids: list[int], tipo: str):
    """Gera eventos SSE enquanto cria campanha e vincula CPFs em lotes."""
    cpfs_lista = _normalizar_cpfs_unicos(cpfs)
    total = len(cpfs_lista)
    if not nome.strip():
        yield {'evento': 'error', 'ok': False, 'erro': 'Nome da campanha obrigatório.'}
        return
    if not equipes_ids:
        yield {'evento': 'error', 'ok': False, 'erro': 'Selecione ao menos uma equipe.'}
        return
    if total == 0:
        yield {'evento': 'error', 'ok': False, 'erro': 'Nenhum CPF válido para criar a campanha.'}
        return

    with transaction.atomic():
        campanha = criar_campanha({
            'nome': nome.strip(),
            'tipo_campanha': tipo,
            'equipes_ids': equipes_ids,
        })

    yield {'evento': 'start', 'total': total, 'campanha_id': campanha.id, 'nome': campanha.nome}

    for i in range(0, total, BATCH_CRIAR_CPFS):
        lote = cpfs_lista[i:i + BATCH_CRIAR_CPFS]
        with transaction.atomic():
            objs = [
                ClienteCampanhaV2(campanha=campanha, cpf=cpf, tipo=tipo)
                for cpf in lote
            ]
            ClienteCampanhaV2.objects.bulk_create(objs, ignore_conflicts=True)
        yield {
            'evento': 'progress',
            'processados': min(i + BATCH_CRIAR_CPFS, total),
            'total': total,
        }

    criados = ClienteCampanhaV2.objects.filter(campanha=campanha).count()
    yield {
        'evento': 'complete',
        'ok': True,
        'campanha_id': campanha.id,
        'criados': criados,
        'total_cpfs': total,
        'nome': campanha.nome,
    }


@transaction.atomic
def criar_campanha_siape_com_cpfs(nome: str, cpfs: list[str], equipes_ids: list[int]) -> dict:
    return _persistir_cpfs(nome, 'SIAPE', {normalizar_cpf(c) for c in cpfs}, equipes_ids)


@transaction.atomic
def criar_campanha_siape_de_filtros(nome: str, filtros: dict, equipes_ids: list[int]) -> dict:
    cpfs = coletar_cpfs_siape(filtros)
    if not cpfs:
        return {'ok': False, 'erro': 'Nenhum CPF encontrado com os filtros informados.'}
    return {'ok': True, **_persistir_cpfs(nome, 'SIAPE', cpfs, equipes_ids)}
