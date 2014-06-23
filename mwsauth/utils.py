from django.contrib.auth.models import User


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