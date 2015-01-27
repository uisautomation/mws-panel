from datetime import datetime
from itertools import chain
import json
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django import forms
import re
import reversion
from ucamlookup import get_institutions
from ucamlookup.models import LookupGroup
from mwsauth.utils import get_users_of_a_group
from sitesmanagement.utils import is_camacuk, get_object_or_None


class ServiceNetworkConfig(models.Model):
    """ The network configuration for the VMs of a site:
     Primary VM: IPv4, IPv6, and domain name
     Secondary VM: Private IPv4 and private domain name
    """

    IPv4 = models.GenericIPAddressField(protocol='IPv4', unique=True)
    IPv6 = models.GenericIPAddressField(protocol='IPv6', unique=True)
    SSHFP = models.CharField(max_length=250, null=True, blank=True)
    mws_domain = models.CharField(max_length=250, unique=True)

    IPv4private = models.GenericIPAddressField(protocol='IPv4', unique=True)
    mws_private_domain = models.CharField(max_length=250, unique=True)

    @classmethod
    def num_pre_allocated(cls):
        return cls.objects.filter(site=None).count()

    @classmethod
    def get_free_config(cls):
        return cls.objects.filter(site=None).first()

    def __str__(self):
        return self.IPv4 + " - " + self.mws_domain


class HostNetworkConfig(models.Model):
    IPv6 = models.GenericIPAddressField(protocol='IPv6', unique=True)
    hostname = models.CharField(max_length=250, unique=True)


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

    # Administrator users of a site
    users = models.ManyToManyField(User, related_name='sites')
    # SSH only users of a site
    ssh_users = models.ManyToManyField(User, related_name='sites_auth_as_user')
    # Administrator groups of a site
    groups = models.ManyToManyField(LookupGroup, related_name='sites', null=True, blank=True)
    # SSH only groups
    ssh_groups = models.ManyToManyField(LookupGroup, related_name='sites_auth_as_user', null=True, blank=True)

    # Indicates if the site is disabled by the user
    disabled = models.BooleanField(default=False)

    # The network configuration for the service
    service_network_configuration = models.OneToOneField(ServiceNetworkConfig, related_name='site')

    def __str__(self):
        return self.name

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

    def vm(self, primary):
        if self.virtual_machines.filter(primary=primary).count() is 0:
            return None
        else:
            return self.virtual_machines.get(primary=primary)

    @property
    def primary_vm(self):
        return self.vm(primary=True)

    @property
    def secondary_vm(self):
        return self.vm(primary=False)

    @property
    def domain_names(self):
        domains = []
        for vhost in self.primary_vm.vhosts.all():
            domains += vhost.domain_names.all()
        return sorted(set(domains))

    def calculate_billing(self, financial_year_start, financial_year_end):
        start_date = end_date = None
        if self.end_date is None:
            end_date = financial_year_end  # The site has not yet been deactivated
        elif financial_year_start <= self.end_date <= financial_year_end:
            end_date = self.end_date  # The site was deactivated this financial year

        if financial_year_start <= self.start_date <= financial_year_end:
            start_date = self.start_date  # The site started this financial year
        if self.start_date < financial_year_start:
            start_date = financial_year_start  # The site started before this financial year

        if start_date is None or end_date is None:
            return None  # The site was deactivated before this financial year or started after this financial year
        else:
            if hasattr(self, 'billing'):
                return [self.billing.group, self.billing.purchase_order_number, start_date, end_date]
            else:
                return ['Site ID: %d' % self.id, 'Pending', start_date, end_date]

    def cancel(self):
        self.end_date = datetime.today()
        self.save()
        if self.primary_vm:
            self.primary_vm.power_off()
        if self.secondary_vm:
            self.secondary_vm.power_off()

    def delete_vms(self):
        if self.primary_vm:
            self.primary_vm.delete()
        if self.secondary_vm:
            self.secondary_vm.delete()

    def disable(self):
        self.disabled = True
        self.save()
        if self.primary_vm:
            self.primary_vm.power_off()
        if self.secondary_vm:
            self.secondary_vm.power_off()
        return True

    def enable(self):
        self.disabled = False
        self.save()
        if self.primary_vm:
            self.primary_vm.power_on()
        if self.secondary_vm:
            self.secondary_vm.power_on()
        return True

    @property
    def is_busy(self):
        if self.primary_vm:
            if self.primary_vm.is_busy:
                return True
        if self.secondary_vm:
            if self.secondary_vm.is_busy:
                return True
        if not self.primary_vm and not self.secondary_vm:
            return True
        return False

    @property
    def is_ready(self):
        if self.primary_vm:
            if self.primary_vm.status != 'ready':
                return False
        if self.secondary_vm:
            if self.secondary_vm.status != 'ready':
                return False
        if not self.primary_vm and not self.secondary_vm:
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
    site = models.ForeignKey(Site, related_name='+', unique=True)  # do not to create a backwards relation


