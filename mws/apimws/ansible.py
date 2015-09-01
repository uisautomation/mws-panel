import logging
import subprocess
from celery import shared_task, Task
from django.conf import settings
from sitesmanagement.models import Site


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
    elif service.status == 'installing':
        return
    else:
        raise UnexpectedVMStatus()  # TODO pass the vm object?


def launch_ansible_by_user(user):
    for site in Site.objects.all():
        if user in site.list_of_all_type_of_active_users() and not site.is_canceled():
            launch_ansible_site(site)  # TODO: Change this to other thing more sensible


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
            for vm in service.virtual_machines.all():
                subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name])
        except subprocess.CalledProcessError as e:
            LOGGER.error("An error happened when trying to execute Ansible.\nThe error is %s.\n\n", str(e))
            if not getattr(settings, 'DEMO', False):
                raise launch_ansible_async.retry(exc=e)
        service = refresh_object(service)
        if service.status == 'ansible_queued':
            service.status = 'ansible'
            service.save()
        else:
            service.status = 'ready'
            service.save()


@shared_task(base=TaskWithFailure, default_retry_delay=60, max_retries=5)  # Retry each minute for 5 minutes
def ansible_change_mysql_root_pwd(service):
    try:
        for vm in service.virtual_machines.all():
            subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name,
                                     "--tags", "change_mysql_password", "-e", "change_mysql_root_pwd=true"])
    except subprocess.CalledProcessError as e:
        if not getattr(settings, 'DEMO', False):
            raise launch_ansible_async.retry(exc=e)


@shared_task()
def ansible_create_custom_snapshot(service, snapshot):
    try:
        for vm in service.virtual_machines.all():
            subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name,
                                     "--tags", "create_custom_snapshot", "-e", 'snapshot_name="%s"' % snapshot.name])
    except Exception as e:
        snapshot.delete()
        raise e
