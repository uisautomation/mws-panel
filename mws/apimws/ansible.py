from celery import shared_task
import subprocess


class UnexpectedVMStatus(Exception):
    pass


def launch_ansible(vm):
    # TODO if ansible is already running, then mark a flag that to reexecute ansible once finished
    if vm.status == 'ready':
        vm.status = 'ansible'
        vm.save()
        launch_ansible_async.delay(vm)
    elif vm.status == 'ansible':
        vm.status = 'ansible_queued'
        vm.save()
        launch_ansible_async.delay(vm)
    elif vm.status == 'ansible_queued':
        return
    else:
        raise UnexpectedVMStatus()


def launch_ansible_site(site):
    if site.primary_vm is not None:
        launch_ansible(site.primary_vm)
    if site.secondary_vm is not None:
        launch_ansible(site.secondary_vm)


@shared_task
def launch_ansible_async(vm):
    ansible_response = subprocess.check_output(["userv", "mws-admin", "mws_ansible"])
    if vm.status == 'ansible_queued':
        vm.status = 'ansible'
        vm.save()
        launch_ansible_async.delay(vm)
    else:
        vm.status = 'ready'
        vm.save()
