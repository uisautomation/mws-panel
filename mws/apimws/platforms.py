from __future__ import absolute_import
import uuid
from celery import shared_task, Task
import json
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
import os
from django.conf import settings
import requests
from sitesmanagement.models import VirtualMachine


class PlatformsAPINotWorkingException(Exception):
    pass


class PlatformsAPIInputException(Exception):
    pass


def on_vm_api_failure(request, response):
        subject = "MWS3: Platform's VM API ERROR"
        message = "An error was returned when sending a request to Platform's VM API.\n\n The request was: \n %s \n\n " \
                  "The answer was: \n %s" % (request, response)
        from_email = settings.EMAIL_MWS3_SUPPORT
        recipient_list = (settings.EMAIL_MWS3_SUPPORT, )
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return False # TODO raise exception? and log it in the logger


class TaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        subject = "MWS3: Platform's VM API ERROR"
        message = "An error happened when trying to communicate with Platform's VM API.\n The task id is " \
                  "%s. \n\n The parameters passed to the task were: %s \n\n " \
                  "The traceback is: \n %s" % (task_id, args, einfo)
        from_email = settings.EMAIL_MWS3_SUPPORT
        recipient_list = (settings.EMAIL_MWS3_SUPPORT, )
        send_mail(subject, message, from_email, recipient_list, fail_silently=False) # TODO raise exception? and log it in the logger


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def new_site_primary_vm(vm):
    return install_vm(vm)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def install_vm(vm):
    return True


def get_vm_power_state(vm):
    return vm.vm_status_demo.get_status_display


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def change_vm_power_state(vm, on):
    if on != 'on' and on != 'off':
        raise PlatformsAPIInputException("passed wrong parameter power %s" % on)

    vm.vm_status_demo.status = on
    vm.save()
    return True


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def reset_vm(vm):
    return True


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def destroy_vm(vm):
    return True


def clone_vm(site, primary_vm):
    delete_vm = None

    if primary_vm:
        original_vm = site.primary_vm
        if site.secondary_vm:
            delete_vm = site.secondary_vm
    else:
        original_vm = site.secondary_vm
        if site.primary_vm:
            delete_vm = site.primary_vm

    if delete_vm:
        delete_vm.site = None
        delete_vm.save()

    destination_vm = VirtualMachine.objects.create(primary=(not primary_vm), status='requested', token=uuid.uuid4(),
                                                   site=site)
    clone_vm_api_call(original_vm, destination_vm, delete_vm)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def clone_vm_api_call(orignal_vm, destination_vm, delete_vm):
    if delete_vm:
        delete_vm.delete()

    destination_vm.name = str(uuid.uuid4())
    destination_vm.status = 'requested'
    destination_vm.save()

    # Copy Unix Groups
    for unix_group in orignal_vm.unix_groups.all():
        copy_users = unix_group.users.all()
        unix_group.pk = None
        unix_group.vm = destination_vm
        unix_group.save()
        unix_group.users = copy_users

    # Copy Ansible Configuration
    for ansible_conf in orignal_vm.ansible_configuration.all():
        ansible_conf.pk = None
        ansible_conf.vm = destination_vm
        ansible_conf.save()

    # Copy vhosts
    # TODO copy Domain Names
    for vhost in orignal_vm.vhosts.all():
        vhost.pk = None
        vhost.vm = destination_vm
        vhost.save()

    return True
