import uuid
from datetime import datetime
from itertools import chain
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models
import re
from os.path import splitext
import reversion
from ucamlookup.models import LookupGroup
from mwsauth.utils import get_users_of_a_group
from sitesmanagement.utils import is_camacuk, get_object_or_None, deprecated


class NetworkConfig(models.Model):
    NETWORK_CONFIGURATION_TYPES = (
        ('ipv4pub', 'Public IPv4 Only'),
        ('ipv4priv', 'Private IPv4 Only'),
        ('ipvxpub', 'Public IPv4 and IPv6'),
        ('ipvxpriv', 'Private IPv4 and IPv6'),
        ('ipv6', 'IPv6 Only'),
    )

    IPv4 = models.GenericIPAddressField(protocol='IPv4', unique=True, null=True, blank=True)
    IPv4_netmask = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    IPv4_gateway = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    IPv6 = models.GenericIPAddressField(protocol='IPv6', unique=True, null=True, blank=True)
    name = models.CharField(max_length=250, unique=True)
    type = models.CharField(max_length=50, choices=NETWORK_CONFIGURATION_TYPES)

    @classmethod
    def get_free_prod_service_config(cls):
        return cls.objects.filter(service=None, type='ipvxpub').first()

    @classmethod
    def get_free_test_service_config(cls):
        return cls.objects.filter(service=None, type='ipv4priv').first()

    @classmethod
    def get_free_host_config(cls):
        return cls.objects.filter(vm=None, type='ipv6').first()

    def __unicode__(self):
        return self.name


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
    end_date = models.DateField(null=True, blank=True)
    # is the site deleted?
    deleted = models.BooleanField(default=False)
    # webmaster email
    email = models.EmailField(null=False, blank=False)
    # Indicates if the user wants to renew or not their MWS3 subscription
    subscription = models.BooleanField(default=True)

    # Administrator users of a site
    users = models.ManyToManyField(User, related_name='sites')
    # SSH only users of a site
    ssh_users = models.ManyToManyField(User, related_name='sites_auth_as_user', blank=True)
    # Administrator groups of a site
    groups = models.ManyToManyField(LookupGroup, related_name='sites', blank=True)
    # SSH only groups
    ssh_groups = models.ManyToManyField(LookupGroup, related_name='sites_auth_as_user', blank=True)

    # Indicates if the site is disabled by the user
    disabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('showsite', args=[str(self.id)])

    def __unicode__(self):
        return self.name

    # @property
    # def virtual_machines(self):
    #     return VirtualMachine.objects.filter(service__site_id=self.id)

    def is_admin_suspended(self):
        for susp in self.suspensions.all():
            if susp.active:
                return True
        return False

    def is_canceled(self):
        return self.end_date is not None

    def is_disabled(self):
        return self.disabled

    def suspend_now(self, input_reason):
        return Suspension.objects.create(reason=input_reason, start_date=datetime.today(), site=self)

    @property
    def vms(self):
        return VirtualMachine.objects.filter(service__site=self)

    @property
    def production_vms(self):
        return self.vms.filter(service__type='production')

    @property
    def test_vms(self):
        return self.vms.filter(service__type='test')

    @property
    def production_service(self):
        return Service.objects.filter(type='production', site=self).first()

    @property
    def test_service(self):
        return Service.objects.filter(type='test', site=self).first()

    @property
    @deprecated
    def primary_vm(self):
        return self.vms.filter(service__type='production').first()

    @property
    @deprecated
    def secondary_vm(self):
        return self.vms.filter(service__type='test').first()

    @property
    def domain_names(self):
        return DomainName.objects.filter(vhost__service=self.production_service)

    def cancel(self):
        self.end_date = datetime.today()
        self.users.clear()
        self.ssh_users.clear()
        self.groups.clear()
        self.ssh_groups.clear()
        self.save()
        if self.production_service:
            self.production_service.power_off()
        if self.test_service:
            self.test_service.power_off()

    def disable(self):
        self.disabled = True
        self.save()
        if self.production_service:
            self.production_service.power_off()
        if self.test_service:
            self.test_service.power_off()

    def enable(self):
        self.disabled = False
        self.save()
        if self.production_service:
            self.production_service.power_on()
        if self.test_service:
            self.test_service.power_on()

    @property
    def is_busy(self):
        if self.production_service and self.production_service.is_busy:
            return True
        if self.test_service and self.test_service.is_busy:
            return True
        if not self.production_service and not self.test_service:
            return True
        return False

    @property
    def is_ready(self):
        if self.production_service and not self.production_service.is_ready:
            return False
        if self.test_service and not self.test_service.is_ready:
            return False
        if not self.production_service and not self.test_service:
            return False
        return True

    def list_of_admins(self):
        list_of_admins_in_lookup_groups = list(chain.from_iterable(map(get_users_of_a_group, self.groups.all())))
        list_of_admins_directly_assigned = list(self.users.all())
        return list(set(list_of_admins_in_lookup_groups + list_of_admins_directly_assigned))

    def list_of_ssh_users(self):
        list_of_ssh_users_in_lookup_groups = list(chain.from_iterable(map(get_users_of_a_group, self.ssh_groups.all())))
        list_of_ssh_users_directly_assigned = list(self.ssh_users.all())
        final_list_of_ssh_users = list(set(list_of_ssh_users_in_lookup_groups + list_of_ssh_users_directly_assigned))
        return [item for item in final_list_of_ssh_users if item not in self.list_of_admins()]

    def list_of_all_type_of_users(self):
        list_of_ssh_users_in_lookup_groups = list(chain.from_iterable(map(get_users_of_a_group, self.ssh_groups.all())))
        list_of_ssh_users_directly_assigned = list(self.ssh_users.all())
        final_list_of_ssh_users = list_of_ssh_users_in_lookup_groups + list_of_ssh_users_directly_assigned
        final_list_of_all_type_of_users = final_list_of_ssh_users + self.list_of_admins()
        return list(set(final_list_of_all_type_of_users))

    def list_of_active_admins(self):
        return filter(lambda user: user.is_active, self.list_of_admins())

    def list_of_active_ssh_users(self):
        return filter(lambda user: user.is_active, self.list_of_ssh_users())

    def list_of_all_type_of_active_users(self):
        return filter(lambda user: user.is_active, self.list_of_all_type_of_users())


