from django.core.management.base import NoArgsCommand, CommandError
from optparse import make_option
import sys
import json
from itertools import chain

from sitesmanagement.models import VirtualMachine

idprefix = "mwsclient-"
group = "mwsclients"

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
            raise CommandError, (
                "Exactly one of --list and --host must be specified.")
        outfile = outfile or sys.stdout
        if list:
            vms = VirtualMachine.objects.filter(
                status__in=('ansible', 'ready'))
            result = { '_meta': { 'hostvars': { } } }
            result[group] = [self.hostid(vm) for vm in vms]
            for vm in vms:
                result['_meta']['hostvars'][self.hostid(vm)] = (
                    self.hostvars(vm))
            json.dump(result, outfile)
            outfile.write("\n")
        else:
            if not host.startswith(idprefix):
                raise CommandError, "Host identifier not found"
            host = host[len(idprefix):]
            vm = VirtualMachine.objects.get(id=int(host))
            json.dump(self.hostvars(vm), outfile)
            outfile.write("\n")
    def hostid(self, vm):
        return idprefix + str(vm.id)
    def hostvars(self, vm):
        v = { }
        v['ansible_ssh_host'] = vm.hostname
        v['mws_name'] = vm.site.name
        v['mws_webmaster_email'] = vm.site.email
        def user_vars(user):
            uv = { }
            uv['username'] = user.username
            if hasattr(user, "mws_user") and user.mws_user.uid is not None:
                uv['uid'] = user.mws_user.uid
                if user.mws_user.ssh_public_key:
                    uv['ssh_key'] = user.mws_user.ssh_public_key
            return uv
        v['mws_users'] = [ user_vars(u) for u in
                           vm.site.list_of_all_type_of_active_users()]
        def vhost_vars(vh):
            vhv = { }
            vhv['name'] = vh.name
            vhv['domains'] = [dom.name for dom in
                                vh.domain_names.filter(status='accepted')]
            if vh.main_domain:
                vhv['main_domain'] = vh.main_domain.name
            if vh.certificate:
                vhv['certificate'] = vh.certificate
            vhv['tls_enabled'] = 'certificate' in vhv
            return vhv
        v['mws_vhosts'] = [ vhost_vars(vh) for vh in vm.vhosts.all()]
        v['mws_is_primary'] = vm.primary
        v['mws_ipv4'] = vm.ipv4
        v['mws_ipv6'] = vm.ipv6
        v['mws_tls_enabled'] = any(['certificate' in vhv
                                    for vhv in v['mws_vhosts']])
        return v
