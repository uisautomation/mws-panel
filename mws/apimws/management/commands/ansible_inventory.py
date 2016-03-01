import sys
import json
from django.core.management.base import NoArgsCommand, CommandError
from optparse import make_option
from django.db.models import Q
from apimws.models import ApacheModule, PHPLib
from sitesmanagement.models import VirtualMachine, Site, UnixGroup


group = "mwsclients"
# We start Unix Group IDs by the 2^16-2 which is the last one free in Debian and assign them to groups in decrease order
INITIAL_GID = 4294967293


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
            uv['groups'] = list(UnixGroup.objects.filter(service=service, users__in=[user], to_be_deleted=False)
                                .values_list('name', flat=True))
            if hasattr(user, "mws_user") and user.mws_user.uid is not None:
                uv['uid'] = user.mws_user.uid
                if user.mws_user.ssh_public_key:
                    uv['ssh_key'] = user.mws_user.ssh_public_key
            return uv
        v['mws_users'] = [user_vars(u, vm.service) for u in
                          vm.site.list_of_all_type_of_active_users()]

        def vhost_vars(vh):
            vhv = {}
            vhv['id'] = vh.id
            vhv['name'] = vh.name
            vhv['domains'] = [dom.name for dom in
                              vh.domain_names.filter(Q(status='accepted') | Q(status='external'))]
            if vh.main_domain:
                vhv['main_domain'] = vh.main_domain.name
            if vh.certificate:
                vhv['certificate'] = vh.certificate
            if vh.tls_key_hash:
                vhv['tls_key_hash'] = vh.tls_key_hash
            vhv['tls_enabled'] = vh.tls_enabled
            vhv['generate_csr'] = 'tls_key_hash' in vhv and vh.tls_key_hash == "requested"
            vhv['webapp'] = vh.webapp
            return vhv

        v['mws_vhosts'] = [vhost_vars(vh) for vh in vm.service.vhosts.all()]
        v['mws_is_primary'] = vm.primary
        if vm.network_configuration.IPv4:
            v['mws_ipv4'] = vm.network_configuration.IPv4
            v['mws_ipv4_netmask'] = vm.network_configuration.IPv4_netmask
            v['mws_ipv4_gateway'] = vm.network_configuration.IPv4_gateway
        if vm.network_configuration.IPv6:
            v['mws_ipv6'] = vm.network_configuration.IPv6
        v['mws_tls_enabled'] = any(['certificate' in vhv
                                    for vhv in v['mws_vhosts']])
        v['mws_os'] = vm.operating_system

        v['mws_with_pacemaker'] = False

        # Corosync needs a 32-bit node ID.  ID 0 is reserved, and
        # according to corosync.conf(5), "Some openais clients require
        # a signed 32 bit nodeid that is greater than zero".  For
        # safety, we thus insist on something between 1 and 0x7fffffff
        # inclusive.  For a reasonably-sized MWS, just using the
        # primary key of the VirtualMachine should be fine.
        v['mws_cluster_nodeid'] = vm.id
        assert(1 <= v['mws_cluster_nodeid'] <= 0x7fffffff)

        # mws_site_group refers to the Ansible host group representing
        # this host's site.
        v['mws_site_group'] = self.sitegroup(vm.site)
        # mws_site_id is a convenient string identifying the site for use
        # in filenames etc.
        v['mws_site_id'] = v['mws_site_group']

        # mws_service_group refers to the Ansible host group representing
        # this host's service.
        if vm.service.type == "production":
            # Only output mws_service_* if the VM is in the prod service, do not use/show test service addresses
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
        for unix_group in UnixGroup.objects.filter(service=vm.service, to_be_deleted=False):
            v['mws_unix_groups'].append({'name': unix_group.name, 'gid': INITIAL_GID-unix_group.id})

        # List of Unix Groups to be deleted
        v['mws_delete_unix_groups'] = []
        for unix_group in UnixGroup.objects.filter(service=vm.service, to_be_deleted=True):
            v['mws_delete_unix_groups'].append({'name': unix_group.name})

        # Let ansible know if the VM should be quarantined (apache and exim services disabled)
        v['mws_quarantined'] = vm.service.quarantined

        return v
