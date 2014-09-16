import json
import os
import random
import string
import crypt
from django.conf import settings
import requests
from sitesmanagement.models import VirtualMachine, NetworkConfig


class PlatformsAPINotWorkingException(Exception):
    pass

class PlatformsAPIInputException(Exception):
    pass

class NoPrealocatedPrivateIPsAvailable(Exception):
    pass


def new_site_primary_vm(site, primary):
    network_configuration = NetworkConfig.objects.filter(virtual_machine=None).first()
    vm = VirtualMachine.objects.create(primary=primary, status='requested',
                                       network_configuration=network_configuration, site=site)
    return install_vm(vm)


def install_vm(vm):
    return True


def get_vm_power_state(vm):
    return vm.vm_status_demo.get_status_display


def change_vm_power_state(vm, on):
    if on != 'on' and on != 'off':
        raise PlatformsAPIInputException("passed wrong parameter power %s" % on)

    vm.vm_status_demo.status = on
    vm.save()
    return True


def reset_vm(vm):
    return True


def destroy_vm(vm):
    return True


def clone_vm(site, primary_vm):
    if primary_vm:
        if site.secondary_vm:
            site.secondary_vm.delete()
    else:
        if site.primary_vm:
            site.primary_vm.delete()

    network_configuration = NetworkConfig.objects.filter(virtual_machine=None).first()

    if network_configuration is None:
        raise NoPrealocatedPrivateIPsAvailable()

    VirtualMachine.objects.create(primary=(not primary_vm), status='requested',
                                  network_configuration=network_configuration, site=site)

    return True