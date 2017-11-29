from django.core.management.base import BaseCommand, CommandError
from apimws.models import AnsibleConfiguration
from sitesmanagement.models import Service


class BadVariableName(ValueError):
    pass


class Command(BaseCommand):
    help = "Stores variables of a MWS3 server in the database"

    def add_arguments(self, parser):
        parser.add_argument('service_id', type=str)
        parser.add_argument('variable_name', type=str)
        parser.add_argument('variable_value', type=str)

    def handle(self, *args, **options):
        try:
            service = Service.objects.get(id=options['service_id'].replace("mwsservice-", ""))
            variable_name = options['variable_name']
            if variable_name not in ["mysql_root_password"]:
                raise BadVariableName()
        except Service.DoesNotExist:
            raise CommandError("Service not found with id: %s" % args[0])
        except BadVariableName:
            raise CommandError("Incorrect variable name")

        ansibleconf, created = AnsibleConfiguration.objects.get_or_create(service=service, key=variable_name)
        ansibleconf.value = options['variable_value']
        ansibleconf.save()
