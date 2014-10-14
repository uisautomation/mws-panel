from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from ucamlookup import user_in_groups
from ucamlookup.models import LookupGroup
from sitesmanagement.models import Site


def get_or_create_user_by_crsid(crsid):
    """ Returns the django user corresponding to the crsid parameter.
        :param crsid: the crsid of the retrieved user
    """

    user = User.objects.filter(username=crsid)
    if user.exists():
        user = user.first()
    else:
        user = User.objects.create_user(username=crsid)

    return user


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
    site = get_object_or_404(Site, pk=site_id)

    # If the user is not in the user auth list of the site and neither belongs to a group in the group auth list or
    # the site is suspended or canceled return None
    try:
        if (not site in user.sites.all() and not user_in_groups(user, site.groups.all())) or site.is_admin_suspended()\
                or site.is_canceled() or site.is_disabled():
            return None
    except Exception:
        return None

    return site
