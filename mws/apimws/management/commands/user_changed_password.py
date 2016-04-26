from django.contrib.auth.models import User
from django.core.management.base import NoArgsCommand, CommandError
from apimws.ansible import launch_ansible_by_user


class Command(NoArgsCommand):
    args = "{ <crsid> }"
    help = "Informs the django admin panel that the user has changed their UIS password"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("You need to supply a crsid")
        try:
            user = User.objects.get(username=args[0])
        except User.DoesNotExist:
            return  # The user has never used MWS

        launch_ansible_by_user(user)
