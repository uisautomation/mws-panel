import json
import logging
import subprocess
from datetime import date, timedelta
from celery import shared_task, Task
from django.core.mail import EmailMessage
from django.utils import timezone
from apimws.jackdaw import SSHTaskWithFailure
from sitesmanagement.models import Billing, Site, VirtualMachine

LOGGER = logging.getLogger('mws')


class FinanceTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to send an email to Finance.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


@shared_task(base=FinanceTaskWithFailure)
def send_reminder_renewal():
    today = timezone.now().date()
    # Billings of sites that haven't been canceled (end_date is null), that hasn't expressed to want to cancel
    # their subscription, and that started in the previous month of the current one of a previous year
    renewal_sites_billing = Billing.objects.filter(site__start_date__month=today.month-1 if today.month != 1 else 12,
                                                   site__start_date__lt=date(today.year, 1, 1),
                                                   site__end_date__isnull=True,
                                                   site__subscription=True)
    for billing in renewal_sites_billing:
        EmailMessage(
            subject="The annual charge for your managed web site is due next month",
            body="The annual charge for your managed web site '%s' is due next month on %s. Unless you tell us otherwise "
                 "we will automatically issue an invoice for this at the end of next month based on information from the "
                 "most recent purchase order you have given us. Please use the web control panel (under 'billing settings') "
                 "to check that this information is still current. If you want to amend your purchase order you can upload "
                 "a new one. Your site may be cancelled if we can't successfully invoice for it.\n\n"
                 "If you no longer want you site then please either cancel it now (under 'edit the MWS profile'), or mark "
                 "it 'Not for renewal' in which case it will be automatically cancelled on '%s'." 
                 % (billing.site.name, billing.site.start_date, billing.site.start_date),
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[billing.site.email],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'}
        ).send()

    renewal_sites_billing = Billing.objects.filter(site__start_date__month=today.month, site__subscription=True,
                                                   site__start_date__lt=date(today.year, 1, 1),
                                                   site__end_date__isnull=True)
    for billing in renewal_sites_billing:
        EmailMessage(
            subject="REMINDER: the annual charge for your managed web site is due this month",
            body="The annual charge for your managed web site '%s' is due this month on %s. Unless you tell us otherwise "
                 "we will automatically issue an invoice for this at the end of this month based on information from the "
                 "most recent purchase order you have given us. If you haven't already, please use the web control panel "
                 "(under 'billing settings') to check that this information is still current. If you want to amend your "
                 "purchase order you can upload a new one. Your site may be cancelled if we can't successfully invoice for it.\n\n"
                 "If you no longer want you site then please either cancel it now (under 'edit the MWS profile'), or mark "
                 "it 'Not for renewal' in which case it will be automatically cancelled on '%s'." 
                 % (billing.site.name, billing.site.start_date, billing.site.start_date),
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[billing.site.email],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'}
        ).send()


@shared_task(base=FinanceTaskWithFailure)
def check_subscription():
    today = timezone.now().date()
    # Check which sites still do not have a billing associated, warn or cancel them based on
    # how many days ago they were created
    sites = Site.objects.filter(billing__isnull=True, end_date__isnull=True)
    for site in sites:
        if (today - site.start_date) >= timedelta(days=31):
            # Cancel site
            EmailMessage(
                subject="Your managed web site has been cancelled",
                body="Your managed web site '%s' has been cancelled because we haven't received payment information for it." % site.name,
                from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
                to=[site.email],
                headers={'Return-Path': 'mws3-support@cam.ac.uk'}
            ).send()
            site.cancel()
        elif ((today - site.start_date) == timedelta(days=15)) or ((today - site.start_date) >= timedelta(days=24)):
            # Warning 15 days before and each day in the last week before deadline
            EmailMessage(
                subject="Remember to upload a purchase order for your managed web site",
                body="Please upload a purchase order using the control web panel to pay for your managed "
                     "web site '%s'.\n\nIf you don't upload a valid purchase order before %s your site '%s' will be "
                     "automatically cancelled." % (site.name, site.start_date+timedelta(days=30), site.name),
                from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
                to=[site.email],
                headers={'Return-Path': 'mws3-support@cam.ac.uk'}
            ).send()
    # Cancel sites with subscription finished
    if today.month == 2 and today.day == 29:
        last_year = date(today.year-1, 3, 1)
    else:
        last_year = date(today.year-1, today.month, today.day)
    sites = Site.objects.filter(end_date__isnull=True, start_date__lt=last_year, subscription=False)
    for site in sites:
        # Cancel site
        EmailMessage(
            subject="Your managed web site has been cancelled",
            body="Your managed web site '%s' has been cancelled per your requested." % site.name,
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[site.email],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'}
        ).send()
        site.cancel()


@shared_task
def check_backups():
    try:
        result = subprocess.check_output(["userv", "mws-admin", "mws_check_backups"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOGGER.error("An error happened when checking ook backups in ent.\n\n"
                     "The output from the command was: %s\n", e.output)
        raise e
    except Exception as e:
        LOGGER.error("An error happened when checking ook backups in ent.\n\n"
                     "The output from the command was: %s\n", e)
        raise e
    try:
        result = json.loads(result)
    except Exception as e:
        LOGGER.error("An error happened when checking ook backups in ent.\n\n"
                     "Result is not in json format: %s\n", result)
        raise e
    for failed_backup in result['failed']:
        LOGGER.error("A backup for the host %s did not complete last night", failed_backup)

    for vm in VirtualMachine.objects.filter(service__site__deleted=False,
                                            service__site__start_date__lt=(date.today() - timedelta(days=1)),
                                            service__status__in=('ansible', 'ansible_queued', 'ready'),
                                            service__site__end_date__lte=date.today()):
        if not filter(lambda host: host.startswith(vm.name), result['ok']+result['failed']):
            LOGGER.error("A backup for the host %s did not complete last night", vm.name)
