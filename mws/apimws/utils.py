from __future__ import absolute_import
import json
import logging
import uuid
from celery import shared_task, Task
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.urlresolvers import reverse
from apimws.ipreg import get_nameinfo
from sitesmanagement.models import EmailConfirmation


LOGGER = logging.getLogger('mws')


class EmailTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to send an email.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=EmailTaskWithFailure, default_retry_delay=15*60, max_retries=12)  # Retry each 15 minutes for 12 times
def ip_register_api_request(domain_name):
    nameinfo = get_nameinfo(domain_name)
    if nameinfo['emails']:
        emails = nameinfo['emails']
    elif nameinfo['crsids']:
        emails = map(lambda crsid: crsid+"@cam.ac.uk", nameinfo['crsids'])
    else:
        LOGGER.error("Domain name %s do not have emails or crsids associated in IPREG database.\n"
                     "Received: %s", domain_name.name, json.dumps(nameinfo))
        raise Exception("Domain name %s do not have emails or crsids associated in IPREG database" % domain_name.name)
    EmailMessage(
        subject="Domain name authorisation request for %s" % nameinfo['domain'],
        body="You are receiving this email because you are the administrator of the domain %s.\n\n"
             "The user %s (https://www.lookup.cam.ac.uk/person/crsid/%s) has requested permission to use the domain "
             "name %s for a UIS Managed Web Server website (see http://www.ucs.cam.ac.uk/managed-web-service/).\n\n"
             "To authorise or reject this request please visit the following URL %s%s. If we don't hear from you "
             "in three working days the request will be automatically %s.\n\n%s"
             "Questions about this message can be referred to mws3-support@uis.cam.ac.uk."
             % (nameinfo['domain'], domain_name.requested_by.last_name, domain_name.requested_by.username,
                domain_name.name, settings.MAIN_DOMAIN,
                reverse('apimws.views.confirm_dns', kwargs={'dn_id': domain_name.id, 'token': domain_name.token}),
                "rejected" if nameinfo['exists'] else "accepted",
                "We have detected that this domain name already exists in the DNS. In order to accept the request "
                "you will have to change the domain name to a CNAME or delete it.\n\n"
                if nameinfo['exists'] and "C" not in nameinfo['exists'] else ""),
        from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
        to=emails,
        headers={'Return-Path': 'mws3-support@cam.ac.uk'}
    ).send()


def email_confirmation(site):
    EmailConfirmation.objects.filter(site=site).delete()  # Delete previous one
    EmailConfirmation.objects.create(email=site.email, token=uuid.uuid4(), status="pending", site=site)
    send_email_confirmation.delay(site)


@shared_task(base=EmailTaskWithFailure, default_retry_delay=5*60, max_retries=12)  # Retry each 5 minutes for 1 hours
def send_email_confirmation(site):
    email_conf = EmailConfirmation.objects.filter(site=site)
    if email_conf:
        email_conf = email_conf.first()
        EmailMessage(
            subject="University of Cambridge Managed Web Service: Please confirm your email address",
            body="Please, confirm your email address by clicking in the following link: %s%s"
                 % (settings.MAIN_DOMAIN, reverse('apimws.views.confirm_email',
                                                  kwargs={'ec_id': email_conf.id, 'token': email_conf.token})),
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[site.email],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'}
        ).send()


@shared_task(base=EmailTaskWithFailure, default_retry_delay=5*60, max_retries=12)  # Retry each 5 minutes for 1 hours
def finished_installation_email_confirmation(site):
    EmailMessage(
        subject="University of Cambridge Managed Web Service: Your MWS3 site is available",
        body="Your MWS3 site is now available. You can access to the web panel of your MWS3 site by clicking the "
             "following link: %s%s" % (settings.MAIN_DOMAIN, site.get_absolute_url()),
        from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
        to=[site.email],
        headers={'Return-Path': 'mws3-support@cam.ac.uk'}
    ).send()
