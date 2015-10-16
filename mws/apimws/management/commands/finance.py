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


class Command(NoArgsCommand):
    args = "{ <month> <year> }"
    help = "Generates a financial monthly report for the month and year specified"

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("You need to specify a month and a year of the financial report you want")
        month = int(args[0])
        year = int(args[1])

        #################
        ### NEW SITES ###
        #################

        if month == 1:
            inidate = date(year-1, 12, 1)
        else:
            inidate = date(year, month-1, 1)

        if Site.objects.filter(start_date__month=inidate.month, start_date__year=inidate.year,
                               deleted=False, billing__isnull=True).exists():
            LOGGER.error("Sites not cancelled were found without billing after a month")

        new_sites_billing = Billing.objects.filter(site__start_date__month=inidate.month,
                                                   site__start_date__year=inidate.year, site__deleted=False)

        ################
        ### RENEWALS ###
        ################

        # Send renewal to finance if it the billing was sent to finance 1 year (or more) ago
        renewal_sites_billing = Billing.objects.filter(site__start_date__month=month,
                                                       site__start_date__lt=date(year, 1, 1), site__deleted=False)

        if not(new_sites_billing.exists() or renewal_sites_billing.exists()):
            return  # Nothing to send

        ###################
        ### SEND REPORT ###
        ###################

        po_files = map(lambda x: ("%s%s" % (x.purchase_order_number, splitext(x.purchase_order.name)[1]),
                                  x.purchase_order.read(), 'application/other'),
                       new_sites_billing | renewal_sites_billing)
        new_billing = map(lambda x: [x.site.id, x.site.name, x.site.institution_id, x.group,
                                     x.purchase_order_number, x.site.start_date, settings.YEAR_COST, x.site.start_date,
                                     x.site.start_date.replace(year = x.site.start_date.year + 1)],
                          new_sites_billing)
        renewals_billing = map(lambda x: [x.site.id, x.site.name, x.site.institution_id, x.group,
                                          x.purchase_order_number, x.site.start_date, settings.YEAR_COST,
                                          x.site.start_date.replace(year = year),
                                          x.site.start_date.replace(year = year + 1)],
                               renewal_sites_billing)
        header = ['id', 'Name', 'Institution', 'PO raised by', 'PO number', 'Created at', 'Cost', 'Period start',
                  'Period end']
        new_billing = [header] + new_billing
        renewals_billing = [header] + renewals_billing

        stream_new = StringIO()
        stream_renewal = StringIO()
        writer_new = csv.writer(stream_new)
        writer_renewal = csv.writer(stream_renewal)

        for billing in new_billing:
            writer_new.writerow(billing)

        for billing in renewals_billing:
            writer_renewal.writerow(billing)

        EmailMessage(
            subject="Monthly Financial Report MWS3 - %s %i" % (month_name[month], year),
            body="Attached you can find the monthly report spreadsheet for new sites and for renewals. You will "
                 "also find all the the corresponding purchase orders",
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=[settings.FINANCE_EMAIL],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'},
            attachments=[('mws3sites_new.csv', stream_new.getvalue(), 'application/vnd.ms-excel'),
                         ('mws3sites_renewals.csv', stream_renewal.getvalue(), 'application/vnd.ms-excel')] + po_files
        ).send()

        new_sites_billing.update(date_sent_to_finance=timezone.now().date())
        renewal_sites_billing.update(date_sent_to_finance=timezone.now().date())

        stream_new.close()
        stream_renewal.close()