class EmailConfirmation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
    )

    email = models.EmailField(null=True, blank=True)
    token = models.CharField(max_length=50)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    site = models.OneToOneField(Site, related_name='+')  # do not to create a backwards relation


class Suspension(models.Model):
    reason = models.CharField(max_length=250)
    # is the suspension active?
    active = models.BooleanField(default=True)
    # start date of the suspension
    start_date = models.DateField()
    # end date of the suspension
    end_date = models.DateField(null=True, blank=True)
    site = models.ForeignKey(Site, related_name="suspensions")


def validate_file_extension(value):
    if splitext(value.name)[1] != '.pdf':
        raise ValidationError(u'Only PDF files are accepted.')


class Billing(models.Model):
    purchase_order_number = models.CharField(max_length=100)
    purchase_order = models.FileField(upload_to='billing', validators=[validate_file_extension])
    group = models.CharField(max_length=250)
    site = models.OneToOneField(Site, related_name='billing')
    date_created = models.DateField(auto_now_add=True)
    date_modified = models.DateField(auto_now=True)
    date_sent_to_finance = models.DateField(null=True, blank=True)


def full_domain_validator(hostname):
    """
    Fully validates a domain name as compilant with the standard rules:
        - Composed of series of labels concatenated with dots, as are all domain names.
        - Each label must be between 1 and 63 characters long.
        - The entire hostname (including the delimiting dots) has a maximum of 255 characters.
        - Only characters 'a' through 'z' (in a case-insensitive manner), the digits '0' through '9'.
        - Labels can't start or end with a hyphen.
    """
    HOSTNAME_LABEL_PATTERN = re.compile("(?!-)[A-Z\d-]+(?<!-)$", re.IGNORECASE)
    if not hostname:
        return
    if len(hostname) > 255:
        raise ValidationError("The domain name cannot be composed of more than 255 characters.")
    if hostname[-1:] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    for label in hostname.split("."):
        if len(label) > 63:
            raise ValidationError(
                "The label '%(label)s' is too long (maximum is 63 characters)." % {'label': label})
        if not HOSTNAME_LABEL_PATTERN.match(label):
            raise ValidationError("Unallowed characters in label '%(label)s'. Domain names may be formed from the set "
                                  "of alphanumeric ASCII characters (a-z, A-Z, 0-9), but characters are "
                                  "case-insensitive. In addition the hyphen is permitted if it is surrounded by a "
                                  "characters or digits, i.e., it is not the start or end of a label. Labels are "
                                  "always separated by the full stop (period) character in the textual name "
                                  "representation." % {'label': label})


