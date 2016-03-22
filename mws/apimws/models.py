from django.db import models
from sitesmanagement.models import Service


class Cluster(models.Model):
    name = models.CharField(max_length=100, primary_key=True)


class Host(models.Model):
    hostname = models.CharField(max_length=250, primary_key=True)
    cluster = models.ForeignKey(Cluster, related_name='hosts')


class AnsibleConfiguration(models.Model):
    service = models.ForeignKey(Service, related_name='ansible_configuration')
    key = models.CharField(max_length=250, db_index=True)
    value = models.TextField()

    class Meta:
        unique_together = ("service", "key")


class ApacheModule(models.Model):
    name = models.CharField(max_length=150, primary_key=True)
    description = models.CharField(max_length=250)
    available = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='apache_modules', blank=True)

    def __unicode__(self):
        return self.name


class PHPLib(models.Model):
    name = models.CharField(max_length=150, primary_key=True)
    description = models.CharField(max_length=250)
    available = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='php_libs', blank=True)

    def __unicode__(self):
        return self.name
