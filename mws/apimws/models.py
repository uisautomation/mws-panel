from django import forms
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from apimws.platforms import destroy_vm, change_vm_power_state
from sitesmanagement.models import VirtualMachine


class AnsibleConfiguration(models.Model):
    vm = models.ForeignKey(VirtualMachine)
    key = models.CharField(max_length=250, db_index=True)
    value = models.TextField()


@receiver(pre_delete, sender=VirtualMachine)
def api_call_to_delete_vm(instance, **kwargs):
    change_vm_power_state(instance, "off")
    destroy_vm(instance)