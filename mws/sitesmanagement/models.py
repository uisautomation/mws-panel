import uuid
import re
import reversion
from datetime import datetime, timedelta, date
from itertools import chain
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import now
from os.path import splitext
from ucamlookup.models import LookupGroup
from apimws.ipreg import DomainNameDelegatedException
from mwsauth.utils import get_users_of_a_group
from sitesmanagement.utils import get_object_or_None, deprecated


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


class ServerType(models.Model):
    numcpu = models.IntegerField()
    sizeram = models.IntegerField()  # In GB
    sizedisk = models.IntegerField()  # In GB
    preallocated = models.IntegerField()  # Number of pre-allocated server of this type
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.CharField(max_length=100, blank=True, null=True)
    order = models.IntegerField()

    def __unicode__(self):
        return self.description or "%d CPU cores, %dGB of RAM, %dGB of SSD Disk, %s pounds per year" % \
                                   (self.numcpu, self.sizeram, self.sizedisk-5, self.price)


class Site(models.Model):
    """
    The site which is purchased by a user. It is the primary object which a
    user interacts with.

    :py:class:`.Site` object have the following fields:

    preallocated
        Is this a "preallocated" site as described in :any:`vmlifecycle`.
    name
        Human-friendly name of the site
    description
        Human-friendly description of the site
    institution_id
        The owning institution (retrieved using lookup)
    start_date
        Start date of the site
    end_date
        End date of the site (when the site will be cancelled, scheduled by the user or other reasons)
    deleted
        Is the site deleted?
    email
        Webmaster email
    subscription
        Indicates if the user wants to renew or their MWS3 subscription
    type
        Server type (amount of CPU, RAM, and disk)
    users
        Administrator users of a site
    ssh_users
        SSH only users of a site
    groups
        A set of :py:class:`.LookupGroup` instances representing the
        administrator groups of a site.
    ssh_groups
        SSH only groups
    supporters
        Supporters list (list of MWS support admins temporary added to the user list)
    disabled
        Indicates if the site is disabled by the user
    days_without_admin
        Number of days since the site lost its last admin
    exmws2
        Flag to mark Grandfathered MWS2 sites (Real date of start)
    migrated
        Whether site data has been copied over to Openstack

    """
    preallocated = models.BooleanField(default=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=250, blank=True)
    institution_id = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    email = models.EmailField(null=False, blank=False)
    subscription = models.BooleanField(default=True)

    type = models.ForeignKey(ServerType)

    users = models.ManyToManyField(User, related_name='sites')
    ssh_users = models.ManyToManyField(User, related_name='sites_auth_as_user', blank=True)
    groups = models.ManyToManyField(LookupGroup, related_name='sites', blank=True)
    ssh_groups = models.ManyToManyField(LookupGroup, related_name='sites_auth_as_user', blank=True)
    supporters = models.ManyToManyField(User, related_name='sites_auth_as_supporter', blank=True)

    disabled = models.BooleanField(default=False)

    days_without_admin = models.IntegerField(default=0)

    exmws2 = models.DateField(null=True, blank=True)

    migrated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]
    #
    # def clean(self):
    #     # Don't allow empty start_date for a non preallocated site (already on production)
    #     if not self.preallocated and self.start_date is None:
    #         raise ValidationError('start date cannot be null if the site is not a preallocated one')

    def get_absolute_url(self):
        """Return an absolute URL for this site's control panel."""
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

    def unsuspend(self):
        suspensions = Suspension.objects.filter(site=self)
        for susp in suspensions:
            if susp.active:
                susp.end_date = now()
                susp.save()
        return True

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
    def in_testing(self):
        return self.production_service.active and self.test_service.active

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
        if self.disabled:
            return False
        self.disabled = True
        self.save()
        if self.production_service:
            self.production_service.power_off()
        if self.test_service:
            self.test_service.power_off()
        return True

    def enable(self):
        if not self.disabled:
            return False
        self.disabled = False
        self.save()
        if self.production_service:
            self.production_service.power_on()
        if self.test_service:
            self.test_service.power_on()
        return True

    def switch_services(self):
        prod_service = self.production_service
        test_service = self.test_service
        netconf_prod = prod_service.network_configuration
        netconf_test = test_service.network_configuration
        vhost_prod = prod_service.vhosts.all()
        ug_prod = prod_service.unix_groups.all()

        with transaction.atomic():
            # Switch vhosts, test service has no vhosts
            for vhost in vhost_prod:
                vhost.service = test_service
                vhost.save()

            # Switch unix groups, test service has no UG
            for ug in ug_prod:
                ug.service = test_service
                ug.save()

            # Switch network configuration
            test_service.network_configuration = NetworkConfig.get_free_test_service_config()
            test_service.type = "production"
            test_service.site = None
            test_service.save()
            prod_service.network_configuration = netconf_test
            prod_service.type = "test"
            prod_service.save()
            test_service.site = self
            test_service.network_configuration = netconf_prod
            test_service.save()

            from apimws.models import AnsibleConfiguration
            AnsibleConfiguration.objects.update_or_create(service=test_service, key="backup_first_date",
                                                          defaults={'value': date.today().isoformat(), })

        from apimws.ansible import launch_ansible
        launch_ansible(prod_service)
        launch_ansible(test_service)
        return True

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
    # start date of the suspension
    start_date = models.DateTimeField(auto_now_add=True)
    # end date of the suspension
    end_date = models.DateTimeField(null=True, blank=True)
    site = models.ForeignKey(Site, related_name="suspensions")

    @property
    def active(self):
        now = timezone.now()
        if self.end_date:
            return self.start_date <= now and self.end_date > now
        else:
            return self.start_date <= now


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
    site = models.ForeignKey(Site, null=True, blank=True, related_name="services")
    type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    quarantined = models.BooleanField(default=False)

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
        self.status = 'ansible'
        self.save()
        from apimws.ansible import launch_ansible_async
        launch_ansible_async.apply_async(args=(self, ), countdown=120)

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
    numcpu = models.IntegerField()
    sizeram = models.IntegerField()  # In GB
    service = models.ForeignKey(Service, related_name='virtual_machines')

    from apimws.models import Cluster
    cluster = models.ForeignKey(Cluster, related_name='guests')

    def save(self, *args, **kwargs):
        # the primary VM may have had its parameters changed
        vm = self if self.service.primary else self.service.site.production_service.virtual_machines.first()
        self.numcpu = vm.numcpu if vm.numcpu is not None else self.service.site.type.numcpu
        self.sizeram = vm.sizeram if vm.sizeram is not None else self.service.site.type.sizeram
        super(VirtualMachine, self).save(*args, **kwargs)

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
        reset_vm.delay(self.id)
        return True

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


