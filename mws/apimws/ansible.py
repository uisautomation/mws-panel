from celery import shared_task
import subprocess
from sitesmanagement.models import Service


class UnexpectedVMStatus(Exception):
    pass


def refresh_object(obj):
    """ Reload an object from the database """
    return obj.__class__._default_manager.get(pk=obj.pk)


def launch_ansible(service):
    if service.status == 'ready':
        service.status = 'ansible'
        service.save()
        launch_ansible_async.delay(service)
    elif service.status == 'ansible':
        service.status = 'ansible_queued'
        service.save()
    elif service.status == 'ansible_queued':
        return
    else:
        raise UnexpectedVMStatus()  # TODO pass the vm object?


def launch_ansible_site(site):
    if site.production_service is not None:
        launch_ansible(site.production_service)
    if site.test_service is not None:
        launch_ansible(site.test_service)


@shared_task
def launch_ansible_async(service):
    while service.status != 'ready':
        ansible_response = subprocess.check_output(["userv", "mws-admin", "mws_ansible"])
        service = refresh_object(service)
        if service.status == 'ansible_queued':
            service.status = 'ansible'
            service.save()
        else:
            service.status = 'ready'
            service.save()
