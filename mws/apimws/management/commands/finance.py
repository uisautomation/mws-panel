from calendar import month_name
import csv
from datetime import date, timedelta
from StringIO import StringIO
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import NoArgsCommand, CommandError
from django.utils import timezone
from os.path import splitext
from sitesmanagement.models import Site, Billing


LOGGER = logging.getLogger('mws')


def generateemail(sitelist):
    billing_list_file = map(lambda x: ("%d%s" % (x.site.id, splitext(x.purchase_order.name)[1]),
                                       x.purchase_order.read(), 'application/other'),
                            sitelist)
    billing_list_info = map(lambda x: [x.site.id, x.site.name, x.site.institution_id, x.group,
                                       x.purchase_order_number, x.site.start_date, settings.YEAR_COST],
                            sitelist)

    tempstream = StringIO()
    writer = csv.writer(tempstream)

    for billing in billing_list_info:
        writer.writerow(billing)

    return tempstream, billing_list_file

class Command(NoArgsCommand):
    args = "{ <month> <year> }"
    help = "Generates a financial monthly report for the month and year specified"

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("You need to specify a month and a year of the financial report you want")
        month = int(args[0])
        year = int(args[1])
        if month == 1:
            inidate = date(year-1, 12, 1)
        else:
            inidate = date(year, month-1, 1)
        enddate = date(year, month, 1) - timedelta(days=1)

        if Site.objects.filter(start_date__month=inidate.month, start_date__year=inidate.year,
                               deleted=False, billing__isnull=True).exists():
            LOGGER.error("Sites not cancelled were found without billing after a month")

        pendingsitesbilling = Billing.objects.filter(site__start_date__month=inidate.month,
                                                     site__start_date__year=inidate.year, site__deleted=False)

        if pendingsitesbilling.exists():
            tempstream, billing_list_file = generateemail(pendingsitesbilling)

            EmailMessage(
                subject="New Sites Monthly Report MWS3 - Period from %s to %s." % (inidate.isoformat(),
                                                                                   enddate.isoformat()),
                body="Attached you can find the monthly report spreadsheet file and the corresponding purchase orders"
                     "for the following period: from %s to %s." % (inidate.isoformat(), enddate.isoformat()),
                from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
                to=[settings.FINANCE_EMAIL],
                headers={'Return-Path': 'mws3-support@cam.ac.uk'},
                attachments=[('mws3report.csv', tempstream.getvalue(), 'application/vnd.ms-excel')]+billing_list_file
            ).send()

            tempstream.close()

            pendingsitesbilling.update(date_sent_to_finance=timezone.now().date())

        ################
        ### RENEWALS ###
        ################

        # Send renewal to finance if it the billing was sent to finance 1 year (or more) ago
        renewalsitesbilling = Billing.objects.filter(site__start_date__month=month,
                                                     site__start_date__year__lt=year,
                                                     site__deleted=False)

        if renewalsitesbilling.exists():
            tempstream, billing_list_file = generateemail(renewalsitesbilling)

            EmailMessage(
                subject="Renewal Sites Monthly Report MWS3 - Period of %s of previous years" % month_name[month],
                body="Attached you can find the monthly report spreadsheet file and the corresponding purchase orders"
                     "for the following period: %s of previous year." % month_name[month],
                from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
                to=[settings.FINANCE_EMAIL],
                headers={'Return-Path': 'mws3-support@cam.ac.uk'},
                attachments=[('mws3report.csv', tempstream.getvalue(), 'application/vnd.ms-excel')]+billing_list_file
            ).send()

            tempstream.close()

            renewalsitesbilling.update(date_sent_to_finance=timezone.now().date())
