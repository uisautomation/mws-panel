from datetime import timedelta
from django import template


register = template.Library()


@register.filter
def calcendperiod(value):
    return value.replace(year = value.year + 1) - timedelta(days=1)


@register.filter
def renewalsdate(value, year):
    return value.replace(year=year)
