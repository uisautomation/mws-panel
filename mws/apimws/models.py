from django.conf import settings
from django.db import models
from sitesmanagement.models import Service


class Cluster(models.Model):
    name = models.CharField(max_length=100, primary_key=True)

    def __unicode__(self):
        return self.name


class Host(models.Model):
    hostname = models.CharField(max_length=250, primary_key=True)
    cluster = models.ForeignKey(Cluster, related_name='hosts')

    def __unicode__(self):
        return self.hostname


class AnsibleConfiguration(models.Model):
    service = models.ForeignKey(Service, related_name='ansible_configuration')
    key = models.CharField(max_length=250, db_index=True)
    value = models.TextField()

    class Meta:
        unique_together = ("service", "key")


class PHPLib(models.Model):
    name = models.CharField(max_length=150, primary_key=True)
    name_next_os = models.CharField(max_length=150, blank=True)
    description = models.CharField(max_length=250)
    available = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='php_libs', blank=True)

    def os_dep_name(self, service):
        """
        :param service: the target Service
        :return: the correct name of the php lib for the OS version of a service
        """
        if service.operating_system == settings.NEXT_OS:
            return self.name_next_os
        return self.name

    def __unicode__(self):
        return self.name
