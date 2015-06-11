from django.conf import settings

VM_API = getattr(settings, 'VM_API', "xen")
if VM_API == "vmware":
    from apimws.platforms import *
else:
    from apimws.xen import *
