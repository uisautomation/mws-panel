from datetime import date
import logging
from celery import shared_task, Task
from django.core.mail import EmailMessage
from django.utils import timezone
from sitesmanagement.models import Billing


LOGGER = logging.getLogger('mws')


class FinanceTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to send an email to Finance.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=FinanceTaskWithFailure)
def send_reminder_renewal():
    today = timezone.now().date()
    renewal_sites_billing = Billing.objects.filter(site__start_date__month=today.month-1 if today.month != 1 else 12,
                                                   site__start_date__lt=date(today.year, 1, 1), site__deleted=False)
    for billing in renewal_sites_billing:
        EmailMessage(
            subject="University of Cambridge Managed Web Service: Your MWS3 site is due to renew next month",
            body="Dear MWS3 user,\n\nYour MWS3 site '%s' is due to renew next month on %s. "
                 "Please make sure the purchase order that you submitted as payment method is up to date and can be"
                 "used as a valid payment method this year as well. If you want to amend your purchase order, you can"
                 "upload a new one using the web control panel.\n\nIf the purchase order cannot be processed your site"
                 "may be deleted automatically." % (billing.site.name, billing.site.start_date),
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[billing.site.email],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'}
        ).send()

    renewal_sites_billing = Billing.objects.filter(site__start_date__month=today.month,
                                                   site__start_date__lt=date(today.year, 1, 1), site__deleted=False)
    for billing in renewal_sites_billing:
        EmailMessage(
            subject="University of Cambridge Managed Web Service: Your MWS3 site is due to renew this month",
            body="Dear MWS3 user,\n\nYour MWS3 site '%s' is due to renew next month on %s. "
                 "Please make sure the purchase order that you submitted as payment method is up to date and can be"
                 "used as a valid payment method this year as well. If you want to amend your purchase order, you can"
                 "upload a new one using the web control panel.\n\nIf the purchase order cannot be processed your site"
                 "may be deleted automatically." % (billing.site.name, billing.site.start_date),
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[billing.site.email],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'}
        ).send()