class Service(models.Model):
    SERVICE_TYPES = (
        ('production', 'Production'),
        ('test', 'Test'),
    )
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
        ('installing', 'Installing OS'),
        ('postinstall', 'Post Installing OS'),
        ('ansible', 'Running Ansible'),
        ('ansible_queued', 'Ansible queued'),
        ('ready', 'Ready'),
    )
    # The network configuration for the service
    network_configuration = models.OneToOneField(NetworkConfig, null=True, blank=True)
    site = models.ForeignKey(Site, null=True, blank=True)
    type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    @property
    def operating_system(self):
        from apimws.models import AnsibleConfiguration
        ansible_configuraton = get_object_or_None(AnsibleConfiguration, service=self, key="os")
        return ansible_configuraton.value if ansible_configuraton else None

    def due_update(self):
        return self.operating_system in getattr(settings, 'OS_DUE_UPGRADE', [])

    @property
    def is_busy(self):
        return self.virtual_machines.count() > 0 and self.status != 'ready' \
               and self.status != 'ansible' and self.status != 'ansible_queued'

    @property
    def is_ready(self):
        return self.status is None or self.status == '' or self.status == 'ready'

    @property
    def primary(self):
        return self.type == 'production'

    @property
    def active(self):
        return self.virtual_machines.count() > 0

    @property
    def ipv4(self):
        return self.network_configuration.IPv4

    @property
    def ipv6(self):
        return self.network_configuration.IPv6

    @property
    def hostname(self):
        return self.network_configuration.name

    @property
    def all_domain_names(self):
        domains = []
        for vhost in self.vhosts.all():
            for domain in vhost.domain_names.all():
                domains.append(domain)
        return domains

    def do_reset(self):
        result = True
        for vm in self.virtual_machines.all():
            result = result and vm.do_reset()
        return result

    def power_on(self):
        for vm in self.virtual_machines.all():
            vm.power_on()

    def power_off(self):
        for vm in self.virtual_machines.all():
            vm.power_off()

    class Meta:
        unique_together = (("site", "type"), ("network_configuration", ), )

    def __unicode__(self):
        if self.network_configuration is None:
            return "Non active service"
        else:
            return self.network_configuration.name


