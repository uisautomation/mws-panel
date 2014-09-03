from datetime import datetime
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django import forms
import re
from ucamlookup import get_institutions
from ucamlookup.models import LookupGroup


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

    # Authorised users per site
    users = models.ManyToManyField(User, related_name='sites')
    # Authorised user groups per site
    groups = models.ManyToManyField(LookupGroup, related_name='sites', null=True, blank=True)

    def __str__(self):
        return self.name

    def is_admin_suspended(self):
        for susp in self.suspensions.all():
            if susp.active:
                return True
        return False

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


class Vhost(models.Model):
    name = models.CharField(max_length=250)
    # main domain name for this vhost
    main_domain = models.ForeignKey('DomainName', related_name='+', null=True, blank=True)
    site = models.ForeignKey(Site, related_name='vhosts')

    def __unicode__(self):
        return self.name


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
            raise ValidationError("Unallowed characters in label '%(label)s'." % {'label': label})


class DomainName(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied'),
    )

    name = models.CharField(max_length=250, unique=True, validators=[full_domain_validator])
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='requested')
    vhost = models.ForeignKey(Vhost, related_name='domain_names')

    def __unicode__(self):
        return self.name


class NetworkConfig(models.Model):
    """ The network configuration for a VM (IPv4, IPv6, and domain name associated
    """
    IPv4 = models.GenericIPAddressField(protocol='IPv4')
    IPv6 = models.GenericIPAddressField(protocol='IPv6')
    SSHFP = models.CharField(max_length=250, null=True, blank=True)
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
        ('ansible', 'Running Ansible'),
        ('ready', 'Ready'),
    )

    name = models.CharField(max_length=250, blank=True, null=True)
    primary = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    network_configuration = models.OneToOneField(NetworkConfig, related_name='virtual_machine')
    site = models.ForeignKey(Site, related_name='virtual_machines')

    def is_on(self):
        from apimws.platforms import get_vm_power_state
        if get_vm_power_state(self) == "On":
            return True
        else:
            return False

    def power_on(self):
        from apimws.platforms import change_vm_power_state
        return change_vm_power_state(self, 'on')

    def power_off(self):
        from apimws.platforms import change_vm_power_state
        return change_vm_power_state(self, 'off')

    def do_reset(self):
        from apimws.platforms import reset_vm
        return reset_vm(self)

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


class VhostForm(forms.ModelForm):
    class Meta:
        model = Vhost
        fields = ('name', )
        labels = {
            'name': 'Vhost name',
        }


class DomainNameFormNew(forms.ModelForm):
    #name = forms.CharField(max_length=250, required=True, label="Domain name",
    #                       validators=[DomainName.full_domain_validator])

    class Meta:
        model = DomainName
        fields = ('name', )
        labels = {
            'name': 'DomainName',
        }


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ('purchase_order_number', 'group', 'purchase_order')


