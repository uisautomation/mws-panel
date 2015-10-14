import csv
from datetime import date, timedelta
from StringIO import StringIO
from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from django.core.mail import EmailMessage
from django.core.management.base import NoArgsCommand, CommandError
from sitesmanagement.models import Site, Billing


class Command(NoArgsCommand):
    args = "{ <month> <year> }"
    help = "Generates a financial monthly report for the month and year specified"

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("You need to specify a month and a year of the financial report you want")
        month = int(args[0])
        year = int(args[1])
        inidate = date(year, month, 1)
        if month == 12:
            enddate = date(year+1, 1, 1)
        else:
            enddate = date(year, month+1, 1)

        billing_list = Billing.objects.filter(date_modified__lt=enddate, date_modified__gte=inidate)
        billing_list = map(lambda x: [x.site.id, x.site.name, x.site.institution_id, x.group, x.purchase_order_number,
                                      x.site.start_date, settings.YEAR_COST], billing_list)

        tempstream = StringIO()
        writer = csv.writer(tempstream)

        for billing in billing_list:
            writer.writerow(billing)

        EmailMessage(
            subject="Monthly Report MWS3",
            body="Attached you can find the monthly report",
            from_email="Managed Web Service Support <mws3-support@cam.ac.uk>",
            to=['amc203@cam.ac.uk'],
            headers={'Return-Path': 'mws3-support@cam.ac.uk'},
            attachments=[('mws3.csv', tempstream.getvalue(), 'application/vnd.ms-excel')]
        ).send()

        tempstream.close()
