from django.contrib.auth.models import User, Group


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