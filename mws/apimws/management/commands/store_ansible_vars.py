from django.core.management.base import NoArgsCommand, CommandError
from apimws.models import AnsibleConfiguration
from sitesmanagement.models import Service


class Command(NoArgsCommand):
    args = "{ <service_id> <variable_name> <variable_value> }"
    help = "Stores variables of a MWS3 server in the database"

    def handle(self, *args, **options):
        if len(args) != 3:
            raise CommandError("All arguments need to be supplied")
        try:
            service = Service.objects.get(id=args[0].replace("mwsservice-", ""))
            variable_name = args[1]
            if variable_name not in ["mysql_root_password"]:
                raise
        except Service.DoesNotExist:
            raise CommandError("Service not found with id: %s" % args[0])
        except:
            raise CommandError("Incorrect variable name")

        ansibleconf, created = AnsibleConfiguration.objects.get_or_create(service=service, key=variable_name)
        ansibleconf.value = args[2]
        ansibleconf.save()