class SystemPackagesForm(forms.Form):
        OPTIONS = (
            ("1", "dwoo - PHP5 template engine"),
            ("2", "php5-exactimage - fast image manipulation library (PHP bindings)"),
            ("3", "php5-ffmpeg - audio and video support via ffmpeg for php5"),
            ("4", "php5-gdcm - Grassroots DICOM PHP5 bindings"),
            ("5", "php5-vtkgdcm - Grassroots DICOM VTK PHP bindings"),
            ("6", "php-geshi - Generic Syntax Highlighter"),
            ("7", "gosa-plugin-phpgw - phpgw plugin for GOsa"),
            ("8", "gosa-plugin-phpscheduleit - phpscheduleit plugin for GOsa"),
            ("9", "libgv-php5 - PHP5 bindings for graphviz"),
            ("10", "jffnms - PHP Network Management System"),
            ("11", "kdevelop-php - PHP plugin for KDevelop"),
            ("12", "kdevelop-php-docs - PHP documentation plugin for KDevelop"),
            ("13", "php5-lasso - Library for Liberty Alliance and SAML protocols - PHP 5 bindings"),
            ("14", "libfpdf-tpl-php - PHP library to use PDF templates with FPDF"),
            ("15", "libfpdi-php - PHP library for importing existing PDF documents into FPDF"),
            ("16", "libkohana3.1-core-php - PHP5 framework core classes"),
            ("17", "libkohana3.1-php - PHP5 framework metapackage"),
            ("18", "libkohana3.2-core-php - PHP5 framework core classes"),
            ("19", "libkohana3.2-php - PHP5 framework metapackage"),
            ("20", "libmarkdown-php - PHP library for rendering Markdown data"),
            ("21", "liboauth-php - PHP library implementing the OAuth secure authentication protocol"),
            ("22", "php5-mapscript - php5-cgi module for MapServer"),
            ("23", "php5-ming - Ming module for php5"),
            ("24", "phamm - PHP front-end to manage virtual services on LDAP - main package"),
            ("25", "phamm-ldap - PHP front-end to manage virtual services on LDAP - back-end files"),
            ("26", "phamm-ldap-amavis - PHP front-end to manage virtual services on LDAP - back-end files"),
            ("27", "phamm-ldap-vacation - PHP front-end to manage virtual services on LDAP - back-end files"),
            ("28", "php5-adodb - Extension optimising the ADOdb database abstraction library"),
            ("29", "php-apc - APC (Alternative PHP Cache) module for PHP 5"),
            ("30", "php-auth - PHP PEAR modules for creating an authentication system"),
            ("31", "php-auth-http - HTTP authentication"),
            ("32", "php-auth-sasl - Abstraction of various SASL mechanism responses"),
            ("33", "php-cache - framework for caching of arbitrary data"),
            ("34", "php-cache-lite - Fast and lite data cache system"),
            ("35", "php-cas - Central Authentication Service client library in php"),
            ("36", "php-codecoverage - provides collection, processing and rendering for PHP code coverage "
                   "information"),
            ("37", "php-codesniffer - PHP, CSS and JavaScript coding standard analyzer and checker"),
            ("38", "php-compat - Provides components to achieve PHP version independence"),
            ("39", "php-config - Your configuration's swiss-army knife"),
            ("40", "php-console-table - PHP PEAR module to make it easy to build console style tables"),
            ("41", "php-crypt-blowfish - Allows for quick two-way blowfish encryption without requiring the MCrypt PHP "
                   "extension"),
            ("42", "php-crypt-cbc - PEAR class to emulate Perl's Crypt::CBC module"),
            ("43", "php-date - PHP PEAR module for date and time manipulation"),
            ("44", "php-db - PHP PEAR Database Abstraction Layer"),
            ("45", "php-doc - Documentation for PHP5"),
            ("46", "php-elisp - Emacs support for php files"),
            ("47", "php-event-dispatcher - Dispatch notifications using PHP callbacks"),
            ("48", "php-file - PHP Pear modules for common file and directory routines"),
            ("49", "php-file-iterator - FilterIterator implementation for PHP"),
            ("50", "php-fpdf - PHP class to generate PDF files"),
            ("51", "php5-geoip - GeoIP module for php5"),
            ("52", "php-getid3 - PHP script to extract informations from multimedia files"),
            ("53", "php-gettext - read gettext MO files directly, without requiring anything other than PHP"),
            ("54", "php-html-common - base class for other HTML classes"),
            ("55", "php-html-safe - strip down all potentially dangerous content within HTML"),
            ("56", "php-html-template-it - PEAR HTML Isotemplate API"),
            ("57", "php-htmlpurifier - Standards-compliant HTML filter"),
            ("58", "php-http - PHP PEAR module for HTTP related stuff"),
            ("59", "php-http-request - PEAR class to provide an easy way to perform HTTP requests"),
            ("60", "php-http-upload - Easy and secure management of files submitted via HTML Forms"),
            ("61", "php-http-webdav-server - WebDAV server base class"),
            ("62", "php-image-text - PEAR module to do advanced text manipulations in images"),
            ("63", "php5-imagick - ImageMagick module for php5"),
            ("64", "php-imlib - PHP Imlib2 Extension"),
            ("65", "php-invoker - utility class for invoking callables with a timeout"),
            ("66", "php-letodms-core - Document management system - Core files"),
            ("67", "php-letodms-lucene - Document management system - Fulltext search"),
            ("68", "php-log - log module for PEAR"),
            ("69", "php-mail - PHP PEAR module for sending email"),
            ("70", "php-mail-mime - PHP PEAR module for creating MIME messages"),
            ("71", "php-mail-mimedecode - PHP PEAR module to decode MIME messages"),
            ("72", "php-mdb2 - merge of the PEAR DB and Metabase php database abstraction layers"),
            ("73", "php-mdb2-driver-mysql - PHP PEAR module to provide a MySQL driver for MDB2"),
            ("74", "php-mdb2-driver-pgsql - PHP PEAR module to provide a PostgreSQL driver for MDB2"),
            ("75", "php-mdb2-schema - XML based database schema manager"),
            ("76", "php5-memcache - memcache extension module for PHP5"),
            ("77", "php5-memcached - memcached extension module for PHP5, uses libmemcached"),
            ("78", "php-mime-type - Utility class for dealing with MIME types"),
            ("79", "php-net-checkip - check the syntax of IPv4 addresses"),
            ("80", "php-net-dime - class that implements DIME encoding"),
            ("81", "php-net-dnsbl - Checks if a given host or URL is listed on a DNSBL or SURBL"),
            ("82", "php-net-ftp - provides an OO interface to the PHP FTP functions"),
            ("83", "php-net-imap - Provides an implementation of the IMAP protocol"),
            ("84", "php-net-ipv4 - IPv4 network calculations and validation"),
            ("85", "php-net-ipv6 - Check and validate IPv6 addresses"),
            ("86", "php-net-ldap - a OO interface for searching and manipulating LDAP-entries"),
            ("87", "php-net-ldap2 - PHP PEAR module for searching and manipulating LDAP-entries"),
            ("88", "php-net-lmtp - PHP PEAR module implementing LMTP protocol"),
            ("89", "php-net-nntp - PHP Pear module for NNTP"),
            ("90", "php-net-portscan - Portscanner utilities"),
            ("91", "php-net-sieve - net_sieve module for PEAR"),
            ("92", "php-net-smartirc - provides an OO interface to the PHP IRC functions"),
            ("93", "php-net-smtp - PHP PEAR module implementing SMTP protocol"),
            ("94", "php-net-socket - PHP PEAR Network Socket Interface module"),
            ("95", "php-net-url - easy parsing of Urls"),
            ("96", "php-net-url2 - Class for parsing and handling URL"),
            ("97", "php-net-whois - PHP PEAR module for querying whois services"),
            ("98", "php-numbers-words - PEAR module providing methods for spelling numerals in words"),
            ("99", "php-openid - PHP OpenID library"),
        )
        system_packages = forms.MultipleChoiceField(widget=forms.SelectMultiple, choices=OPTIONS, label="")