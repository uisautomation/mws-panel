from django.conf import settings
exec('from %s import *' % getattr(settings, 'ANSIBLE_IMPL', "apimws.ansible_impl"))
