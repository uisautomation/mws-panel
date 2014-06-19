from django.contrib.auth.models import User, Group
from django.db import models


class Site(models.Model):
    # Name of the site
    name = models.CharField(max_length=100, unique=True)
    # Description of the site
    description = models.CharField(max_length=250, blank=True)
    # The institution (retrieved using lookup)
    institution_id = models.CharField(max_length=100)
    # Start date of the site
    start_date = models.DateField()
    # End date of the site (when user decides to delete the site)
    end_date = models.DateField(null=True)
    # is the site deleted?
    deleted = models.BooleanField(default=False)
    # webmaster email
    email = models.EmailField(null=True)

    # Authorised users per site
    users = models.ManyToManyField(User, related_name='sites')
    # Authorised user groups per site
    group = models.ManyToManyField(Group, related_name='sites', null=True)


class Suspension(models.Model):
    reason = models.CharField(max_length=250)
    # is the suspension active?
    active = models.BooleanField(default=True)
    # start date of the suspension
    start_date = models.DateField()
    # end date of the suspension
    end_date = models.DateField(null=True)

    site = models.ForeignKey(Site, related_name="suspensions")


class Billing(models.Model):
    purchase_order = models.FileField()
    group = models.CharField(max_length=250)
    site = models.OneToOneField(Site, related_name='billing')


class DomainName(models.Model):
    name = models.CharField(max_length=250, unique=True)
    site = models.ForeignKey(Site, related_name='domain_names', null=True)


class NetworkConfig(models.Model):
    """ The network configuration for a VM (IPv4, IPv6, and domain name associated
    """
    IPv4 = models.GenericIPAddressField(protocol='IPv4')
    IPv6 = models.GenericIPAddressField(protocol='IPv6')
    main_domain = models.OneToOneField(DomainName)


class VirtualMachine(models.Model):
    """ A virtual machine is associated to a site and has a network configuration. Its attributes include
        a name and a boolean to indicate if it's the primary or secondary VM of a Site.
    """
    name = models.CharField(max_length=250)
    primary = models.BooleanField(default=True)

    network_configuration = models.OneToOneField(NetworkConfig, related_name='virtual_machine')
    site = models.ForeignKey(Site, related_name='virtual_machines')