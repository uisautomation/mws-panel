from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from apimws.vm import destroy_vm
from sitesmanagement.models import VirtualMachine, Service


class AnsibleConfiguration(models.Model):
    service = models.ForeignKey(Service, related_name='ansible_configuration')
    key = models.CharField(max_length=250, db_index=True)
    value = models.TextField()

    class Meta:
        unique_together = ("service", "key")


class ApacheModules(models.Model):
    name = models.CharField(max_length=150, primary_key=True)
    description = models.CharField(max_length=250)
    available = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='apache_modules', blank=True)

    def __unicode__(self):
        return self.name


class PHPLibs(models.Model):
    name = models.CharField(max_length=150, primary_key=True)
    description = models.CharField(max_length=250)
    available = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='php_libs', blank=True)

    def __unicode__(self):
        return self.name


@receiver(pre_delete, sender=VirtualMachine)
def api_call_to_delete_vm(instance, **kwargs):
    if instance.name:
        if instance.site:
            destroy_vm.delay(instance)
        else:
            destroy_vm(instance)
