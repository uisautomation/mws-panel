from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<crsid crsid crsid ...>'
    help = 'List of users to be created as superusers. This is only for brand new installations. ' \
           'Existing users will be ignored'

    def handle(self, *args, **options):
        for crsid in args:
            try:
                User.objects.create_superuser(crsid, None, None)
            except Exception as e:
                pass