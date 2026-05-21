from django.apps import AppConfig


class FinanceiroGeralConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tesouraria.financeiro_geral'

    def ready(self):
        import apps.tesouraria.financeiro_geral.signals  # noqa: F401
