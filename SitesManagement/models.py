from django.contrib.auth.models import User, Group
from django.db import models


class Site(models.Model):
    # Name of the site
    name = models.CharField(max_length=100, unique=True)
    # Description of the site
    description = models.CharField(max_length=250, blank=True)
    # The institution (retrieved using lookup)
    institution_id = models.CharField(max_length=100, validators=[validate_correct_institution])
    # Suspended site?
    suspended = models.BooleanField(default=False)
    # Administratively suspended site?
    admin_suspended = models.BooleanField(default=False)


    # Authorised users per site
    users = models.ManyToManyField(User, related_name='sites')
    # Authorised user groups per site
    group = models.ManyToManyField(Group, related_name='sites', null=True)



class DomainName(models.Model):
    name = models.CharField(max_length=250, unique=True)
    network_configuration = models.ForeignKey(NetworkConfig)


class ContactEmail(models.Model):
    email = models.EmailField()
    site = models.ForeignKey(Site)


class Billing(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    purchase_order = models.FileField()
    group = models.CharField(max_length=250)
    site = models.OneToOneField(Site, related_name='billing')


class NetworkConfig(models.Model):
    """ The network configuration for a VM (IPv4, IPv6, and domain name associated
    """
    IPv4 = models.GenericIPAddressField(protocol='IPv4')
    IPv6 = models.GenericIPAddressField(protocol='IPv6')
    main_domain = models.OneToOneField(DomainName, related_name="network_configuration")


class VirtualMachine(models.Model):
    """ A virtual machine is associated to a site and has a network configuration. Its attributes include
        a name and a boolean to indicate if it's the primary or secondary VM of a Site.
    """
    name = models.CharField(max_length=250)
    primary = models.BooleanField(default=True)
    network_configuration = models.OneToOneField(NetworkConfig, null=True, related_name='virtual_machine')
    site = models.ForeignKey(Site, null=True, related_name='virtual_machine')