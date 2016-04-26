import logging
import subprocess
from celery import shared_task, Task
from django.contrib.auth.models import User
from mwsauth.models import MWSUser


LOGGER = logging.getLogger('mws')


def extract_crsid_and_uuid(text_to_be_parsed):
    text_parsed = text_to_be_parsed.split(',')
    crsid = text_parsed[0].lower().lower()
    if text_parsed[2] == '':
        LOGGER.warning("The user " + str(crsid) + " does not have UID in the Jackdaw feed")
        return (crsid, None)  # TODO temporal workaround for jackdaw users without uid
    uid = int(text_parsed[2])
    return (crsid, uid)


def deactive_this_user(user_crsid):
    # TODO pass to ansible the uid of the user so it can delete this user?
    updated = User.objects.filter(username=user_crsid).update(is_active=False)
    # if updated is 0 the user had never used the mws3 service
    # if updated is 1 then the user used the service and has been deactivated
    # if updated is more than 2 an exception should be raise, it shouldn't be the case
    MWSUser.objects.filter(user_id=user_crsid).delete()


def deactivate_users(jackdaw_users_crsids, list_of_mws_users):
    map(deactive_this_user, set(list_of_mws_users) - set(jackdaw_users_crsids))


def reactivate_or_create_mws_user(user_crsid, jackdaw_users):
    updated = User.objects.filter(username=user_crsid).update(is_active=True)
    # if updated is 0 the user has not yet used the mws3 service
    # if updated is 1 then the user has used the service, was deactivated and now they has been reactivated
    # if updated is more than 2 an exception should be raise, it shouldn't be the case
    # Assumption that the uid is never going to change in jackdaw
    if jackdaw_users[user_crsid] < 1000:
        MWSUser.objects.update_or_create(user_id=user_crsid, uid=66000+jackdaw_users[user_crsid])
    else:
        MWSUser.objects.update_or_create(user_id=user_crsid, uid=jackdaw_users[user_crsid])
    # TODO if we let users enter to MWS server if they are not in jackdaw change to get_or_create


def reactivate_users(jackdaw_users_crsids, list_of_mws_users, jackdaw_users):
    map(lambda x: reactivate_or_create_mws_user(x, jackdaw_users), set(jackdaw_users_crsids) - set(list_of_mws_users))


class SSHTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if type(exc) is subprocess.CalledProcessError:
            LOGGER.error("An error happened when trying to execute SSH.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n\n"
                         "The output from the command was: %s\n", task_id, args, einfo, exc.output)
        else:
            LOGGER.error("An error happened when trying to execute SSH.\nThe task id is %s.\n\n"
                         "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=SSHTaskWithFailure)
def jackdaw_api():
    jackdaw_response = subprocess.check_output(["ssh", "mwsv3@jackdaw.csi.cam.ac.uk", "p", "get_people"],
                                               stderr=subprocess.STDOUT)
    jackdaw_response_parsed = jackdaw_response.splitlines()  # TODO Raise a custom exception if response is empty
    jackdaw_users = map(extract_crsid_and_uuid, jackdaw_response_parsed)
    # Only take as valid users, users with uid
    jackdaw_valid_users = filter(lambda user: user[1] is not None, jackdaw_users)
    jackdaw_users_crsids = dict(jackdaw_valid_users).keys()
    list_of_mws_users = MWSUser.objects.values_list('user', flat=True)
    # Deactivate those users that are no longer in Jackdaw
    deactivate_users(jackdaw_users_crsids, list_of_mws_users)
    # Reactivate those users that are in Jackdaw but not in MWS3 db
    reactivate_users(jackdaw_users_crsids, list_of_mws_users, dict(jackdaw_users))
