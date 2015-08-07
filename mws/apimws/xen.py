from __future__ import absolute_import
import copy
import logging
import uuid
import json
from celery import shared_task, Task
from django.conf import settings
from django.core.urlresolvers import reverse
import subprocess
from apimws.views import post_installation
from sitesmanagement.models import VirtualMachine, NetworkConfig, Service


LOGGER = logging.getLogger('mws')


class VMAPINotWorkingException(Exception):
    pass


class VMAPIInputException(Exception):
    pass


class VMAPIFailure(Exception):
    pass


def vm_api_request(**json_object):
    if not getattr(settings, 'VM_END_POINT_COMMAND', False):
        raise VMAPIFailure("VM_END_POINT_COMMAND not found")
    api_command = copy.copy(settings.VM_END_POINT_COMMAND)
    api_command.append(json_object['command'])
    api_command.append("'%s'" % json.dumps(json_object['parameters']))
    try:
        response = subprocess.check_output(api_command, stderr=subprocess.STDOUT)
        LOGGER.info("VM API request: %s\nVM API response: %s", api_command, response)
    except subprocess.CalledProcessError as e:
        response = e.output
        LOGGER.error("VM API request: %s\nVM API response: %s", api_command, response)
        raise VMAPIFailure(json_object, response)
    return response


def on_vm_api_failure(request, response):
    """ This function logs the error in the logger. The logger can be configured to send an email.
    :param request: the VM API request
    :param response: the VM API response
    :return: False
    """
    LOGGER.error("VM API request: %s\nVM API response: %s", request, response)
    raise VMAPIFailure(request, response)


class TaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to communicate with Xen's VM API.\n The task id is %s. \n\n "
                     "The parameters passed to the task were: %s \n\n The traceback is: \n %s", task_id, args, einfo)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def new_site_primary_vm(service, host_network_configuration=None):
    parameters = {}
    parameters["site-id"] = "mwssite-%d" % service.site.id
    if getattr(settings, 'OS_VERSION_VMXENAPI', False):
        parameters["os"] = settings.OS_VERSION_VMXENAPI

    if host_network_configuration:
        netconf = {}
        if host_network_configuration.IPv4:
            netconf["IPv4"] = host_network_configuration.IPv4
        if host_network_configuration.IPv6:
            netconf["IPv6"] = host_network_configuration.IPv6
        if host_network_configuration.name:
            netconf["hostname"] = host_network_configuration.name
        vm = VirtualMachine.objects.create(service=service, token=uuid.uuid4(),
                                           network_configuration=host_network_configuration)
    else:
        netconf = {}
        if service.network_configuration.IPv4:
            netconf["IPv4"] = service.network_configuration.IPv4
        if service.network_configuration.IPv6:
            netconf["IPv6"] = service.network_configuration.IPv6
        if service.network_configuration.name:
            netconf["hostname"] = service.network_configuration.name
        vm = VirtualMachine.objects.create(service=service, token=uuid.uuid4(),
                                           network_configuration=service.network_configuration)

    parameters["netconf"] = netconf
    parameters["callback"] = {
        "endpoint": "%s%s" % (settings.MAIN_DOMAIN, reverse(post_installation)),
        "vm_id": vm.id,
        "secret": str(vm.token),
    }

    service.status = 'installing'
    service.save()

    try:
        response = vm_api_request(command='create', parameters=parameters)
        # TODO this is temporal until we support service network configuration, then we will use
        # host_network_configuration.ipv6 as a parameter for ip in vm_api_request and host_network_configuration.name
        # for the parameter hostname in vm_api_request
    except VMAPIFailure as e:
        return on_vm_api_failure(*e.args)
    except AttributeError:
        return
    except Exception as e:
        raise new_site_primary_vm.retry(exc=e)

    response = json.loads(response)

    if 'vmid' in response:
        vm.name = response['vmid']
    else:
        vm.name = vm.network_configuration.name
    vm.save()
    return True


