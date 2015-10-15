import csv
from datetime import date
from StringIO import StringIO
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import NoArgsCommand, CommandError
from django.utils import timezone
from os.path import splitext
from sitesmanagement.models import Site

LOGGER = logging.getLogger('mws')


def generateemail(sitelist):
    billing_list_file = map(lambda x: ("%d%s" % (x.id, splitext(x.billing.purchase_order.name)[1]),
                                       x.billing.purchase_order.read(), 'application/other'),
                            sitelist)
    billing_list_info = map(lambda x: [x.id, x.name, x.institution_id, x.billing.group,
                                       x.billing.purchase_order_number, x.start_date, settings.YEAR_COST],
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
        inidate = date(year, month, 1)

        pendingsites = Site.objects.filter(start_date__lte=inidate, deleted=False,
                                           billing__date_sent_to_finance__isnull=True)

        if pendingsites.filter(billing__isnull=True).exists():
            LOGGER.error("Sites not cancelled were found without billing after a month")

        pendingsites = pendingsites.filter(billing__isnull=False)

        tempstream, billing_list_file = generateemail(pendingsites)

        EmailMessage(
            subject="New Sites Monthly Report MWS3",
            body="Attached you can find the monthly report spreadsheet file and the corresponding purchase orders.",
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[settings.FINANCE_EMAIL],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'},
            attachments=[('mws3report.csv', tempstream.getvalue(), 'application/vnd.ms-excel')]+billing_list_file
        ).send()

        tempstream.close()

        pendingsites.update(billing__date_sent_to_finance=timezone.now().date())

        ################
        ### RENEWALS ###
        ################

        # Send renewal to finance if it the billing was sent to finance 1 year (or more) ago
        if month == 12:
            renewaldate = date(year, 1, 1)
        else:
            renewaldate = date(year-1, month+1, 1)

        renewalsites = Site.objects.filter(deleted=False, billing__date_sent_to_finance__lte=renewaldate)

        tempstream, billing_list_file = generateemail(renewalsites)

        EmailMessage(
            subject="Renewal Sites Monthly Report MWS3",
            body="Attached you can find the monthly report spreadsheet file and the corresponding purchase orders.",
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[settings.FINANCE_EMAIL],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'},
            attachments=[('mws3report.csv', tempstream.getvalue(), 'application/vnd.ms-excel')]+billing_list_file
        ).send()

        tempstream.close()

        renewalsites.update(billing__date_sent_to_finance=timezone.now().date())
