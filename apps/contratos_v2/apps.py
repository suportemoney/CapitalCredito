from django.apps import AppConfig


class ContratosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contratos_v2'
    # Label distinto do legado apps.operacional.contratos (tabelas contratos_* no MySQL).
    label = 'contratos_v2'
    verbose_name = 'Contratos (operacional v2)'

    def ready(self):
        # Registra receivers do módulo de signals (Validação [7] — limpeza de
        # arquivos físicos via post_delete em ClienteArquivo).
        from apps.contratos_v2 import signals  # noqa: F401
