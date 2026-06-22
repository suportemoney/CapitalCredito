from apps.vendas.siape.models import Cliente, Contrato, Matricula

from .utils import normalizar_cpf, serializar_decimal


def _filtrar_contratos(matricula) -> list:
    """Retorna contratos de campanhas ativas, no máximo um por número de contrato."""
    qs = (
        Contrato.objects.filter(matricula=matricula, campanha__status=True)
        .select_related('campanha', 'matricula')
        .order_by('-campanha__data_criacao', '-id')
    )

    vistos: set[str] = set()
    resultado: list = []
    for contrato in qs:
        num_contrato = (contrato.contrato or '').strip()
        if num_contrato:
            if num_contrato in vistos:
                continue
            vistos.add(num_contrato)
        resultado.append(contrato)
        if len(resultado) >= 50:
            break
    return resultado


def _serializar_contrato(contrato: Contrato) -> dict:
    matricula = contrato.matricula
    return {
        'matricula': matricula.matricula if matricula else None,
        'banco': contrato.banco,
        'orgao': matricula.orgao if matricula else None,
        'rebrica': matricula.rubrica if matricula else None,
        'parcela': serializar_decimal(contrato.valor_parcela),
        'prazo_restante': contrato.parcelas_restantes,
        'tipo_contrato': contrato.tipo_contrato,
        'num_contrato': contrato.contrato,
    }


def _escolher_matricula(cliente) -> Matricula | None:
    return (
        Matricula.objects.filter(cliente=cliente, status=True, campanha__status=True)
        .select_related('campanha', 'margens')
        .order_by('-data_criacao')
        .first()
    )


def _total_util_margens(margens) -> float | None:
    if not margens:
        return None
    campos = (margens.util_35, margens.util_5, margens.util_5b)
    if all(v is None for v in campos):
        return None
    total = sum(v for v in campos if v is not None)
    return serializar_decimal(total)


def build_payload_siape(cpf: str) -> dict:
    """Monta ficha SIAPE a partir dos modelos CapitalCredito (Cliente → Matricula → Margens/Contrato)."""
    cpf_n = normalizar_cpf(cpf)
    cliente = Cliente.objects.filter(cpf=cpf_n, status=True).first()
    if not cliente:
        return {'encontrado': False, 'cpf': cpf_n, 'tipo': 'SIAPE'}

    matricula = _escolher_matricula(cliente)
    margens = matricula.margens if matricula and hasattr(matricula, 'margens') else None
    debitos = _filtrar_contratos(matricula) if matricula else []

    telefones = []
    if cliente.celular:
        telefones.append({'numero': cliente.celular, 'tipo': 'CELULAR', 'principal': True})

    return {
        'encontrado': True,
        'tipo': 'SIAPE',
        'schema': 'fixo_siape',
        'pessoal': {
            'nome': cliente.nome,
            'cpf': cliente.cpf,
            'uf': cliente.uf,
            'rjur': matricula.rjur if matricula else None,
            'situacao_funcional': cliente.situacao_funcional,
            'data_nascimento': None,
        },
        'margens': {
            'renda_bruta': serializar_decimal(matricula.base_calculo) if matricula else None,
            'bruta_5': serializar_decimal(margens.bruta_5) if margens else None,
            'util_5': serializar_decimal(margens.util_5) if margens else None,
            'saldo_5': serializar_decimal(margens.saldo_5) if margens else None,
            'bruta_beneficio_5': serializar_decimal(margens.bruta_5b) if margens else None,
            'util_beneficio_5': serializar_decimal(margens.util_5b) if margens else None,
            'saldo_beneficio_5': serializar_decimal(margens.saldo_5b) if margens else None,
            'bruta_35': serializar_decimal(margens.bruta_35) if margens else None,
            'util_35': serializar_decimal(margens.util_35) if margens else None,
            'saldo_35': serializar_decimal(margens.saldo_35) if margens else None,
            'total_util': _total_util_margens(margens),
            'total_saldo': (
                serializar_decimal(
                    (margens.saldo_35 or 0) + (margens.saldo_5 or 0) + (margens.saldo_5b or 0)
                )
                if margens else None
            ),
        },
        'debitos': [_serializar_contrato(d) for d in debitos],
        'telefones': telefones,
    }
