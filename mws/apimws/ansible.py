from celery import shared_task
import subprocess


class UnexpectedVMStatus(Exception):
    pass


def refresh_object(obj):
    """ Reload an object from the database """
    return obj.__class__._default_manager.get(pk=obj.pk)


def launch_ansible(vm):
    if vm.status == 'ready':
        vm.status = 'ansible'
        vm.save()
        launch_ansible_async.delay(vm)
    elif vm.status == 'ansible':
        vm.status = 'ansible_queued'
        vm.save()
    elif vm.status == 'ansible_queued':
        return
    else:
        raise UnexpectedVMStatus()  # TODO pass the vm object?


def launch_ansible_site(site):
    if site.primary_vm is not None:
        launch_ansible(site.primary_vm)
    if site.secondary_vm is not None:
        launch_ansible(site.secondary_vm)


@shared_task
def launch_ansible_async(vm):
    while vm.status != 'ready':
        ansible_response = subprocess.check_output(["userv", "mws-admin", "mws_ansible"])
        vm = refresh_object(vm)
        if vm.status == 'ansible_queued':
            vm.status = 'ansible'
            vm.save()
        else:
            vm.status = 'ready'
            vm.save()
