from django.core.management.base import NoArgsCommand, CommandError
from sitesmanagement.models import Vhost


class Command(NoArgsCommand):
    args = "{ <vhost_id> <hash> }"
    help = "Stores the TLS key hash and the CSR in the database"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("All arguments need to be supplied")
        try:
            vhost = Vhost.objects.get(id=args[0])
        except Vhost.DoesNotExist:
            raise CommandError("Vhost not found")

        key_hash_file = open("/home/mws-admin/files_repo/vhost_tls/%d/key_hash" % vhost.id, "r")
        vhost.tls_key_hash = key_hash_file.read()
        key_hash_file.close()

        csr_file = open("/home/mws-admin/files_repo/vhost_tls/%d/csr" % vhost.id, "r")
        vhost.csr = csr_file.read()
        csr_file.close()

        vhost.save()
