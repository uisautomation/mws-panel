import re
import warnings
from django.shortcuts import _get_queryset


def get_object_or_None(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None


def is_camacuk(domain_name):
    return domain_name.endswith(".cam.ac.uk")


def is_camacuk_subdomain(domain_name):
    return re.match("^[a-zA-Z0-9\-]+.cam.ac.uk$", domain_name)


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
    from sitesmanagement.models import Site
    return Site.objects.filter(preallocated=True, disabled=True).count() > 0
