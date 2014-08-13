import json
from django.core.management.base import BaseCommand, CommandError
from sitesmanagement.models import NetworkConfig


class Command(BaseCommand):
    args = '<ipv4_address>'
    help = 'Exports to a JSON format all the ansible configuration parameters in the database for a given IPv4 ' \
           'address of a site'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Only one parameter <ipv4_address> permitted")
        else:
            try:
                site_ipv4 = args[0]
                nc = NetworkConfig.objects.get(IPv4=site_ipv4)
            except NetworkConfig.DoesNotExist:
                raise CommandError('The IPv4 %s does not exist in the database' % site_ipv4)

            ansibleconfiguration_set = nc.virtual_machine.site.ansibleconfiguration_set.all()
            ansibleconfiguration_dict = {}
            for ansibleconfiguration in ansibleconfiguration_set:
                ansibleconfiguration_dict[ansibleconfiguration.key] = ansibleconfiguration.value
            self.stdout.write(json.dumps(ansibleconfiguration_dict))