import sys
import json
from django.core.management.base import NoArgsCommand, CommandError
from optparse import make_option
from django.db.models import Q
from apimws.models import ApacheModule, PHPLib
from sitesmanagement.models import VirtualMachine, Site, UnixGroup


group = "mwsclients"
# We start Unix Group IDs by the 2^16-2 which is the last one free in Debian
# and assign them to groups in decrease order
INITIAL_GID = 4294967293


# At this moment we only support OV Quovadis
CERT_CHAIN = '''-----BEGIN CERTIFICATE-----
MIIFTDCCAzSgAwIBAgIUSJgt4qkssznhyPkzNYJ10+T4glUwDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQk0xGTAXBgNVBAoTEFF1b1ZhZGlzIExpbWl0ZWQxGzAZ
BgNVBAMTElF1b1ZhZGlzIFJvb3QgQ0EgMjAeFw0xMzA2MDExMzM1MDVaFw0yMzA2
MDExMzM1MDVaME0xCzAJBgNVBAYTAkJNMRkwFwYDVQQKExBRdW9WYWRpcyBMaW1p
dGVkMSMwIQYDVQQDExpRdW9WYWRpcyBHbG9iYWwgU1NMIElDQSBHMjCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAOHhhWmUwI9X+jT+wbho5JmQqYh6zle3
0OS1VMIYfdDDGeipY4D3t9zSGaNasGDZdrQdMlY18WyjnEKhi4ojNZdBewVphCiO
zh5Ni2Ak8bSI/sBQ9sKPrpd0+UCqbvaGs6Tpx190ZRT0Pdy+TqOYZF/jBmzBj7Yf
XJmWxlfCy62UiQ6tvv+4C6W2OPu1R4HUD8oJ8Qo7Eg0cD+GFsBM2w8soffyl+Dc6
pKtARmOClUC7EqyWP0V9953lA34kuJZlYxxdgghBTn9rWoaQw/Lr5Fn0Xgd7fYS3
/zGhmXYvVsuAxIn8Gk+YaeoLZ8H9tUvnDD3lEHzvIsMPxqtd7IgcVaMCAwEAAaOC
ASowggEmMBIGA1UdEwEB/wQIMAYBAf8CAQAwEQYDVR0gBAowCDAGBgRVHSAAMHIG
CCsGAQUFBwEBBGYwZDAqBggrBgEFBQcwAYYeaHR0cDovL29jc3AucXVvdmFkaXNn
bG9iYWwuY29tMDYGCCsGAQUFBzAChipodHRwOi8vdHJ1c3QucXVvdmFkaXNnbG9i
YWwuY29tL3F2cmNhMi5jcnQwDgYDVR0PAQH/BAQDAgEGMB8GA1UdIwQYMBaAFBqE
YrxITDMlBNTu0PYDxBlG0ZRrMDkGA1UdHwQyMDAwLqAsoCqGKGh0dHA6Ly9jcmwu
cXVvdmFkaXNnbG9iYWwuY29tL3F2cmNhMi5jcmwwHQYDVR0OBBYEFJEZYq1bF6cw
+/DeOSWxvYy5uFEnMA0GCSqGSIb3DQEBCwUAA4ICAQB8CmCCAEG1Lcw55fTba84A
ipwMieZydFO5bcIh5UyXWgWZ6OP4jb/6LaifEMLjRCC0mU14G6PrPU+iZQiIae7X
5EavhmETEA8JbLICjiD4c9Y6+bgMt4szEPiZ2SALOQj10Br4HKQfy/OvbedRbLax
p9qlDG4qJgSt3uikDIJSarx6mpgEQXu00UZNkiEYUfeO8hXGXrZbtDnkuaiVDtM6
s9yYpcoyFxFOrORrEgViaI7P3EJaDYmI6IDUIPaSBM6GrVMiaINYEMBL1v2jZi8r
XDY0yVsZ/0DAIQiCBNNvT1NjQ5Sn1E+O+ZBiqDD+rBvBoPsI6ydfdKtJur5YL+Oo
kJK2eLrce8287awIcd8FMRDcZw/NX1bc8uKye5OCtwpQ0d4jL4emuXwFv8TqUbZh
2xJShyy57cqw3qWoBOs/WWza29/Hun8PXkQoZepwY/xc+9nI1NaKM8NqhSqJNTJl
vXj7zb3mdpbe3YR9BkSXProlN7l5KOx54gJ7kJ7r6qJYJux03HyPM11Kp4wfdn1R
sC2UQ5awC6fg/3XE2HZVkyqJjKwqh4nFaiK5EMV7DHQ4oJx9ckmDw6pBvDaoPokX
yzdfJ72n+1JfHGP+workciKNldgqYX6J4jPrCIEIBrtDta4QxP10Tyd9RFu13XmE
8SYi/VXvrf3nriQfAZ/nSA==
-----END CERTIFICATE-----'''


