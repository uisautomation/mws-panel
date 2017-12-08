from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'List of users to be created as superusers. This is only for brand new installations. ' \
           'Existing users will be ignored'

    def add_arguments(self, parser):
        parser.add_argument('crsid', nargs='+', type=str)

    def handle(self, *args, **options):
        for crsid in options['crsid']:
            try:
                User.objects.create_superuser(crsid, None, None)
            except Exception:
                pass
