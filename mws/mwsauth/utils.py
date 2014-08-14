from django.contrib.auth.models import User, Group
from apimws.utils import get_groups_of_a_user_in_lookup


def get_or_create_user_by_crsid(crsid):
    """ Returns the django user corresponding to the crsid parameter.
        :param crsid: the crsid of the retrieved user
    """

    user = User.objects.filter(username=crsid)
    if user.exists():
        user = user.first()
    else:
        user = User(username=crsid)
        user.save()

    return user


def get_or_create_group_by_groupid(groupid):
    """ Returns the django group corresponding to the groupid parameter.
        :param crsid: the groupid of the retrieved group
    """
    groupid = int(groupid)
    group = Group.objects.filter(pk=groupid)
    if group.exists():
        group = group.first()
    else:
        group = Group(pk=groupid)
        group.save()

    return group


def user_in_groups(user, groups):
    """ Check in the lookup webservice if the user is member of any of the groups given
    :param user: the user
    :param groups: the list of groups
    :return: True if the user belongs to any of the groups or False otherwise
    """

    user_group_list = get_groups_of_a_user_in_lookup(user)
    groups = filter(lambda group: group.id in user_group_list, groups)
    if len(groups) > 0:
        return True
    else:
        return False