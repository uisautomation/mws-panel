import json
import logging
import subprocess
from datetime import date, timedelta, datetime
from celery import shared_task, Task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from django.utils import timezone

from apimws.ipreg import get_nameinfo
from apimws.utils import preallocate_new_site
from sitesmanagement.models import Billing, Site, VirtualMachine, DomainName

LOGGER = logging.getLogger('mws')


class FinanceTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to send an email to Finance.\nThe task id is %s.\n\n"
                     "The parameters passed to the task were: %s\n\nThe traceback is:\n%s\n", task_id, args, einfo)


class ScheduledTaskWithFailure(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        LOGGER.error("An error happened when trying to execute an scheduled task.\nThe task id is %s.\n\n"
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
            subject="The annual charge for your managed web server is due next month",
            body="You are receiving this message because your email address, or an email alias that includes "
                 "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                 "Server '%s'.\n\nThe annual charge for your managed web server '%s' is due next month on %s. "
                 "Unless you tell us otherwise we will automatically issue an invoice for this at the end of next "
                 "month based on information from the most recent purchase order you have given us. Please use the "
                 "web control panel (under 'billing settings') to check that this information is still current. If "
                 "you want to amend your purchase order you can upload a new one. Your site may be cancelled if we "
                 "can't successfully invoice for it.\n\nIf you no longer want you site then please either cancel "
                 "it now (under 'edit the MWS profile'), or mark it 'Not for renewal' in which case it will be "
                 "automatically cancelled on '%s'."
                 % (billing.site.name, billing.site.name, billing.site.start_date, billing.site.start_date),
            from_email="Managed Web Service Support <%s>"
                       % getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk'),
            to=[billing.site.email],
            headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
        ).send()

    renewal_sites_billing = Billing.objects.filter(site__start_date__month=today.month, site__subscription=True,
                                                   site__start_date__lt=date(today.year, 1, 1),
                                                   site__end_date__isnull=True)
    for billing in renewal_sites_billing:
        EmailMessage(
            subject="REMINDER: the annual charge for your managed web server is due this month",
            body="You are receiving this message because your email address, or an email alias that includes "
                 "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                 "Server '%s'.\n\nThe annual charge for your managed web server '%s' is due this month on %s. "
                 "Unless you tell us otherwise we will automatically issue an invoice for this at the end of this "
                 "month based on information from the most recent purchase order you have given us. If you "
                 "haven't already, please use the web control panel (under 'billing settings') to check that this "
                 "information is still current. If you want to amend your purchase order you can upload a new one. "
                 "Your site may be cancelled if we can't successfully invoice for it.\n\nIf you no longer want "
                 "you site then please either cancel it now (under 'edit the MWS profile'), or mark "
                 "it 'Not for renewal' in which case it will be automatically cancelled on '%s'." 
                 % (billing.site.name, billing.site.name, billing.site.start_date, billing.site.start_date),
            from_email="Managed Web Service Support <mws3-support@uis.cam.ac.uk>",
            to=[billing.site.email],
            headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
        ).send()


@shared_task(base=FinanceTaskWithFailure)
def check_subscription():
    today = timezone.now().date()
    # Check which sites still do not have a billing associated, warn or cancel them based on
    # how many days ago they were created
    sites = Site.objects.filter(billing__isnull=True, end_date__isnull=True, start_date__isnull=False)
    for site in sites:
        if (today - site.start_date) >= timedelta(days=31):
            # Cancel site
            EmailMessage(
                subject="Your managed web server has been cancelled",
                body="You are receiving this message because your email address, or an email alias that includes "
                     "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                     "Server '%s'.\n\nYour managed web server '%s' has been cancelled because we haven't received "
                     "payment information for it." % (site.name, site.name),
                from_email="Managed Web Service Support <mws3-support@uis.cam.ac.uk>",
                to=[site.email],
                headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
            ).send()
            site.cancel()
        elif ((today - site.start_date) == timedelta(days=15)) or ((today - site.start_date) >= timedelta(days=24)):
            # Warning 15 days before and each day in the last week before deadline
            EmailMessage(
                subject="Remember to upload a purchase order for your managed web server",
                body="You are receiving this message because your email address, or an email alias that includes "
                     "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                     "Server '%s'.\n\nPlease upload a purchase order using the control web panel to pay for your "
                     "managed web server '%s'.\n\nIf you don't upload a valid purchase order before %s your site "
                     "'%s' will be automatically cancelled." % (site.name, site.name,
                                                                site.start_date+timedelta(days=30), site.name),
                from_email="Managed Web Service Support <mws3-support@uis.cam.ac.uk>",
                to=[site.email],
                headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
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
            subject="Your managed web server has been cancelled",
            body="You are receiving this message because your email address, or an email alias that includes "
                 "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                 "Server '%s'.\n\nYour managed web site '%s' has been cancelled per your requested." %
                 (site.name, site.name),
            from_email="Managed Web Service Support <mws3-support@uis.cam.ac.uk>",
            to=[site.email],
            headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
        ).send()
        site.cancel()


@shared_task(base=ScheduledTaskWithFailure)
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

    for vm in VirtualMachine.objects.filter(Q(service__site__deleted=False, service__site__disabled=False,
                                              service__site__start_date__lt=(date.today() - timedelta(days=1)),
                                              service__status__in=('ansible', 'ansible_queued', 'ready'))
                                                & (Q(service__site__end_date__isnull=True) |
                                                   Q(service__site__end_date__gt=date.today()))):
        if not filter(lambda host: host.startswith(vm.name), result['ok']+result['failed']):
            LOGGER.error("A backup for the host %s did not complete last night", vm.name)


@shared_task(base=ScheduledTaskWithFailure)
def delete_cancelled():
    """Delete sites that were cancelled 8 weeks ago"""
    Site.objects.filter(end_date__lt=(datetime.today()-timedelta(weeks=8)).date()).delete()


@shared_task(base=ScheduledTaskWithFailure)
def check_num_preallocated_sites():
    desired_num_preallocated_sites = getattr(settings, 'NUM_PREALLOCATED_SITES', 0)
    while Site.objects.filter(preallocated=True).count() < desired_num_preallocated_sites:
        preallocate_new_site()


@shared_task(base=ScheduledTaskWithFailure)
def send_warning_last_or_none_admin():
    for site in Site.objects.filter(Q(start_date__isnull=False) &
                                    (Q(end_date__isnull=True) | Q(end_date__gt=date.today()))):
        num_admins = len(site.list_of_active_admins())
        if num_admins == 1:
            site.days_without_admin = 0
            site.save()
            if datetime.today().weekday() == 0:
                EmailMessage(
                    subject="Your UIS Managed Web Server '%s' has only one administrator" % site.name,
                    body="You are receiving this message because your email address, or an email alias that includes "
                         "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                         "Server '%s'.\n\nThe Managed Web Server '%s' only has a single administrator. This could be "
                         "a problem if some action is required in their absence, or if they leave the University "
                         "since the site would then be automatically suspended. To avoid this, and to stop these "
                         "emails, please add at least one additional administrator via the control panel at %s\n\n"
                         % (site.name, site.name, settings.MAIN_DOMAIN),
                    from_email="Managed Web Service Support <%s>"
                               % getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk'),
                    to=[site.email],
                    headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
                ).send()
        elif num_admins == 0:
            if site.days_without_admin > 7:
                site.suspend_now("No site admin for more than a week")
                site.disable()
                EmailMessage(
                    subject="Your UIS Managed Web Server '%s' has been suspended" % site.name,
                    body="You are receiving this message because your email address, or an email alias that includes "
                         "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                         "Server '%s'.\n\nThe Managed Web Server '%s' had no administrators for the last week "
                         "and has therefore been automatically suspended. It will be deleted in 2 weeks if no action "
                         "is taken.\n\nIf you think this should had not have happened, contact %s\n\n"
                         % (site.name, site.name,
                            getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')),
                    from_email="Managed Web Service Support <%s>"
                               % getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk'),
                    to=[site.email],
                    headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
                ).send()
            else:
                site.days_without_admin += 1
                site.save()
                EmailMessage(
                    subject="Your UIS Managed Web Server '%s' will be suspended" % site.name,
                    body="You are receiving this message because your email address, or an email alias that includes "
                         "you as a recipient, has been configured as the contact address for the UIS Managed Web "
                         "Server '%s'.\n\nThe Managed Web Server '%s' has no administrators and it will be suspended "
                         "in %s days if you do not contact %s and arrange to have at lease one administrator "
                         "added.\n\n" % (site.name, site.name, str(8-site.days_without_admin),
                                          getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')),
                    from_email="Managed Web Service Support <%s>"
                               % getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk'),
                    to=[site.email],
                    headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws3-support@uis.cam.ac.uk')}
                ).send()
        else:
            site.days_without_admin = 0
            site.save()


@shared_task
def reject_or_accepted_old_domain_names_requests():
    for domain_name in DomainName.objects.filter(status='requested',
                                                 requested_at__lt=(timezone.now()-timedelta(days=3))):
        nameinfo = get_nameinfo(domain_name.name)
        if nameinfo['exists'] and "C" not in nameinfo['exists']:
            domain_name.reject_it("This domain name request has been automatically denied due to the lack of answer "
                                  "from the domain name administrator after 3 days.")
        else:
            domain_name.accept_it()
