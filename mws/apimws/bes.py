'''API to output data to Bes++'''
import json

from django.core import serializers
from django.http import HttpResponse
from stronghold.decorators import public
from sitesmanagement.models import Site, VirtualMachine


@public
def bes(request):
    json_all = []
    for site in Site.objects.all():
        json_site = {}
        json_site['id'] = "mwssite-%s" % site.id
        for sitekey in site.keys.all():
            json_site['ssh-public-key-%s' % sitekey.type.lower()] = sitekey.public_key
        json_vms = []
        for vm in VirtualMachine.objects.filter(service__site = site):
            json_vm = {}
            json_vm['name'] = vm.name
            json_vm['fqdn'] = vm.network_configuration.name
            json_vm['service_fqdn'] = vm.service.network_configuration.name
            json_vm['location'] = 'mws-cluster-1'  # TODO change it for a variable in the model
            json_vm['backup'] = True  # TODO change it for a variable in the model
            json_vm['backup-user'] = "dump"  # TODO change it for a variable in the model
            json_vms.append(json_vm)
        json_site['vm'] = json_vms
        json_all.append(json_site)
    return HttpResponse(json.dumps(json_all), content_type='application/json')
