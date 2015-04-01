import logging
import subprocess
from celery import shared_task, Task


LOGGER = logging.getLogger('mws')


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
    if site.production_service and site.production_service.active:
        launch_ansible(site.production_service)
    if site.test_service and site.test_service.active:
        launch_ansible(site.test_service)


class TaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if type(exc) is subprocess.CalledProcessError:
            LOGGER.error("An error happened when trying to execute Ansible.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n\n"
                         "The output from the command was: %s\n", task_id, args, einfo, exc.output)
        else:
            LOGGER.error("An error happened when trying to execute Ansible.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=TaskWithFailure, default_retry_delay=60, max_retries=5)  # Retry each minute for 5 minutes
def launch_ansible_async(service):
    while service.status != 'ready':
        try:
            subprocess.check_output(["userv", "mws-admin", "mws_ansible"])
        except subprocess.CalledProcessError as e:
            raise launch_ansible_async.retry(exc=e)
        service = refresh_object(service)
        if service.status == 'ansible_queued':
            service.status = 'ansible'
            service.save()
        else:
            service.status = 'ready'
            service.save()
