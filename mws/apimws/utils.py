from __future__ import absolute_import
import subprocess
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apimws.platforms import TaskWithFailure
from mwsauth.models import MWSUser
from sitesmanagement.models import EmailConfirmation
import uuid


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def ip_register_api_request(domain_name):

    subject = "New request of a Domain Name for the MWS"
    message = "Domain Name requested: " + domain_name.name + "\n" \
              "IPv4: " + domain_name.vhost.vm.site.network_configuration.IPv4 + "\n" \
              "IPv6: " + domain_name.vhost.vm.site.network_configuration.IPv6 + "\n" \
              "Please, when ready click here: %s/api/confirm_dns/" % settings.MAIN_DOMAIN \
              + str(domain_name.id)
    from_email = "mws3-support@cam.ac.uk"
    recipient_list = ('amc203@cam.ac.uk', )
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288) # Retry each 5 minutes for 24 hours
def email_confirmation(site):
    previous = EmailConfirmation.objects.filter(site=site)
    if previous:
        previous.first().delete()
    email_conf = EmailConfirmation.objects.create(email=site.email, token=uuid.uuid4(), status="pending", site=site)
    subject = "University of Cambridge Managed Web Service: Please confirm your email address"
    message = "Please, confirm your email address by clicking in the following link: " \
              "%s/confirm_email/%d/%s/" % (settings.MAIN_DOMAIN, email_conf.id, email_conf.token)
    from_email = "mws3-support@cam.ac.uk"
    recipient_list = (site.email, )
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


def extract_crsid_and_uuid(text_to_be_parsed):
    text_parsed = text_to_be_parsed.split(',')
    crsid = text_parsed[0].lower().lower()
    uid = int(text_parsed[2])

    try:
        MWSUser.objects.get(user_id=crsid)
    except MWSUser.DoesNotExist:
        MWSUser.objects.create(user_id=crsid, uid=uid)

    return (crsid, uid)


def jackdaw_api():
    jackdaw_response = subprocess.check_output(["ssh", "root@boarstall", "ssh", "mwsv3@jackdaw.csi.cam.ac.uk", "test",
                                                "get_people"])
    jackdaw_response_parsed = jackdaw_response.splitlines()
    if jackdaw_response_parsed.pop(0) != "Databae:jdawtest":
        return False # TODO Raise a custom exception
    jackdaw_response_parsed = map(extract_crsid_and_uuid, jackdaw_response_parsed)
    return jackdaw_response_parsed  # TODO remove those users that are no longer in Jackdaw


def launch_ansible(site):
    # TODO if ansible is already running, then mark a flag that to reexecute ansible once finished
    primary_vm = site.primary_vm
    primary_vm.status = 'ansible'
    primary_vm.save()

    # TODO Remove the following code when the Ansible API is ready and substitute by an API call
    primary_vm.status = 'ready'
    primary_vm.save()
