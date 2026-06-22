import csv
import io

from .utils import normalizar_chave_csv, normalizar_cpf


def extrair_cpfs_csv(conteudo: bytes) -> dict:
    """Extrai CPFs de CSV com coluna A cabeçalho CPF."""
    try:
        texto = conteudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        texto = conteudo.decode('latin-1')

    reader = csv.reader(io.StringIO(texto))
    try:
        header = next(reader)
    except StopIteration:
        return {'ok': False, 'erro': 'CSV vazio.'}

    if not header:
        return {'ok': False, 'erro': 'CSV sem cabeçalho.'}

    if normalizar_chave_csv(header[0]) != 'cpf':
        return {'ok': False, 'erro': 'Coluna A deve ter cabeçalho "CPF".'}

    cpfs: list[str] = []
    invalidos = 0
    for row in reader:
        if not row:
            continue
        cpf = normalizar_cpf(row[0])
        if len(cpf) == 11:
            cpfs.append(cpf)
        else:
            invalidos += 1

    # Mantém ordem e remove duplicados
    cpfs_unicos = list(dict.fromkeys(cpfs))
    if not cpfs_unicos:
        return {'ok': False, 'erro': 'Nenhum CPF válido encontrado no arquivo.'}

    return {
        'ok': True,
        'cpfs': cpfs_unicos,
        'total': len(cpfs_unicos),
        'invalidos': invalidos,
    }
