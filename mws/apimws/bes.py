'''API to output data to Bes++'''
import json
from datetime import date
from django.db.models import Q
from django.http import HttpResponse
from stronghold.decorators import public
from sitesmanagement.models import Site, VirtualMachine


@public
def bes(request):
    json_all = []
    for site in Site.objects.filter(
                    Q(deleted=False, services__status__in=('ansible', 'ansible_queued', 'ready'))
                    & (Q(service__site__end_date__isnull=True) | Q(service__site__end_date__gt=date.today()))):
        # Do not backup sites that have been cancelled or sites that are not ready
        # Backups from sites that disappear from the bes API will still be kept during 14 days before getting deleted
        json_site = {}
        json_site['id'] = "mwssite-%s" % site.id
        for sitekey in site.keys.all():
            json_site['ssh-public-key-%s' % sitekey.type.lower()] = sitekey.public_key
        json_vms = []
        for vm in VirtualMachine.objects.filter(service__site = site):
            json_vm = {}
            json_vm['name'] = vm.name
            json_vm['disabled'] = vm.service.site.disabled
            json_vm['fqdn'] = vm.network_configuration.name
            json_vm['service_fqdn'] = vm.service.network_configuration.name
            json_vm['location'] = 'mws-cluster-1'  # TODO change it for a variable in the model
            json_vm['backup'] = ['/replicated']  # TODO change it for a variable?
            json_vm['backup-user'] = "dump"  # TODO change it for a variable in the model
            json_vms.append(json_vm)
        json_site['vms'] = json_vms
        json_all.append(json_site)
    return HttpResponse(json.dumps(json_all), content_type='application/json')
