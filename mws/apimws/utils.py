from __future__ import absolute_import
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.core.urlresolvers import reverse
from apimws.platforms import TaskWithFailure
from sitesmanagement.models import EmailConfirmation
import uuid


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def ip_register_api_request(domain_name):

    subject = "New request of a Domain Name for the MWS"
    message = "Domain Name requested: " + domain_name.name + "\n" \
              "IPv4: " + domain_name.vhost.service.network_configuration.IPv4 + "\n" \
              "IPv6: " + domain_name.vhost.service.network_configuration.IPv6 + "\n" \
              "Please, when ready click here: %s/api/confirm_dns/" % settings.MAIN_DOMAIN \
              + str(domain_name.id)
    from_email = "mws3-support@cam.ac.uk"
    recipient_list = ('amc203@cam.ac.uk', )
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
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
    headers = {'Reply-To': from_email}
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


@shared_task(base=TaskWithFailure, default_retry_delay=5*60, max_retries=288)  # Retry each 5 minutes for 24 hours
def resend_email_confirmation(site):
    email_conf = EmailConfirmation.objects.get(site=site)
    subject = "University of Cambridge Managed Web Service: Please confirm your email address"
    message = "Please, confirm your email address by clicking in the following link: " \
              "%s/confirm_email/%d/%s/" % (settings.MAIN_DOMAIN, email_conf.id, email_conf.token)
    from_email = "mws3-support@cam.ac.uk"
    recipient_list = (site.email, )
    headers = {'Reply-To': from_email}
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)


@shared_task(base=TaskWithFailure, default_retry_delay=60, max_retries=5)
def finished_installation_email_confirmation(site):
    subject = "University of Cambridge Managed Web Service: Your MWS3 site is available"
    message = "Your MWS3 site is now available. You can access to the web panel of your MWS3 site by clicking the " \
              "following link: %s%s" % (settings.MAIN_DOMAIN,
                                          reverse('sitesmanagement.views.show', kwargs={'site_id': site.id}))
    from_email = "mws3-support@cam.ac.uk"
    recipient_list = (site.email, )
    headers = {'Reply-To': from_email}
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
