from django.core.management.base import BaseCommand, CommandError
from sitesmanagement.models import Vhost


class Command(BaseCommand):
    '''
        "requested": First time a CSR is requested, a new key hash and csr needs to be passed to the server
        "renewal": An existing CSR exists a new key and CSR is generated, new csr needs to be passed to the server
        "renewal_cert": New certificate uploaded, pass new key hash to the server
    '''
    help = "Stores the TLS key hash and the CSR in the database"

    def add_arguments(self, parser):
        parser.add_argument('vhost_id', type=str)

    def handle(self, *args, **options):
        try:
            vhost = Vhost.objects.get(id=options['vhost_id'])
        except Vhost.DoesNotExist:
            raise CommandError("Vhost not found")

        if vhost.tls_key_hash == 'renewal':
            vhost.tls_key_hash = 'renewal_waiting_cert'
        else:
            key_hash_file = open("/home/mws-admin/files_repo/vhost_tls/%d/key_hash" % vhost.id, "r")
            vhost.tls_key_hash = key_hash_file.read()
            key_hash_file.close()

        csr_file = open("/home/mws-admin/files_repo/vhost_tls/%d/csr" % vhost.id, "r")
        vhost.csr = csr_file.read()
        csr_file.close()
        if vhost.csr == "Requested via ACME":
            vhost.tls_enable = True
        vhost.save()
