import csv
import io

from django.db import transaction

from apps.vendas.plus.models_v2 import CampanhaV2, ClienteCampanhaV2, ImportacaoCsvV2

from .utils import CPF_ALIASES, normalizar_chave_csv, normalizar_cpf


def detectar_coluna_cpf(colunas: list[str]) -> str | None:
    for col in colunas:
        if col in CPF_ALIASES:
            return col
    return None


def parse_csv_preview(conteudo: bytes, encoding: str = 'utf-8-sig') -> dict:
    """Lê CSV e retorna schema + linhas preview sem persistir."""
    try:
        texto = conteudo.decode(encoding)
    except UnicodeDecodeError:
        texto = conteudo.decode('latin-1')

    reader = csv.DictReader(io.StringIO(texto))
    if not reader.fieldnames:
        return {'ok': False, 'erro': 'CSV sem cabeçalho.'}

    colunas_raw = reader.fieldnames
    mapa = {c: normalizar_chave_csv(c) for c in colunas_raw}
    coluna_cpf = detectar_coluna_cpf(list(mapa.values()))
    if not coluna_cpf:
        return {'ok': False, 'erro': 'Coluna CPF não encontrada (use cpf, documento ou doc).'}

    rows = []
    for i, row in enumerate(reader):
        if i >= 100:
            break
        dados = {}
        cpf_val = None
        for raw, norm in mapa.items():
            val = (row.get(raw) or '').strip()
            if norm == coluna_cpf:
                cpf_val = normalizar_cpf(val)
            dados[norm] = val
        if cpf_val and len(cpf_val) == 11:
            rows.append({'cpf': cpf_val, 'dados_json': dados})

    return {
        'ok': True,
        'schema': list(mapa.values()),
        'coluna_cpf': coluna_cpf,
        'rows': rows,
        'total_preview': len(rows),
    }


@transaction.atomic
def confirmar_importacao_csv(
    campanha_id: int,
    conteudo: bytes,
    arquivo_nome: str,
    user,
) -> dict:
    try:
        texto = conteudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        texto = conteudo.decode('latin-1')

    reader = csv.DictReader(io.StringIO(texto))
    if not reader.fieldnames:
        return {'ok': False, 'erro': 'CSV sem cabeçalho.'}

    mapa = {c: normalizar_chave_csv(c) for c in reader.fieldnames}
    coluna_cpf = detectar_coluna_cpf(list(mapa.values()))
    if not coluna_cpf:
        return {'ok': False, 'erro': 'Coluna CPF não encontrada.'}

    campanha = CampanhaV2.objects.filter(pk=campanha_id).first()
    if not campanha:
        return {'ok': False, 'erro': 'Campanha não encontrada.'}

    criados = 0
    atualizados = 0
    for row in reader:
        dados = {}
        cpf_val = None
        for raw, norm in mapa.items():
            val = (row.get(raw) or '').strip()
            if norm == coluna_cpf:
                cpf_val = normalizar_cpf(val)
            dados[norm] = val
        if not cpf_val or len(cpf_val) != 11:
            continue
        _, created = ClienteCampanhaV2.objects.update_or_create(
            campanha=campanha,
            cpf=cpf_val,
            defaults={'tipo': 'OUTROS', 'dados_json': dados},
        )
        if created:
            criados += 1
        else:
            atualizados += 1

    ImportacaoCsvV2.objects.create(
        campanha=campanha,
        colunas_schema=list(mapa.values()),
        arquivo_nome=arquivo_nome,
        total_linhas=criados + atualizados,
        criado_por=user,
    )

    return {
        'ok': True,
        'criados': criados,
        'atualizados': atualizados,
        'total': criados + atualizados,
    }
