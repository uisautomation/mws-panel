import csv
import logging
from calendar import month_name
from datetime import date
from StringIO import StringIO
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import NoArgsCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify
from os.path import splitext
from ucamlookup import get_institutions, get_institution_name_by_id
from sitesmanagement.models import Site, Billing
from sitesmanagement.templatetags.calcendperiod import calcendperiod


LOGGER = logging.getLogger('mws')


class Command(NoArgsCommand):
    args = "{ <month> <year> }"
    help = "Generates a financial monthly report for the month and year specified"

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("You need to specify a month and a year of the financial report you want")
        month = int(args[0])
        year = int(args[1])

        ###################
        ### NEW SERVERS ###
        ###################

        if month == 1:
            inidate = date(year-1, 12, 1)
        else:
            inidate = date(year, month-1, 1)

        # Sites that haven't been canceled (end_date is null) and do not have a billing (PO) associated
        if Site.objects.filter(start_date__month=inidate.month, start_date__year=inidate.year,
                               end_date__isnull=True, billing__isnull=True).exists():
            LOGGER.error("Sites not cancelled were found without billing after a month")

        # Billings of sites that haven't been canceled (end_date is null) and are new (start_date actual month/year)
        new_sites_billing = Billing.objects.filter(site__start_date__month=inidate.month,
                                                   site__start_date__year=inidate.year, site__end_date__isnull=True)

        ################
        ### RENEWALS ###
        ################

        # Billings of sites that haven't been canceled (end_date is null), that hasn't expressed to want to cancel
        # their subscription, and that started in the actual month of a previous year
        renewal_sites_billing = Billing.objects.filter(site__start_date__month=month,
                                                       site__start_date__lt=date(year, 1, 1),
                                                       site__end_date__isnull=True)

        if not(new_sites_billing.exists() or renewal_sites_billing.exists()):
            return  # Nothing to send

        ###################
        ### SEND REPORT ###
        ###################

        all_institutitons = get_institutions() # We catch all institutions to avoid hitting lookup several times

        po_files = map(lambda x: ("%s%s" % (slugify(x.purchase_order_number), splitext(x.purchase_order.name)[1]),
                                  x.purchase_order.read(), 'application/other'),
                       new_sites_billing | renewal_sites_billing)
        new_billing = map(lambda x: [x.site.id, x.site.name,
                                     get_institution_name_by_id(x.site.institution_id, all_institutitons), x.group,
                                     x.purchase_order_number, x.site.start_date, settings.YEAR_COST, x.site.start_date,
                                     calcendperiod(x.site.start_date)],
                          new_sites_billing)
        renewals_billing = map(lambda x: [x.site.id, x.site.name,
                                          get_institution_name_by_id(x.site.institution_id, all_institutitons), x.group,
                                          x.purchase_order_number, x.site.start_date, settings.YEAR_COST,
                                          x.site.start_date.replace(year = year), calcendperiod(x.site.start_date)],
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
            body="Hello,\n\nAttached you can find the monthly report spreadsheet for new servers and for renewals. "
                 "You will also find all the corresponding purchase orders. The cost codes for MWS3 are:\n\n"
                 "Cost centre for Managed Web Service = VCBQ\nTransaction code for Managed Web Service = LRED\n"
                 "Internal code = VCBQ GAAB LRED\nExternal code = VCBQ GAAA LRED\n\nBest regards,\n\nMWS3 Team.\n",
            from_email="Managed Web Service Support <%s>"
                       % getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws-support@uis.cam.ac.uk'),
            to=[settings.FINANCE_EMAIL],
            headers={'Return-Path': getattr(settings, 'EMAIL_MWS3_SUPPORT', 'mws-support@uis.cam.ac.uk')},
            attachments=[('mws3sites_new.csv', stream_new.getvalue(), 'application/vnd.ms-excel'),
                         ('mws3sites_renewals.csv', stream_renewal.getvalue(), 'application/vnd.ms-excel')] + po_files
        ).send()

        new_sites_billing.update(date_sent_to_finance=timezone.now().date())
        renewal_sites_billing.update(date_sent_to_finance=timezone.now().date())

        stream_new.close()
        stream_renewal.close()
