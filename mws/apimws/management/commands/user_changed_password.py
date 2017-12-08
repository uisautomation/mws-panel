from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from apimws.ansible import launch_ansible_by_user


class Command(BaseCommand):
    help = "Informs the django admin panel that the user has changed their UIS password"

    def add_arguments(self, parser):
        parser.add_argument('crsid', type=str)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['crsid'])
        except User.DoesNotExist:
            return  # The user has never used MWS

        launch_ansible_by_user(user)
