import json
import random
import string
import crypt
import requests
from sitesmanagement.models import VirtualMachine, NetworkConfig


def new_site_primary_vm(site, primary):
    network_configuration = NetworkConfig.objects.filter(virtual_machine=None).first()
    vm = VirtualMachine.objects.create(primary=primary, status='requested',
                                       network_configuration=network_configuration, site=site)
    json_object = {
        'username': 'mwsadmin',
        'secret': crypt.crypt("7d503557b69ecd94c921784541f18bc2f9ecdd62",
                              "$6$"+''.join(random.sample(string.hexdigits, 16))),
        'command': 'create',
        'ip': vm.network_configuration.IPv4,
        'hostname': vm.network_configuration.mws_domain,
    }
    headers = {'Content-type': 'application/json'}
    r = requests.post("https://bes.csi.cam.ac.uk/mws-api/v1/vm.json", data=json.dumps(json_object), headers=headers)
    #TODO explore request


def get_vm_power_state(vm):
    json_object = {
        'username': 'mwsadmin',
        'secret': crypt.crypt("7d503557b69ecd94c921784541f18bc2f9ecdd62",
                              "$6$"+''.join(random.sample(string.hexdigits, 16))),
        'command': 'get power state',
        'vmid': '502b427f-9f9d-9017-076e-ae83a0498faf' # TODO change that for vm.name
    }
    headers = {'Content-type': 'application/json'}
    r = requests.post("https://bes.csi.cam.ac.uk/mws-api/v1/vm.json", data=json.dumps(json_object), headers=headers)
    try:
        response = json.loads(r.text)
    except Exception as e:
        pass # TODO raise error

    if response['result'] == 'Success':
        if response['powerState'] == 'poweredOff':
            return "Off"
        elif response['powerState'] == 'poweredOn':
            return "On"
        else:
            pass # TODO raise error
    else:
        pass # TODO raise error


def change_vm_power_state(vm, on):
    if on != 'on' and on != 'off':
        pass # TODO raise error

    json_object = {
        'username': 'mwsadmin',
        'secret': crypt.crypt("7d503557b69ecd94c921784541f18bc2f9ecdd62",
                              "$6$"+''.join(random.sample(string.hexdigits, 16))),
        'command': 'power '+on,
        'vmid': '502b427f-9f9d-9017-076e-ae83a0498faf' # TODO change that for vm.name
    }

    headers = {'Content-type': 'application/json'}
    r = requests.post("https://bes.csi.cam.ac.uk/mws-api/v1/vm.json", data=json.dumps(json_object), headers=headers)
    try:
        response = json.loads(r.text)
    except Exception as e:
        pass # TODO raise error

    if response['result'] == 'Success':
        return True
    else:
        return False # TODO raise error