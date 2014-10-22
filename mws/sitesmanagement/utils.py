import re
from django.shortcuts import _get_queryset


def get_object_or_None(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None


def is_camacuk(domain_name):
    return domain_name.endswith("cam.ac.uk")
