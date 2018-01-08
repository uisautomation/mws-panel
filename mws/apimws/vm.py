from django.conf import settings

VM_API = getattr(settings, 'VM_API', "apimws.xen")

if VM_API == "apimws.xen_mock":
    from apimws.xen_mock import *
else:
    from apimws.xen import *