def get_vm_power_state(vm):
    try:
        # TODO implement something sensible
        response = {"powerState": "On"}
    except VMAPIFailure:
        raise
    except Exception as e:
        raise VMAPINotWorkingException(e.message)

    if response['powerState'] == 'Off':
        return "Off"
    elif response['powerState'] == 'On':
        return "On"
    else:
        raise VMAPIFailure(None, response)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def change_vm_power_state(vm, on):
    if on != 'on' and on != 'off':
        raise VMAPIInputException("passed wrong parameter power %s" % on)
    try:
        vm_api_request(command='button', parameters={"action": "power%s" % on, "vmid": vm.name})
    except VMAPIFailure as e:
        return on_vm_api_failure(*e.args)
    except Exception as e:
        raise change_vm_power_state.retry(exc=e)
    return True


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def reset_vm(vm):
    try:
        vm_api_request(command='button', parameters={"action": "reboot", "vmid": vm.name})
    except VMAPIFailure as e:
        return on_vm_api_failure(*e.args)
    except Exception as e:
        raise reset_vm.retry(exc=e)  # TODO are we sure we want to do that?
    return True


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def destroy_vm(vm):
    try:
        vm_api_request(command='delete', parameters={'vmid': vm.name})
    except VMAPIFailure as e:
        return on_vm_api_failure(*e.args)
    except Exception as e:
        raise destroy_vm.retry(exc=e)

    return True


def clone_vm(site, primary_vm):
    if primary_vm:
        original_service = site.production_service
        delete_service = site.test_service
    else:
        original_service = site.test_serivce
        delete_service = site.production_service

    if not delete_service:
        raise Exception("A site has no production or test service")  # TODO create custom exception

    # TODO restore this service in case the clonning does not work? then do not delete the VMs

    service_netconf = delete_service.network_configuration
    service_type = delete_service.type
    delete_service.delete()

    destination_service = Service.objects.create(site=original_service.site, type=service_type,
                                                 network_configuration=service_netconf, status='requested')
    destination_vm = VirtualMachine.objects.create(token=uuid.uuid4(), service=destination_service,
                                                   network_configuration=NetworkConfig.get_free_host_config())

    clone_vm_api_call.delay(original_service, destination_vm)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def clone_vm_api_call(original_service, destination_vm):

    original_vm = original_service.virtual_machines.first()
    destination_service = destination_vm.service

    parameters = {}
    parameters["netconf"] = {}
    if destination_vm.network_configuration.IPv4:
        parameters["netconf"]["IPv4"] = destination_vm.network_configuration.IPv4
    if destination_vm.network_configuration.IPv6:
        parameters["netconf"]["IPv6"] = destination_vm.network_configuration.IPv6
    if destination_vm.network_configuration.name:
        parameters["netconf"]["hostname"] = destination_vm.network_configuration.name

    try:
        response = vm_api_request(command='clone', vmid=original_vm.name, parameters=parameters)
    except VMAPIFailure as e:
        return on_vm_api_failure(*e.args)
    except Exception as e:
        raise clone_vm_api_call.retry(exc=e)

    response = json.loads(response)

    if 'vmid' in response:
        destination_vm.name = response['vmid']
    else:
        destination_vm.name = destination_vm.network_configuration.name
    destination_vm.save()

    destination_service.status = 'ready'
    destination_service.save()

    # Copy Unix Groups
    for unix_group in original_service.unix_groups.all():
        copy_users = unix_group.users.all()
        unix_group.pk = None
        unix_group.service = destination_service
        unix_group.save()
        unix_group.users = copy_users

    # Copy Ansible Configuration
    for ansible_conf in original_service.ansible_configuration.all():
        ansible_conf.pk = None
        ansible_conf.service = destination_service
        ansible_conf.save()

    # Copy vhosts
    # TODO copy Domain Names
    for vhost in original_service.vhosts.all():
        vhost.pk = None
        vhost.main_domain = None
        vhost.service = destination_service
        vhost.save()

    return True
