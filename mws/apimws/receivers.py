from django.db.models.signals import pre_delete
from django.dispatch import receiver
from apimws.vm import destroy_vm
from sitesmanagement.models import VirtualMachine


@receiver(pre_delete, sender=VirtualMachine)
def api_call_to_delete_vm(instance, **kwargs):
    if instance.name:
        destroy_vm(instance.id)
