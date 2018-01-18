from django.conf import settings

VM_API = getattr(settings, 'ANSIBLE_IMPL', "apimws.ansible_impl")

if VM_API == "apimws.ansible_mock":
    from apimws.ansible_mock import *
else:
    from apimws.ansible_impl import *