class Suspension(models.Model):
    reason = models.CharField(max_length=250)
    # is the suspension active?
    active = models.BooleanField(default=True)
    # start date of the suspension
    start_date = models.DateField()
    # end date of the suspension
    end_date = models.DateField(null=True, blank=True)

    site = models.ForeignKey(Site, related_name="suspensions")


class Billing(models.Model):
    purchase_order_number = models.CharField(max_length=100)
    purchase_order = models.FileField(upload_to='billing')
    group = models.CharField(max_length=250)
    site = models.OneToOneField(Site, related_name='billing')


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


class VirtualMachine(models.Model):
    """ A virtual machine is associated to a site and has a network configuration. Its attributes include
        a name and a boolean to indicate if it's the primary or secondary VM of a Site.
    """
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
        ('installing', 'Installing OS'),
        ('ansible', 'Running Ansible'),
        ('ansible_queued', 'Ansible queued'),
        ('ready', 'Ready'),
    )

    name = models.CharField(max_length=250, blank=True, null=True)
    primary = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    token = models.CharField(max_length=50)

    site = models.ForeignKey(Site, related_name='virtual_machines', null=True)
    host_network_configuration = models.OneToOneField(HostNetworkConfig, related_name="vm")

    def is_on(self):
        from apimws.platforms import get_vm_power_state
        if get_vm_power_state(self) == "On":
            return True
        else:
            return False

    @property
    def is_busy(self):
        if self.status != 'ready' and self.status != 'ansible' and self.status != 'ansible_queued':
            return True
        else:
            return False

    @property
    def is_ready(self):
        if self.status == 'ready':
            return True
        else:
            return False

    def power_on(self):
        from apimws.platforms import change_vm_power_state
        change_vm_power_state(self, 'on')

    def power_off(self):
        from apimws.platforms import change_vm_power_state
        change_vm_power_state(self, 'off')

    def do_reset(self):
        from apimws.platforms import reset_vm
        return reset_vm.delay(self)

    @property
    def ipv4(self):
        if self.primary:
            return self.site.service_network_configuration.IPv4
        else:
            return self.site.service_network_configuration.IPv4private

    @property
    def sshfp(self):
        return self.site.service_network_configuration.SSHFP

    @property
    def ipv6(self):
        if self.primary:
            return self.site.service_network_configuration.IPv6
        else:
            return None

    @property
    def hostname(self):
        if self.primary:
            return self.site.service_network_configuration.mws_domain
        else:
            return self.site.service_network_configuration.mws_private_domain

    @property
    def ip_register_domains(self):
        domains = []
        for vhost in self.vhosts.all():
            for domain in vhost.domain_names.all():
                if is_camacuk(domain.name) and domain.status == 'accepted':
                    domains.append(domain)
        return sorted(set(domains))

    @property
    def all_domain_names(self):
        domains = []
        for vhost in self.vhosts.all():
            for domain in vhost.domain_names.all():
                domains.append(domain)
        return domains

    @property
    def operating_system(self):
        from apimws.models import AnsibleConfiguration
        ansible_configuraton = get_object_or_None(AnsibleConfiguration, vm=self, key="os")
        if ansible_configuraton:
            return json.loads(ansible_configuraton.value)
        else:
            return None

    def due_update(self):
        operating_system_dict = self.operating_system
        if operating_system_dict:
            if settings.OS_VERSION[operating_system_dict.keys()[0]] > operating_system_dict.values()[0]:
                return True
            else:
                return False
        else:
            return False # TODO also raise an exception?

    @property
    def os_type(self):
        operating_system_dict = self.operating_system
        if operating_system_dict:
            return operating_system_dict.keys()[0]
        else:
            return ""

    @property
    def os_version(self):
        operating_system_dict = self.operating_system
        if operating_system_dict:
            return operating_system_dict.values()[0]
        else:
            return ""

    def __str__(self):
        if self.name is None:
            return "<Under request>"
        else:
            return self.name


