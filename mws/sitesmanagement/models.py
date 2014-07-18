from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.db import models
from django import forms
from django.db.models.signals import post_save
from django.dispatch import receiver
from .utils import get_institutions


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
    email = models.EmailField(null=True, blank=True)
    # main domain name for this mws site
    main_domain = models.ForeignKey('DomainName', related_name='+', null=True, blank=True)

    # Authorised users per site
    users = models.ManyToManyField(User, related_name='sites')
    # Authorised user groups per site
    groups = models.ManyToManyField(Group, related_name='sites', null=True, blank=True)

    def __str__(self):
        return self.name

    def is_admin_suspended(self):
        for susp in self.suspensions.all():
            if susp.active:
                return True
        return False

    def vm(self, primary):
        if self.virtual_machines.filter(primary=primary).count() is 0:
            return None
        else:
            return self.virtual_machines.get(primary=primary)

    def primary_vm(self):
        return self.vm(primary=True)

    def secondary_vm(self):
        return self.vm(primary=False)

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
                return [self.billing.group, self.billing.purchase_order, start_date, end_date]
            else:
                return ['Site ID: %d' % self.id, 'Pending', start_date, end_date]


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
    purchase_order = models.FileField(upload_to=settings.MEDIA_ROOT)
    group = models.CharField(max_length=250)
    site = models.OneToOneField(Site, related_name='billing')


class DomainName(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
    )

    name = models.CharField(max_length=250, unique=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    site = models.ForeignKey(Site, related_name='domain_names')

    def __unicode__(self):
        return self.name


class NetworkConfig(models.Model):
    """ The network configuration for a VM (IPv4, IPv6, and domain name associated
    """
    IPv4 = models.GenericIPAddressField(protocol='IPv4')
    IPv6 = models.GenericIPAddressField(protocol='IPv6')
    mws_domain = models.CharField(max_length=250, unique=True)

    @classmethod
    def num_pre_allocated(cls):
        return cls.objects.filter(virtual_machine=None).count()

    def __unicode__(self):
        return self.IPv4 + " - " + self.mws_domain


class VirtualMachine(models.Model):
    """ A virtual machine is associated to a site and has a network configuration. Its attributes include
        a name and a boolean to indicate if it's the primary or secondary VM of a Site.
    """
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
        ('ready', 'Ready'),
    )

    name = models.CharField(max_length=250, blank=True, null=True)
    primary = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    network_configuration = models.OneToOneField(NetworkConfig, related_name='virtual_machine')
    site = models.ForeignKey(Site, related_name='virtual_machines')

    def __unicode__(self):
        if self.name is None:
            return "<Under request>"
        else:
            return self.name


# FORMS

class SiteForm(forms.ModelForm):
    institution_id = forms.ChoiceField(label='The University institution responsible for this site')
    description = forms.CharField(label='Description for the web server (e.g. Web server for St Botolph\'s College '
                                        'main website)',
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
            'name': 'A short name for this web server (e.g. St Botolph\'s main site)',
            'email': 'The webmaster email (please use a role email when possible)'
        }


class DomainNameFormNewSite(forms.ModelForm):
    name = forms.CharField(max_length=250, required=False, label="Main domain name")

    class Meta:
        model = DomainName
        fields = ('name', )


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ('group', 'purchase_order')


#@receiver(post_save, sender=Site)
#def platforms_api_request(instance, created, update_fields, **kwargs):
def platforms_api_request(site, primary):
    network_configuration = NetworkConfig.objects.filter(virtual_machine=None).first()
    vm = VirtualMachine(primary=primary, status='requested', network_configuration=network_configuration, site=site)
    vm.save()

    subject = "New request of a VM for the MWS"
    message = "IPv4: " + network_configuration.IPv4 + "\n" \
              "IPv6: " + network_configuration.IPv6 + "\n" \
              "Domain Name: " + network_configuration.mws_domain + "\n" \
              "Attached: autoyast.xml (with IPs, keys)\n" \
              "Please, when ready click here: http://localhost:8000/api/confirm_vm/"+str(vm.id)
    from_email = "mws-admin@cam.ac.uk"
    recipient_list = ('amc203@cam.ac.uk', )
    send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None,
              connection=None, html_message=None)


def ip_register_api_request(site, domain_name):
    domain_requested = DomainName(name=domain_name, status='requested', site=site)
    domain_requested.save()

    subject = "New request of a Domain Name for the MWS"
    message = "Domain Name requested: " + domain_name + "\n" \
              "IPv4: " + site.primary_vm().network_configuration.IPv4 + "\n" \
              "IPv6: " + site.primary_vm().network_configuration.IPv6 + "\n" \
              "Please, when ready click here: http://localhost:8000/api/confirm_dns/"+str(domain_requested.id)
    from_email = "mws-admin@cam.ac.uk"
    recipient_list = ('amc203@cam.ac.uk', )
    send_mail(subject, message, from_email, recipient_list, fail_silently=False, auth_user=None, auth_password=None,
              connection=None, html_message=None)