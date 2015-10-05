from __future__ import absolute_import
import logging
from celery import shared_task, Task
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.urlresolvers import reverse
from sitesmanagement.models import EmailConfirmation
import uuid


LOGGER = logging.getLogger('mws')


class EmailTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to send an email.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=EmailTaskWithFailure, default_retry_delay=5*60, max_retries=12)  # Retry each 5 minutes for 1 hours
def ip_register_api_request(domain_name):
    EmailMessage(
        subject="New request of a Domain Name for the MWS",
        body="Domain Name requested: " + domain_name.name + "\n"
             "IPv4: " + domain_name.vhost.service.network_configuration.IPv4 + "\n"
             "IPv6: " + domain_name.vhost.service.network_configuration.IPv6 + "\n"
             "Please, when ready click here: %s%s" % (settings.MAIN_DOMAIN, reverse('apimws.views.confirm_dns',
                                                                                    kwargs={'dn_id': domain_name.id})),
        from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
        to=['amc203@cam.ac.uk'],
        headers={'Return-Path': 'mws3-support@cam.ac.uk'}
    ).send()


@shared_task(base=EmailTaskWithFailure, default_retry_delay=5*60, max_retries=12)  # Retry each 5 minutes for 1 hours
def ip_register_api_sshfp(sshfprecord):
    EmailMessage(
        subject="Managed Web Service: Please update the following DNS entries",
        body=sshfprecord,
        from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
        to=['amc203@cam.ac.uk'],
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