class VirtualMachine(models.Model):
    """ A virtual machine is associated to a site and has a network configuration. Its attributes include
        a name and a boolean to indicate if it's the primary or secondary VM of a Site.
    """

    name = models.CharField(max_length=250, blank=True, null=True)
    token = models.CharField(max_length=50)

    network_configuration = models.OneToOneField(NetworkConfig, related_name="vm", unique=True)
    service = models.ForeignKey(Service, related_name='virtual_machines')

    @property
    def site(self):
        if self.service and self.service.site:
            return self.service.site
        else:
            return None

    @property
    def operating_system(self):
        return self.service.operating_system

    def power_on(self):
        from apimws.vm import change_vm_power_state
        change_vm_power_state.delay(self.id, 'on')

    def power_off(self):
        from apimws.vm import change_vm_power_state
        change_vm_power_state.delay(self.id, 'off')

    def do_reset(self):
        from apimws.vm import reset_vm
        return not reset_vm.delay(self.id).failed()

    @property
    def primary(self):
        if self.service:
            return self.service.primary

    @property
    def ipv4(self):
        return self.network_configuration.IPv4

    @property
    def ipv6(self):
        return self.network_configuration.IPv6

    @property
    def hostname(self):
        return self.network_configuration.name

    def __unicode__(self):
        if self.name is None:
            return "<Under request>"
        else:
            return self.name


class Vhost(models.Model):
    WEBAPP_CHOICES = (
        ('wordpress', 'Wordpress'),
    )
    name = models.CharField(max_length=150, validators=[validate_slug])
    # main domain name for this vhost
    main_domain = models.ForeignKey('DomainName', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    service = models.ForeignKey(Service, related_name='vhosts')
    csr = models.TextField(null=True, blank=True)
    certificate = models.TextField(null=True, blank=True)
    tls_key_hash = models.TextField(null=True, blank=True)
    tls_enabled = models.BooleanField(default=False)
    webapp = models.CharField(max_length=100, choices=WEBAPP_CHOICES, null=True, blank=True)

    def sorted_domain_names(self):
        return sorted(set(self.domain_names.all()))

    class Meta:
        unique_together = ("name", "service")

    def __unicode__(self):
        return self.name


class DomainName(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('external', 'External'),
        ('denied', 'Denied'),
    )

    name = models.CharField(max_length=250, unique=True, validators=[full_domain_validator])
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='requested')
    vhost = models.ForeignKey(Vhost, related_name='domain_names')
    requested_by = models.ForeignKey(User, related_name='domain_names_requested', blank=True, null=True)
    reject_reason = models.CharField(max_length=250, blank=True, null=True)
    token = models.CharField(max_length=32, default=uuid.uuid4)
    authorised_by = models.ForeignKey(User, related_name='domain_names_authorised', blank=True, null=True)

    def __unicode__(self):
        return self.name


class UnixGroup(models.Model):
    name = models.CharField(max_length=16)  # TODO add validator to comply with Debian guidelines of Unix group names
    service = models.ForeignKey(Service, related_name='unix_groups')
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return self.name


class SiteKey(models.Model):
    ALGORITHMS = {
        'RSA': 1,
        'DSA': 2,
        'ECDSA': 3,
        'ED25519': 4
    }
    FP_TYPES = {
        'SHA-1': 1,
        'SHA-256': 2
    }
    type = models.CharField(max_length=100)
    public_key = models.TextField()
    fingerprint = models.CharField(max_length=250, null=True)
    site = models.ForeignKey(Site, related_name="keys")

    class Meta:
        unique_together = (("site", "type"), )


def no_date_validator(name):
    """
    Validates that the name is not a data in iso format to avoid clashes with daily snapshots
    """
    PATTERN = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    if PATTERN.match(name):
        raise ValidationError("Do not use a data format for the snapshot name")


class Snapshot(models.Model):
    name = models.CharField(max_length=50, validators=[validate_slug, no_date_validator])
    date = models.DateTimeField(auto_now_add=True)
    service = models.ForeignKey(to=Service, related_name="snapshots")
    pending_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = (("name", "service"), )


reversion.register(Service, follow=["unix_groups", "ansible_configuration", "vhosts", "virtual_machines"])
reversion.register(VirtualMachine, follow=["service"])
reversion.register(Vhost, follow=["domain_names", "service"])
reversion.register(DomainName, follow=["vhost"])
reversion.register(UnixGroup, follow=["service"])
