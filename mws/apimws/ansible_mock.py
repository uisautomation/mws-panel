"""
A module to allow the testing of mws-panel locally - only updates model when performing an ansible function.
"""
import logging
from time import timezone

from celery import Task, shared_task

from sitesmanagement.models import Service, Site, Vhost, Snapshot

LOGGER = logging.getLogger('mws')


def refresh_object(obj):
    """ Reload an object from the database """
    return obj.__class__._default_manager.get(pk=obj.pk)


def launch_ansible(service):
    pass


def launch_ansible_site(site):
    if site.production_service and site.production_service.active:
        launch_ansible(site.production_service)
    if site.test_service and site.test_service.active:
        launch_ansible(site.test_service)


def launch_ansible_by_user(user):
    for site in Site.objects.all():
        if user in site.list_of_all_type_of_active_users() and not site.is_canceled():
            launch_ansible_site(site)  # TODO: Change this to other thing more sensible


class AnsibleTaskWithFailure(Task):
    """If you want to use this task with failure be sure that the first argument is the Service"""
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to execute Ansible.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: \nargs: %s\nkwargs: %s\n\nThe traceback is:\n%s\n",
                     task_id, args, kwargs, einfo)
        if args[0].__class__ == Service:
            service = args[0]
            service.status = 'ready'
            service.save()


@shared_task(base=AnsibleTaskWithFailure, default_retry_delay=120, max_retries=2)
def launch_ansible_async(service, ignore_host_key=False):
    while service.status != 'ready':
        service.status = 'ready'
        service.save()


@shared_task(base=AnsibleTaskWithFailure)
def ansible_change_mysql_root_pwd(service):
    pass


@shared_task(base=AnsibleTaskWithFailure)
def ansible_create_custom_snapshot(service, snapshot):
    snapshot.date = timezone.now()
    snapshot.save()


@shared_task(base=AnsibleTaskWithFailure)
def restore_snapshot(service, snapshot_name):
    pass


@shared_task(base=AnsibleTaskWithFailure)
def delete_snapshot(snapshot_id):
    snapshot = Snapshot.objects.get(id=snapshot_id)
    snapshot.delete()


@shared_task(base=AnsibleTaskWithFailure)
def delete_vhost_ansible(service, vhost_name, vhost_webapp):
    launch_ansible(service)


@shared_task(base=AnsibleTaskWithFailure)
def vhost_enable_apache_owned(vhost_id):
    vhost = Vhost.objects.get(id=vhost_id)
    vhost.apache_owned = True
    vhost.save()
    vhost_disable_apache_owned.apply_async(args=(vhost_id,), countdown=3600)  # Leave an hour to the user


@shared_task(base=AnsibleTaskWithFailure)
def vhost_disable_apache_owned(vhost_id):
    """Revert the ownership of the docroot folder back to site-admin"""
    vhost = Vhost.objects.get(id=vhost_id)
    vhost.apache_owned = False
    vhost.save()
