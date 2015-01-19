import logging
import subprocess
from celery import shared_task
from django.contrib.auth.models import User
from mwsauth.models import MWSUser

logger = logging.getLogger('mws')


def extract_crsid_and_uuid(text_to_be_parsed):
    text_parsed = text_to_be_parsed.split(',')
    crsid = text_parsed[0].lower().lower()
    if text_parsed[2] == '':
        logger.warning("The user " + str(crsid) + " does not have UID in the Jackdaw feed")
        return (crsid, None) # TODO temporal workaround for jackdaw users without uid
    uid = int(text_parsed[2])
    return (crsid, uid)


def deactive_this_user(user_crsid):
    # TODO pass to ansible the uid of the user so it can delete this user
    updated = User.objects.filter(username=user_crsid).update(is_active=False)
    # if updated is 0 the user had never used the mws3 service
    # if updated is 1 then the user used the service and has been deactivated
    # if updated is more than 2 an exception should be raise, it shouldn't be the case
    MWSUser.objects.filter(user_id=user_crsid).delete()


def deactivate_users(jackdaw_users_crsids, list_of_mws_users):
    map(deactive_this_user, set(list_of_mws_users) - set(jackdaw_users_crsids))


def reactivate_this_user(user_crsid, jackdaw_users):
    updated = User.objects.filter(username=user_crsid).update(is_active=True)
    # if updated is 0 the user has not yet used the mws3 service
    # if updated is 1 then the user has used the service, was deactivated and now they has been reactivated
    # if updated is more than 2 an exception should be raise, it shouldn't be the case
    # Assumption that the uid is never going to change in jackdaw
    MWSUser.objects.update_or_create(user_id=user_crsid, uid=jackdaw_users[user_crsid])
    # TODO if we let users enter to MWS site if they are not in jackdaw change to get_or_create


def reactivate_users(jackdaw_users_crsids, list_of_mws_users, jackdaw_users):
    map(lambda x: reactivate_this_user(x, jackdaw_users), set(jackdaw_users_crsids) - set(list_of_mws_users))


@shared_task()
def jackdaw_api():
    jackdaw_response = subprocess.check_output(["ssh", "mwsv3@jackdaw.csi.cam.ac.uk", "p", "get_people"])
    jackdaw_response_parsed = jackdaw_response.splitlines()  # TODO Raise a custom exception if response is empty
    jackdaw_users = dict(map(extract_crsid_and_uuid, jackdaw_response_parsed))
    jackdaw_users_crsids = jackdaw_users.keys()
    list_of_mws_users = MWSUser.objects.values_list('user', flat=True)
    # Deactivate those users that are no longer in Jackdaw
    deactivate_users(jackdaw_users_crsids, list_of_mws_users)
    # Reactivate those users that are in Jackdaw but not in MWS3 db
    reactivate_users(jackdaw_users_crsids, list_of_mws_users, jackdaw_users)
