from django.db.models import Count, Q
from django.utils import timezone

from apps.vendas.plus.models_v2 import AgendamentoV2, CampanhaV2, ControleClienteV2

from .distribuicao import campanhas_do_usuario


def build_esteira_kpis(user, campanha_id: int | None = None) -> dict:
    hoje = timezone.now().date()
    campanhas = campanhas_do_usuario(user)
    campanha_ids = [c.id for c in campanhas]

    if campanha_id:
        campanha_ids = [campanha_id] if campanha_id in campanha_ids else []

    controles = ControleClienteV2.objects.filter(user=user, campanha_id__in=campanha_ids)

    tabulados_hoje = controles.filter(
        updated_at__date=hoje,
        tabulacao__isnull=False,
    ).count()

    agendamentos_pendentes = AgendamentoV2.objects.filter(
        controle__user=user,
        controle__campanha_id__in=campanha_ids,
        status=AgendamentoV2.STATUS_EM_ESPERA,
        dia_agendamento__gte=hoje,
    ).count()

    total_trabalhados = controles.filter(tabulacao__isnull=False).count()
    total_conversao = controles.filter(tabulacao__conversao=True).count()
    taxa_conversao = round((total_conversao / total_trabalhados * 100), 1) if total_trabalhados else 0

    clientes_campanha_ativa = 0
    if campanha_ids:
        from apps.vendas.plus.models_v2 import ClienteCampanhaV2
        clientes_campanha_ativa = ClienteCampanhaV2.objects.filter(
            campanha_id=campanha_ids[0]
        ).count()

    return {
        'tabulados_hoje': tabulados_hoje,
        'agendamentos_pendentes': agendamentos_pendentes,
        'taxa_conversao': taxa_conversao,
        'clientes_campanha': clientes_campanha_ativa,
        'campanhas_ativas': len(campanha_ids),
        'total_trabalhados': total_trabalhados,
    }
