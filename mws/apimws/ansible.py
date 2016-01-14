import logging
import subprocess
from celery import shared_task, Task
from django.utils import timezone
from sitesmanagement.models import Site, Snapshot, Service

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
    elif service.status in ['installing', 'postinstall']:
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


class AnsibleTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if type(exc) is subprocess.CalledProcessError:
            LOGGER.error("An error happened when trying to execute Ansible.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n\n"
                         "The output from the command was: %s\n", task_id, args, einfo, exc.output)
        else:
            LOGGER.error("An error happened when trying to execute Ansible.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)
        service = kwargs['service']
        service.status = 'ready'
        service.save()


@shared_task(base=AnsibleTaskWithFailure, default_retry_delay=120, max_retries=2)
def launch_ansible_async(service):
    while service.status != 'ready':
        try:
            for vm in service.virtual_machines.all():
                subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name],
                                        stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise launch_ansible_async.retry(exc=e)
        service = refresh_object(service)
        if service.status == 'ansible_queued':
            service.status = 'ansible'
            service.save()
        else:
            service.status = 'ready'
            service.save()


@shared_task(base=AnsibleTaskWithFailure)
def ansible_change_mysql_root_pwd(service):
    for vm in service.virtual_machines.all():
        subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name,
                                 "--tags", "change_mysql_root_pwd", "-e", "change_mysql_root_pwd=true"],
                                stderr=subprocess.STDOUT)


@shared_task(base=AnsibleTaskWithFailure)
def ansible_create_custom_snapshot(service, snapshot):
    try:
        for vm in service.virtual_machines.all():
            subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name,
                                     "--tags", "create_custom_snapshot", "-e",
                                     'create_snapshot_name="%s"' % snapshot.name], stderr=subprocess.STDOUT)
        snapshot.date = timezone.now()
        snapshot.save()
    except Exception as e:
        snapshot.delete()
        raise e


@shared_task(base=AnsibleTaskWithFailure)
def restore_snapshot(service, snapshot_name):
    for vm in service.virtual_machines.all():
        subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name,
                                 "--tags", "restore_snapshot", "-e", 'restore_snapshot_name="%s"' % snapshot_name],
                                stderr=subprocess.STDOUT)


@shared_task(base=AnsibleTaskWithFailure)
def delete_snapshot(snapshot_id):
    snapshot = Snapshot.objects.get(id=snapshot_id)
    for vm in snapshot.service.virtual_machines.all():
        subprocess.check_output(["userv", "mws-admin", "mws_ansible_host", vm.network_configuration.name,
                                 "--tags", "delete_snapshot", "-e", 'delete_snapshot_name="%s"' % snapshot.name],
                                stderr=subprocess.STDOUT)
    snapshot.delete()


@shared_task(base=AnsibleTaskWithFailure)
def delete_vhost_ansible(vhost_name, service_id):
    service = Service.objects.get(id=service_id)
    for vm in service.virtual_machines.all():
        subprocess.check_output(["userv", "mws-admin", "mws_delete_vhost", vm.network_configuration.name,
                                 "--tags", "delete_vhost", "-e", 'delete_vhost_name="%s"' % vhost_name],
                                stderr=subprocess.STDOUT)
    launch_ansible(service)
    return
