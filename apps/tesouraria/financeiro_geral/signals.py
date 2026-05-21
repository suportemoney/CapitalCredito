from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Conta, Salario, Beneficio

@receiver(post_save, sender=Conta)
def _conta_saved(sender, **kwargs):
    from .apis.sse import push_contas_notificacao_count
    push_contas_notificacao_count()

@receiver(post_save, sender=Salario)
def _salario_saved(sender, **kwargs):
    from .apis.sse import push_contas_notificacao_count
    push_contas_notificacao_count()

@receiver(post_save, sender=Beneficio)
def _beneficio_saved(sender, **kwargs):
    from .apis.sse import push_contas_notificacao_count
    push_contas_notificacao_count()
