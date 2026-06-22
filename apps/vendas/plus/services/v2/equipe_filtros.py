"""Filtros hierárquicos para atribuição de participantes em equipes Plus."""
from apps.rh.admin.models import Departamento, Empresa, Setor
from apps.rh.funcionarios.models import Funcionario


def listar_filtros_equipe_participantes() -> dict:
    empresas = list(
        Empresa.objects.filter(status=True).order_by('nome').values('id', 'nome')
    )
    departamentos = list(
        Departamento.objects.filter(status=True)
        .order_by('empresa__nome', 'nome')
        .values('id', 'nome', 'empresa_id')
    )
    setores = list(
        Setor.objects.filter(status=True)
        .order_by('departamento__nome', 'nome')
        .values('id', 'nome', 'departamento_id')
    )
    funcionarios = []
    qs = (
        Funcionario.objects.filter(
            status=True,
            usuario__isnull=False,
            usuario__is_active=True,
        )
        .select_related(
            'usuario',
            'dados_profissionais__empresa',
            'dados_profissionais__departamento',
            'dados_profissionais__setor',
            'dados_profissionais__cargo',
        )
        .order_by('nome_completo')
    )
    for func in qs:
        dp = getattr(func, 'dados_profissionais', None)
        funcionarios.append({
            'user_id': func.usuario_id,
            'nome': func.nome_completo,
            'apelido': func.apelido or (func.nome_completo.split()[0] if func.nome_completo else ''),
            'username': func.usuario.username,
            'empresa_id': dp.empresa_id if dp else None,
            'departamento_id': dp.departamento_id if dp else None,
            'setor_id': dp.setor_id if dp else None,
            'cargo': dp.cargo.nome if dp and dp.cargo else '',
        })
    return {
        'empresas': empresas,
        'departamentos': departamentos,
        'setores': setores,
        'funcionarios': funcionarios,
    }
