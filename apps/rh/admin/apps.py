from django.apps import AppConfig


class AdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rh.admin'
    label = 'rh_admin'
    verbose_name = 'RH Administrativo'
