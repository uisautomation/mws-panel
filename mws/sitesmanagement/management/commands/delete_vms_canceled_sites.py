from datetime import timedelta, date
from django.core.management.base import BaseCommand
from sitesmanagement.models import Site


class Command(BaseCommand):
    args = ''
    help = 'Deletes VMs associated to sites that were cancelled more than 30 days ago'

    def handle(self, *args, **options):
        old_deleted_sites = Site.objects.filter(end_date__lt=date.today()-timedelta(days=30),
                                                virtual_machines__isnull=True)
        for old_site in old_deleted_sites:
            if old_site.primary_vm:
                old_site.primary_vm.delete()
            if old_site.secondary_vm:
                old_site.secondary_vm.delete()