class Command(NoArgsCommand):
    args = "{ --list | --host <hostname> }"
    help = "Generates a dynamic inventory for ansible from the MWS database."
    output_transaction = True
    option_list = NoArgsCommand.option_list + (
        make_option("--list", action='store_true',
                    help="emit a list of configured MWS clients"),
        make_option("--host", action='store',
                    help="emit the configuration of a single MWS client"),
        )

    def handle_noargs(self, list=None, host=None, outfile=None, **options):
        if (not list and not host) or (list and host):
            raise CommandError("Exactly one of --list and --host must be specified.")
        outfile = outfile or sys.stdout
        if list:
            vms = VirtualMachine.objects.filter(
                service__status__in=('ansible', 'ansible_queued', 'ready', 'postinstall'),
                service__site__disabled=False, service__site__deleted=False, service__site__end_date__isnull=True)
            result = {'_meta': {'hostvars': {}}, group: [self.hostid(vm) for vm in vms]}
            for site in Site.objects.all():
                if not site.is_canceled():
                    result[self.sitegroup(site)] = [
                        self.hostid(vm) for vm in vms.filter(service__site=site)]
            for vm in vms:
                result['_meta']['hostvars'][self.hostid(vm)] = (
                    self.hostvars(vm))
            json.dump(result, outfile)
            outfile.write("\n")
        else:
            vm = VirtualMachine.objects.get(
                network_configuration__name=host)
            json.dump(self.hostvars(vm), outfile)
            outfile.write("\n")

    def sitegroup(self, site):
        return "mwssite-%d" % (site.id,)

    def servicegroup(self, service):
        return "mwsservice-%d" % (service.id,)

    def hostid(self, vm):
        return vm.network_configuration.name

    def hostvars(self, vm):
        v = {}
        v['ansible_ssh_host'] = (vm.network_configuration.name or
                                 vm.network_configuration.IPv4 or
                                 vm.network_configuration.IPv6)
        v['mws_name'] = vm.site.name
        v['mws_webmaster_email'] = vm.site.email

        def user_vars(user, service):
            uv = {}
            uv['username'] = user.username
            uv['groups'] = list(UnixGroup.objects.filter(service__site=service.site, users__in=[user],
                                                         to_be_deleted=False).values_list('name', flat=True))
            if hasattr(user, "mws_user") and user.mws_user.uid is not None:
                uv['uid'] = user.mws_user.uid
                if user.mws_user.ssh_public_key:
                    uv['ssh_key'] = user.mws_user.ssh_public_key
            return uv

        # List of active users (admin and ssh only) together with the list of supporters
        v['mws_users'] = [user_vars(u, vm.service) for u in
                          vm.site.list_of_all_type_of_active_users() + list(vm.site.supporters.all())]

        def vhost_vars(vh):
            # List of variables for each vhost
            vhv = {}
            vhv['id'] = vh.id
            vhv['name'] = vh.name
            # List of domain names associated to the vhost (only those already accepted or external [non cam.ac.uk])
            vhv['domains'] = [dom.name for dom in
                              vh.domain_names.filter(Q(status='accepted') | Q(status='external'))]
            # The main domain where all the domain names associated will redirect to
            if vh.main_domain:
                vhv['main_domain'] = vh.main_domain.name
            # The TLS certificate if already uploaded
            if vh.certificate:
                vhv['certificate'] = vh.certificate
                vhv['certificatechain'] = CERT_CHAIN
            if vh.tls_key_hash:
                vhv['tls_key_hash'] = vh.tls_key_hash
            # If is TLS enabled whether the certificate has been yet uploaded or not
            vhv['tls_enabled'] = vh.tls_enabled
            # Generate csr if there is a request from the web panel
            vhv['generate_csr'] = 'tls_key_hash' in vhv and vh.tls_key_hash == "requested"
            vhv['generate_csr_renewal'] = 'tls_key_hash' in vhv and vh.tls_key_hash == "renewal"
            vhv['generate_csr_renewal_cert'] = 'tls_key_hash' in vhv and vh.tls_key_hash == "renewal_waiting_cert"
            vhv['generate_renewal_cert'] = 'tls_key_hash' in vhv and vh.tls_key_hash == "renewal_cert"
            # Type of webapp: wordpress, drupal, etc.
            vhv['webapp'] = vh.webapp
            return vhv

        # List of Vhosts of the production service (the test service uses the production one)
        v['mws_vhosts'] = [vhost_vars(vh) for vh in vm.service.vhosts.all()] if vm.service.primary else \
            [vhost_vars(vh) for vh in vm.service.site.production_service.vhosts.all()]

        # Is the VM the production or the test one?
        v['mws_is_primary'] = vm.primary

        # Has this an active test Service?
        v['mws_test_active'] = vm.service.site.test_service.active
        v['mws_test_name'] = vm.service.site.test_service.network_configuration.name

        # Network configuration of the VM
        if vm.network_configuration.IPv4:
            v['mws_ipv4'] = vm.network_configuration.IPv4
            v['mws_ipv4_netmask'] = vm.network_configuration.IPv4_netmask
            v['mws_ipv4_gateway'] = vm.network_configuration.IPv4_gateway
        if vm.network_configuration.IPv6:
            v['mws_ipv6'] = vm.network_configuration.IPv6

        # is there any vhost TLS enabled? That is used later on to use http or https for
        # redirections that do not match any vhost
        v['mws_tls_enabled'] = any(['certificate' in vhv for vhv in v['mws_vhosts']])

        # version of the operating system
        v['mws_os'] = vm.operating_system

        # mws_site_group refers to the Ansible host group representing
        # this host's site.
        v['mws_site_group'] = self.sitegroup(vm.site)
        # mws_site_id is a convenient string identifying the site for use
        # in filenames etc.
        v['mws_site_id'] = v['mws_site_group']

        # mws_service_group refers to the Ansible host group representing
        # this host's service.
        v['mws_service_group'] = self.servicegroup(vm.service)
        v['mws_service_fqdn'] = vm.service.network_configuration.name
        v['mws_service_ipv4'] = vm.service.network_configuration.IPv4
        v['mws_service_ipv4_netmask'] = vm.service.network_configuration.IPv4_netmask
        v['mws_service_ipv4_gateway'] = vm.service.network_configuration.IPv4_gateway
        v['mws_service_ipv6'] = vm.service.network_configuration.IPv6

        # List of Apache modules to be installed and enable
        v['mws_apache_mods_enabled'] = list(ApacheModule.objects.filter(services__id=vm.service.id, available=True)
                                            .values_list('name', flat=True))

        # List of Apache modules to be disabled
        v['mws_apache_mods_disabled'] = list(ApacheModule.objects.exclude(services__id=vm.service.id)
                                             .values_list('name', flat=True))

        # List of PHP libraries to be installed
        v['mws_php_libs_enabled'] = list(PHPLib.objects.filter(services__id=vm.service.id, available=True)
                                         .values_list('name', flat=True))

        # List of PHP libraries to be deleted
        v['mws_php_libs_disabled'] = list(PHPLib.objects.exclude(services__id=vm.service.id)
                                          .values_list('name', flat=True))

        # List of Unix groups and their associated gids
        v['mws_unix_groups'] = []
        for unix_group in UnixGroup.objects.filter(service__site=vm.service.site, to_be_deleted=False):
            v['mws_unix_groups'].append({'name': unix_group.name, 'gid': INITIAL_GID-unix_group.id})

        # List of Unix Groups to be deleted
        v['mws_delete_unix_groups'] = []
        for unix_group in UnixGroup.objects.filter(service__site=vm.service.site, to_be_deleted=True):
            v['mws_delete_unix_groups'].append({'name': unix_group.name})

        # Let ansible know if the VM should be quarantined (apache and exim services disabled)
        v['mws_quarantined'] = vm.service.quarantined

        return v
