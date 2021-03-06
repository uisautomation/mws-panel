from django.conf import settings
from django.db import models
from sitesmanagement.models import Service, Site


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
    """
    A model to represent a PHP library
    """
    name = models.CharField(max_length=150, primary_key=True)
    description = models.CharField(max_length=250)
    available = models.BooleanField(default=True)
    services = models.ManyToManyField(Service, related_name='php_libs', blank=True)

    def __unicode__(self):
        return self.name

class PHPPackage(models.Model):
    """
    A model representing a PHP library operating system package
    """
    OS_CHOICES = (
        ('jessie', 'Debian 8 (jessie)'),
        ('stretch', 'Debian 9 (stretch)'),
    )
    name = models.CharField(max_length=150, blank=False, null=False)
    library = models.ForeignKey(PHPLib, related_name='packages')
    os = models.CharField(max_length=40, choices=OS_CHOICES, blank=False, null=False)

    class Meta:
        unique_together = ("name", "os")

    def __unicode__(self):
        return self.name

class QueueEntry(models.Model):
    """
    Instances of this model form a simple FIFO queue of sites ordered by instance
    creation date, currently used to queue operating system upgrades.
    """
    site = models.OneToOneField(Site, on_delete=models.CASCADE, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']

    def __unicode__(self):
        return self.site.name
