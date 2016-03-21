import logging
from celery import shared_task, Task
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ucamlookup import user_in_groups, get_or_create_user_by_crsid, GroupMethods, conn
from ucamlookup.models import LookupGroup


LOGGER = logging.getLogger('mws')


def get_or_create_group_by_groupid(groupid):
    """ Returns the django group corresponding to the groupid parameter.
        :param crsid: the groupid of the retrieved group
    """
    groupidstr = str(groupid)
    group = LookupGroup.objects.filter(lookup_id=groupidstr)
    if group.exists():
        group = group.first()
    else:
        group = LookupGroup.objects.create(lookup_id=groupidstr)

    return group


def privileges_check(site_id, user):
    from sitesmanagement.models import Site
    site = get_object_or_404(Site, pk=site_id)

    # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
    # the site is disabled or canceled return None
    try:
        if not user.is_superuser and (site not in user.sites.all() and not user_in_groups(user, site.groups.all())) or \
            (site.is_canceled() or site.is_disabled()):
            return None
    except Exception:
        return None
    return site


# TODO move this function to django-ucam-lookup
def get_users_of_a_group(group):
    """ Returns the list of users of a LookupGroup
    :param group: The LookupGroup
    :return: the list of Users
    """

    return map(lambda user: get_or_create_user_by_crsid(user.identifier.value),
               GroupMethods(conn).getMembers(groupid=group.lookup_id))


class ScheduledTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to execute an scheduled task.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=ScheduledTaskWithFailure)
def remove_supporter(site_id, crsid):
    from sitesmanagement.models import Site
    site = Site.objects.get(id=site_id)
    user = User.objects.get(username=crsid)
    site.supporters.remove(user)
    from apimws.ansible import launch_ansible_site
    launch_ansible_site(site)