class Vhost(models.Model):
    name = models.CharField(max_length=250)
    # main domain name for this vhost
    main_domain = models.ForeignKey('DomainName', related_name='+', null=True, blank=True, on_delete=models.SET_NULL)
    vm = models.ForeignKey(VirtualMachine, related_name='vhosts')
    csr = models.TextField(null=True)
    certificate = models.TextField(null=True)

    def sorted_domain_names(self):
        return sorted(set(self.domain_names.all()))

    def __str__(self):
        return self.name


class DomainName(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
        ('to_be_deleted', 'Removing...'),
    )

    name = models.CharField(max_length=250, unique=True, validators=[full_domain_validator])
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='requested')
    vhost = models.ForeignKey(Vhost, related_name='domain_names')

    @property
    def is_external(self):
        return not is_camacuk(self.name)

    def __str__(self):
        return self.name


class UnixGroup(models.Model):
    name = models.CharField(max_length=16)  # TODO add validator to comply with Ubuntu guidelines of Unix group names
    vm = models.ForeignKey(VirtualMachine, related_name='unix_groups')
    users = models.ManyToManyField(User)

    def __str__(self):
        return self.name


class SiteKeys(models.Model):
    type = models.CharField(max_length=100)
    public_key = models.TextField()
    fingerprint = models.CharField(max_length=250, null=True)
    site = models.ForeignKey(Site, related_name="keys")


# FORMS

class SiteForm(forms.ModelForm):
    institution_id = forms.ChoiceField(label='The University institution responsible for this site')
    description = forms.CharField(label='Description for the MWS (e.g. Web server for St Botolph\'s '
                                        'College main website)',
                                  widget=forms.Textarea(attrs={'maxlength': 250}),
                                  max_length=250,
                                  required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(SiteForm, self).__init__(*args, **kwargs)
        self.fields['institution_id'].choices = get_institutions(user)

    class Meta:
        model = Site
        fields = ('name', 'description', 'institution_id', 'email')
        labels = {
            'name': 'A short name for this Managed Web Service account (e.g. St Botolph\'s main site)',
            'email': 'The webmaster email (please use a role email when possible)'
        }


class VhostForm(forms.ModelForm):
    class Meta:
        model = Vhost
        fields = ('name', )
        labels = {
            'name': 'Web site name',
        }


class DomainNameFormNew(forms.ModelForm):
    #name = forms.CharField(max_length=250, required=True, label="Domain name",
    #                       validators=[DomainName.full_domain_validator])

    class Meta:
        model = DomainName
        fields = ('name', )
        labels = {
            'name': 'Domain Name',
        }


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ('purchase_order_number', 'group', 'purchase_order')
        labels = {
            'purchase_order_number': 'Purchase order number (PO)',
            'group': 'Name or Reference of the group that raised the purchase order',
            'purchase_order': 'A PDF file with the purchase order'
        }


class UnixGroupForm(forms.ModelForm):
    class Meta:
        model = UnixGroup
        fields = ('name', )


reversion.register(VirtualMachine, follow=["unix_groups", "ansible_configuration", "vhosts"])
reversion.register(Vhost, follow=["domain_names", "vm"])
reversion.register(DomainName, follow=["vhost"])
reversion.register(UnixGroup, follow=["vm"])
