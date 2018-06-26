"""
A module to allow the testing of mws-panel locally - only updates model when performing a xen function.
"""
from __future__ import absolute_import

import hashlib
import logging
import md5
import subprocess
import uuid

from celery import shared_task, Task
from django.conf import settings
from django.urls import reverse

from apimws.models import Cluster
from apimws.views import post_installation
from libs.sshpubkey import SSHPubKey
from sitesmanagement.models import NetworkConfig, VirtualMachine, SiteKey, Vhost, DomainName

LOGGER = logging.getLogger('mws')


class VMAPIInputException(Exception):
    pass


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


def secrets_prealocation_vm(vm):
    # Gets all the keys generated for the site and generates the fingerprint and the SSHFP from them
    # It sends the SSHFP record to ip-register
    service = vm.service

    for keytype in SiteKey.ALGORITHMS:
        SiteKey.objects.get_or_create(site=service.site, type=keytype,
                                      public_key=uuid.uuid4(), fingerprint=uuid.uuid4(), fingerprint2=uuid.uuid4())


@shared_task(base=XenWithFailure)
def new_site_primary_vm(service, host_network_configuration=None):
    parameters = {}
    parameters["site-id"] = "mwssite-%d" % service.site.id
    parameters["os"] = getattr(settings, 'OS_VERSION', "jessie")

    if host_network_configuration:
        netconf = {}
        if host_network_configuration.IPv4:
            netconf["IPv4"] = host_network_configuration.IPv4
        if host_network_configuration.IPv6:
            netconf["IPv6"] = host_network_configuration.IPv6
        if host_network_configuration.name:
            netconf["hostname"] = host_network_configuration.name
        vm = VirtualMachine.objects.create(service=service, token=uuid.uuid4(),
                                           network_configuration=host_network_configuration, cluster=which_cluster())
    else:
        raise AttributeError("No host network configuration")

    parameters["features"] = {
        "cpu": service.site.type.numcpu,
        "ram": service.site.type.sizeram*1024,
        "disk": service.site.type.sizedisk,
    }

    parameters["netconf"] = netconf
    parameters["callback"] = {
        "endpoint": "%s%s" % (settings.MAIN_DOMAIN, reverse(post_installation)),
        "vm_id": vm.id,
        "secret": str(vm.token),
    }

    service.status = 'installing'
    service.save()

    vm.name = vm.network_configuration.name
    vm.save()
    from apimws.models import AnsibleConfiguration
    AnsibleConfiguration.objects.update_or_create(service=service, key='os',
                                                  defaults={'value': getattr(settings,
                                                                             "OS_VERSION", "jessie")})

    # Create a default Vhost and associate the service name
    default_vhost = Vhost.objects.create(service=service, name="default")
    service_domain = DomainName.objects.create(name=default_vhost.service.network_configuration.name,
                                               status="accepted", vhost=default_vhost)
    default_vhost.main_domain = service_domain
    default_vhost.save()
    secrets_prealocation_vm(vm)


@shared_task(base=XenWithFailure)
def change_vm_power_state(vm_id, on):
    if on != 'on' and on != 'off':
        raise VMAPIInputException("passed wrong parameter power %s" % on)
    return True


@shared_task(base=XenWithFailure)
def clone_vm_api_call(site):
    service = site.test_service
    host_network_configuration = NetworkConfig.get_free_host_config()
    parameters = {}
    parameters["site-id"] = "mwssite-%d" % service.site.id
    parameters["os"] = getattr(settings, 'OS_VERSION', "jessie")

    if host_network_configuration:
        netconf = {}
        if host_network_configuration.IPv4:
            netconf["IPv4"] = host_network_configuration.IPv4
        if host_network_configuration.IPv6:
            netconf["IPv6"] = host_network_configuration.IPv6
        if host_network_configuration.name:
            netconf["hostname"] = host_network_configuration.name
        vm = VirtualMachine.objects.create(service=service, token=uuid.uuid4(),
                                           network_configuration=host_network_configuration, cluster=which_cluster())
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

    vm.name = vm.network_configuration.name
    vm.save()
    from apimws.models import AnsibleConfiguration
    AnsibleConfiguration.objects.update_or_create(service=service, key='os',
                                                  defaults={'value': getattr(settings,
                                                                             "OS_VERSION", "jessie")})
    secrets_prealocation_vm(vm)

    # PHPLibs
    for phplib in site.production_service.php_libs.all():
        phplib.services.add(site.test_service)

    return True


def which_cluster():
    """This function decides which cluster to use when creating a new VM based on how busy each cluster is.
    At present we only have one cluster, so the decision algorithm is pretty obvious. Returns a Cluster object.
    """
    return Cluster.objects.first()
