from django.core.management.base import NoArgsCommand, CommandError
from optparse import make_option
from sys import stdout
import json

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
    def handle_noargs(self, list, host, **options):
        if (not list and not host) or (list and host):
            raise CommandError, (
                "Exactly one of --list and --host must be specified.")
        if list:
            vms = VirtualMachine.objects.filter(
                status__in=('ansible', 'ready'))
            result = { '_meta': { 'hostvars': { } } }
            result[group] = [self.hostid(vm) for vm in vms]
            for vm in vms:
                result['_meta']['hostvars'][self.hostid(vm)] = (
                    self.hostvars(vm))
            json.dump(result, stdout)
            print
        else:
            if not host.startswith(idprefix):
                raise CommandError, "Host identifier not found"
            host = host[len(idprefix):]
            vm = VirtualMachine.objects.get(id=int(host))
            json.dump(self.hostvars(vm), stdout)
            print
    def hostid(self, vm):
        return idprefix + str(vm.id)
    def hostvars(self, vm):
        return { 'ansible_ssh_host': vm.network_configuration.mws_domain }
