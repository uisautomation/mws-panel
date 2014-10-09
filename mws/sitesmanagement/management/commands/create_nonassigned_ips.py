from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from sitesmanagement.models import NetworkConfig


class Command(BaseCommand):
    args = '<crsid crsid crsid ...>'
    help = 'List of users to be created as superusers. This is only for brand new installations. ' \
           'Existing users will be ignored'

    def handle(self, *args, **options):
        for i in range(1, 10):
            for j in range(1, 124):
                NetworkConfig.objects.create(IPv4="10.0.%d.%d" % (i, j), IPv6="::ffff:10.0.%d.%d" % (i, j),
                                             mws_domain="%d.%d.mws.csx.cam.ac.uk" % (i, j), type="public")
            for j in range(125, 250):
                NetworkConfig.objects.create(IPv4="10.0.%d.%d" % (i, j), IPv6="::ffff:10.0.%d.%d" % (i, j),
                                             mws_domain="%d.%d.mws.csx.cam.ac.uk" % (i, j), type="private")