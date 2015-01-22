from celery import shared_task


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
    # TODO launch ansible for the two VMs
    pass


@shared_task
def launch_ansible_async(vm):
    # TODO launch ansible task
    if vm.status == 'ansible_queued':
        vm.status = 'ansible'
        vm.save()
        launch_ansible_async.delay(vm)
    else:
        vm.status = 'ready'
        vm.save()