@receiver(pre_delete, sender=VirtualMachine)
def api_call_to_delete_vm(instance, **kwargs):
    if instance.name:
        from apimws.vm import destroy_vm
        destroy_vm(instance.id)


class Vhost(models.Model):
    WEBAPP_CHOICES = (
        ('wordpress', 'Wordpress'),
    )

    ALL_NAMES = ['denied', 'requested']
    GLOBAL_NAMES = ['global', 'external', 'special']
    PRIVATE_AND_GLOBAL_NAMES = GLOBAL_NAMES + ['accepted', 'private']

    name = models.CharField(max_length=60, validators=[validate_slug])
    # main domain name for this vhost
    main_domain = models.ForeignKey('DomainName', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    service = models.ForeignKey(Service, related_name='vhosts')
    csr = models.TextField(null=True, blank=True)
    certificate = models.TextField(null=True, blank=True)
    certificate_chain = models.TextField(null=True, blank=True)
    tls_key_hash = models.TextField(null=True, blank=True)
    tls_enabled = models.BooleanField(default=False)
    webapp = models.CharField(max_length=100, choices=WEBAPP_CHOICES, null=True, blank=True)
    apache_owned = models.BooleanField(default=False)

    def sorted_domain_names(self):
        return sorted(set(self.domain_names.all()))

    def get_url(self):
        if self.main_domain:
            if self.tls_enabled:
                return "https://%s" % self.main_domain.name
            else:
                return "http://%s" % self.main_domain.name
        else:
            return "#"

    class Meta:
        unique_together = ("name", "service")

    def __unicode__(self):
        if self.service and self.service.network_configuration:
            return self.name + ' - ' + self.service.network_configuration.name
        return self.name


    def domains(self, subset=ALL_NAMES):
        '''
        Return the list of hostnames for the vhost, optionally filtering it.
        '''
        if subset is self.ALL_NAMES:
            # all eligible names
            names = [dom.name for dom in self.domain_names.exclude(status__in=self.ALL_NAMES)]
        elif subset is self.GLOBAL_NAMES:
            # only names that are globally available, except the service hostname
            names = [dom.name for dom in self.domain_names.filter(status__in=self.GLOBAL_NAMES).exclude(
                     name=self.service.network_configuration.name)]
        elif subset is self.PRIVATE_AND_GLOBAL_NAMES:
            # both private and global names
            # TODO: remove service hostname from here as well
            names = [dom.name for dom in self.domain_names.filter(status__in=self.PRIVATE_AND_GLOBAL_NAMES)]
        else:
            raise ValueError('Unknown subset type: %r' % (subset,))
        return names


class DomainName(models.Model):
    STATUS_CHOICES = (              # The hostname:
        ('requested', 'Requested'), #   has been requested through the panel
        ('accepted', 'Accepted'),   #   has been accepted by the domain owner
        ('private', 'Private'),     #   has validated as visible within the CUDN
        ('global', 'Global'),       #   has validated as world-visible
        ('external', 'External'),   #   is in a zone we don't control
        ('special', 'Special'),     #   is under cam.ac.uk, but the MWS can't add/rescind it
        ('denied', 'Denied'),       #   has not been accepted by the domain owner
        ('deleted', 'Deleted'),     #   has failed validation and is scheduled to be deleted
    )

    name = models.CharField(max_length=250, unique=True, validators=[full_domain_validator])
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='requested')
    vhost = models.ForeignKey(Vhost, related_name='domain_names')
    requested_by = models.ForeignKey(User, related_name='domain_names_requested', blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reject_reason = models.CharField(max_length=250, blank=True, null=True)
    token = models.CharField(max_length=50, default=uuid.uuid4)
    authorised_by = models.ForeignKey(User, related_name='domain_names_authorised', blank=True, null=True)

    def accept_it(self):
        self.status = 'accepted'
        self.save()
        if self.vhost.main_domain is None or \
                        self.vhost.main_domain.name == self.vhost.service.network_configuration.name:
            self.vhost.main_domain = self
            self.vhost.save()
        from apimws.ipreg import set_cname
        try:
            set_cname(self.name, self.vhost.service.network_configuration.name)
        except DomainNameDelegatedException:
            return self.reject_it("Domain delegated")
        from apimws.ansible import launch_ansible
        launch_ansible(self.vhost.service)
        now = datetime.now()
        # Check if the set_cname was executed before the DNS refresh of the current hour.
        # DNS refreshes happen at 53 minutes of each hour
        if now.minute > 55:
            # If it was executed after the DNS refresh of the current hour, send the email to the user when
            # the next refresh happens
            eta = now.replace(minute=54) + timedelta(hours=1)
        else:
            # If it was executed before the DNS refresh of the current hour, send the email to the user when
            # the refresh happens
            eta = now.replace(minute=54)
        from apimws.utils import domain_confirmation_user
        domain_confirmation_user.apply_async(args=(self, ), eta=eta)

    def reject_it(self, reason=""):
        self.status = 'denied'
        self.reject_reason = reason
        self.save()
        from apimws.utils import domain_confirmation_user
        domain_confirmation_user.delay(self)

    def special_it(self, reason=""):
        self.status = 'special'
        self.reject_reason = reason
        self.save()
        # TODO send email as special

    def _resolve(self, resolver=None, nameservers=None):
        '''
        Attempt to resolve DomainName, using either specified or default nameservers
        or a custom resolver callable.
        Return True if there are any A or AAAA records that match IPv4/6 addresses
        configured on the DomainName's Vhost's Service.
        '''
        import dns.resolver
        import dns.name
        import dns.rdatatype

        if resolver and nameservers:
            raise ValueError('resolver and nameservers are mutually exclusive')

        r = resolver if resolver else dns.resolver.Resolver()
        r.nameservers = nameservers if nameservers else r.nameservers
        proxies = getattr(settings, 'MWS_ALLOWED_PROXIES', [])
        dnsname = dns.name.from_text(self.name)
        ip4 = self.vhost.service.network_configuration.IPv4
        ip6 = self.vhost.service.network_configuration.IPv6

        try:
            answer = r.query(dnsname, 'AAAA')
            return ip6 in [AAAA.to_text() for AAAA in answer.rrset.items if AAAA.rdtype == dns.rdatatype.AAAA] or \
                   any([AAAA.to_text() in proxies for AAAA in answer.rrset.items if AAAA.rdtype == dns.rdatatype.AAAA])
        except:
            try:
                answer = r.query(dnsname, 'A')
                return ip4 in [A.to_text() for A in answer.rrset.items if A.rdtype == dns.rdatatype.A] or \
                       any([A.to_text() in proxies for A in answer.rrset.items if A.rdtype == dns.rdatatype.A])
            except:
                return False

    def validate(self, update=False):
        '''
        Validate DomainName using a set of resolvers.
        '''
        status = self.status
        results = []
        if status not in ['requested', 'denied']:
            for resolver in settings.MWS_RESOLVERS:
                if self._resolve(resolver=resolver['RESOLVER']):
                    results.append(resolver['SCOPE'])
            if results:
                status = results[0] if status not in ['external', 'special'] else status
            else:
                status = 'deleted'
            if update and self.status != status:
                self.status = status
                self.save()
        return status

    def __unicode__(self):
        return self.name


def unix_group_name_validator(group_name):
    GROUP_NAME_PATTERN = re.compile(r'^[A-Z]+$')
    if len(group_name) < 3:
        raise ValidationError("Unix Group names need to be between 3 and 16 characters")
    if not GROUP_NAME_PATTERN.match(group_name):
        raise ValidationError("Unix Group names can only contain letters written in capital letters")


class UnixGroup(models.Model):
    name = models.CharField(max_length=16, validators=[unix_group_name_validator])
    service = models.ForeignKey(Service, related_name='unix_groups')
    to_be_deleted = models.BooleanField(default=False)
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = (("name", "service"), )


class SiteKey(models.Model):
    ALGORITHMS = {
        'RSA': 1,
        'DSA': 2,
        'ECDSA': 3,
        'ED25519': 4
    }
    FP_TYPES = {
        'SHA1': 1,
        'SHA256': 2
    }
    type = models.CharField(max_length=100)
    public_key = models.TextField()
    fingerprint = models.CharField(max_length=250, null=True)
    fingerprint2 = models.CharField(max_length=250, null=True)
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
