from django.conf import settings
from django.shortcuts import _get_queryset
import warnings


def get_object_or_None(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None


def is_camacuk(domain_name):
    if getattr(settings, 'DEMO', False):
        return domain_name.endswith(".usertest.mws3.csx.cam.ac.uk")
    else:
        return domain_name.endswith(".cam.ac.uk")


def deprecated(func):
    '''This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.'''
    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function {}.".format(func.__name__), category=DeprecationWarning)
        return func(*args, **kwargs)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


def can_create_new_site():
    from sitesmanagement.models import NetworkConfig
    return (NetworkConfig.objects.filter(service=None, type='ipvxpub').count() > 0 and
            NetworkConfig.objects.filter(service=None, type='ipv4priv').count() > 0 and
            NetworkConfig.objects.filter(vm=None, type='ipv6').count() > 0)
