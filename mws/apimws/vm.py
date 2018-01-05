from django.conf import settings
exec('from %s import *' % getattr(settings, 'VM_API', "apimws.xen"))
