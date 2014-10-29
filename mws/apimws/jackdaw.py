import subprocess
from celery import shared_task
from django.contrib.auth.models import User
from mwsauth.models import MWSUser


def extract_crsid_and_uuid(text_to_be_parsed):
    text_parsed = text_to_be_parsed.split(',')
    crsid = text_parsed[0].lower().lower()
    if text_parsed[2] == '':
        return crsid  # TODO temporal workaround for jackdaw users without uid
    uid = int(text_parsed[2])
    MWSUser.objects.update_or_create(user_id=crsid, uid=uid) # Assumption that the uid is never going to change in jackdaw
    # TODO if we let users enter to MWS site if they are not in jackdaw change to get_or_create
    return crsid


def deactive_this_user(user_crsid):
    User.objects.filter(username=user_crsid).update(is_active=False)
    # TODO pass to ansible the uid of the user so it can delete this user
    MWSUser.objects.filter(user_id=user_crsid).delete()


def deactivate_users(list_of_users_crsid_from_jackdaw):
    all_users_crsid = User.objects.values_list('username', flat=True)
    deactive_these_users_crsid = filter(lambda user: user not in all_users_crsid, list_of_users_crsid_from_jackdaw)
    map(deactive_this_user, deactive_these_users_crsid)


def reactivate_this_user(user_crsid):
    User.objects.filter(username=user_crsid).update(is_active=True)


def reactivate_users(list_of_users_crsid_from_jackdaw):
    all_users_crsid_deactivated = User.objects.filter(is_active=False).values_list('username', flat=True)
    reactive_these_users_crsid = filter(lambda user: user in all_users_crsid_deactivated,
                                        list_of_users_crsid_from_jackdaw)
    map(reactivate_this_user, reactive_these_users_crsid)


@shared_task()
def jackdaw_api():
    return