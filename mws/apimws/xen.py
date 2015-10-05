from __future__ import absolute_import
import copy
import logging
import re
import tempfile
import uuid
import json
from celery import shared_task, Task
from django.conf import settings
from django.core.urlresolvers import reverse
import subprocess
from apimws.views import post_installation
from sitesmanagement.models import VirtualMachine, NetworkConfig, Service, SiteKeys, Vhost, DomainName


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
        LOGGER.error("VM API request: %s\nVM API response: %s", api_command, e.output)
        raise VMAPIFailure()
    return response


class XenWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if type(exc) is subprocess.CalledProcessError:
            LOGGER.error("An error happened when trying to communicate with Xen's VM API.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n\n"
                         "The output from the command was: %s\n", task_id, args, einfo, exc.output)
        else:
            LOGGER.error("An error happened when trying to communicate with Xen's VM API.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\n The traceback is: \n %s", task_id, args, einfo)


def secrets_prealocation(vm):
    # TODO move this to preallocation
    # Gets all the keys generated for the site and generates the fingerprint and the SSHFP from them
    # It sends the SSHFP record to ip-register
    service = vm.service
    servicesshfprecord = ""
    hostsshfprecord = ""
    sqlcommand = ""

    for keytype in ["sshrsa", "sshdsa", "sshecdsa", "sshed25519"]:
        p = subprocess.Popen(["userv", "mws-admin", "mws_pubkey"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(json.dumps({"id": service.site.id, "keytype": keytype}))
        try:
            result = json.loads(stdout)
        except ValueError as e:
            LOGGER.error("mws_pubkey response is not properly formated:\nstdout: %s\nstderr: %s" % (stdout, stderr))
            raise e

        pubkey = tempfile.NamedTemporaryFile()
        pubkey.write(result["pubkey"])
        pubkey.flush()
        fingerprint = subprocess.check_output(["ssh-keygen", "-lf", pubkey.name])

        SiteKeys.objects.create(site=service.site, type=keytype.replace("ssh", "").upper(), public_key=result["pubkey"],
                                fingerprint=re.search("([0-9a-f]{2}:)+[0-9a-f]{2}", fingerprint).group(0))

        if keytype is not "sshed25519":  # "sshed25519" as of 2015 is not supported by jackdaw
            sshkeygeno = subprocess.check_output(["ssh-keygen", "-r", "replacehostname", "-f", pubkey.name])
            servicesshfprecord += sshkeygeno.replace('replacehostname', service.network_configuration.name)
            hostsshfprecord += sshkeygeno.replace('replacehostname', vm.network_configuration.name)
            sshkeygeno = sshkeygeno.split('\n')
            for i in [0, 1]:
                sshkglnout = sshkeygeno[i].split(' ')
                sqlcommand += "INSERT INTO IPREG.MY_SSHFP (NAME, ALGORITHM, FPTYPE, FINGERPRINT) " \
                              "VALUES ('%s', %i, %i, '%s');\n" % (service.network_configuration.name,
                                                                  int(sshkglnout[3]), int(sshkglnout[4]), sshkglnout[5])
                sqlcommand += "INSERT INTO IPREG.MY_SSHFP (NAME, ALGORITHM, FPTYPE, FINGERPRINT) " \
                              "VALUES ('%s', %i, %i, '%s');\n" % (vm.network_configuration.name, int(sshkglnout[3]),
                                                                  int(sshkglnout[4]), sshkglnout[5])
        pubkey.close()

    from apimws.utils import ip_register_api_sshfp
    ip_register_api_sshfp("%s\n\n%s\n\n%s" % (hostsshfprecord, servicesshfprecord, sqlcommand))

    # Create a default Vhost with the Service FQDN as main domain name
    default_vhost = Vhost.objects.create(service=service, name="default")
    default_vhost_dn = DomainName.objects.create(name=service.network_configuration.name,
                                                 status="accepted", vhost=default_vhost)
    default_vhost.main_domain = default_vhost_dn
    default_vhost.save()


@shared_task(base=XenWithFailure)
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
        raise AttributeError("No host network configuration")

    parameters["netconf"] = netconf
    parameters["callback"] = {
        "endpoint": "%s%s" % (settings.MAIN_DOMAIN, reverse(post_installation)),
        "vm_id": vm.id,
        "secret": str(vm.token),
    }

    service.status = 'installing'
    service.save()

    response = vm_api_request(command='create', parameters=parameters)

    try:
        jresponse = json.loads(response)
    except ValueError as e:
        LOGGER.error("VM API response is not properly formated: %s", response)
        vm.name = vm.network_configuration.name
        vm.save()
        raise e

    try:
        if 'vmid' in jresponse:
            vm.name = jresponse['vmid']
        else:
            vm.name = vm.network_configuration.name
    except Exception as e:
        vm.name = vm.network_configuration.name
    vm.save()
    from apimws.models import AnsibleConfiguration
    AnsibleConfiguration.objects.update_or_create(service=service, key='os',
                                                  defaults={'value': getattr(settings,
                                                                             "OS_VERSION_VMXENAPI", "jessie")})
    secrets_prealocation(vm)


def recreate_vm(vm):
    service = vm.service
    network_configuration = vm.network_configuration
    parameters = {}
    parameters["site-id"] = "mwssite-%d" % service.site.id
    netconf = {}
    if network_configuration.IPv4:
        netconf["IPv4"] = network_configuration.IPv4
    if network_configuration.IPv6:
        netconf["IPv6"] = network_configuration.IPv6
    if network_configuration.name:
        netconf["hostname"] = network_configuration.name
    os = vm.service.ansible_configuration.filter(key='os')
    if os:
        parameters["os"] = os[0].value
    parameters["netconf"] = netconf
    parameters["callback"] = {
        "endpoint": "%s%s" % (settings.MAIN_DOMAIN, reverse(post_installation)),
        "vm_id": vm.id,
        "secret": str(vm.token),
    }

    service.status = 'installing'
    service.save()

    response = vm_api_request(command='create', parameters=parameters)

    try:
        jresponse = json.loads(response)
    except ValueError as e:
        LOGGER.error("VM API response is not properly formated: %s", response)
        vm.name = vm.network_configuration.name
        vm.save()
        raise e

    try:
        if 'vmid' in jresponse:
            vm.name = jresponse['vmid']
        else:
            vm.name = vm.network_configuration.name
    except Exception as e:
        vm.name = vm.network_configuration.name
    vm.save()


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


@shared_task(base=XenWithFailure)
def change_vm_power_state(vm, on):
    if on != 'on' and on != 'off':
        raise VMAPIInputException("passed wrong parameter power %s" % on)
    vm_api_request(command='button', parameters={"action": "power%s" % on, "vmid": vm.name})
    return True


@shared_task(base=XenWithFailure)
def reset_vm(vm):
    vm_api_request(command='button', parameters={"action": "reboot", "vmid": vm.name})
    return True


@shared_task(base=XenWithFailure)
def destroy_vm(vm):
    vm_api_request(command='delete', parameters={'vmid': vm.name})
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


@shared_task(base=XenWithFailure)
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

    response = vm_api_request(command='clone', vmid=original_vm.name, parameters=parameters)

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
