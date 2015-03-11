from django import forms
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from apimws.platforms import destroy_vm
from sitesmanagement.models import VirtualMachine, Service


class AnsibleConfiguration(models.Model):
    service = models.ForeignKey(Service, related_name='ansible_configuration')
    key = models.CharField(max_length=250, db_index=True)
    value = models.TextField()

    class Meta:
        unique_together = ("service", "key")


@receiver(pre_delete, sender=VirtualMachine)
def api_call_to_delete_vm(instance, **kwargs):
    if instance.name:
        if instance.site:
            destroy_vm.delay(instance)
        else:
            destroy_vm(instance)
