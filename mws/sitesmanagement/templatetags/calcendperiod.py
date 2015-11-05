from datetime import timedelta
from django import template


register = template.Library()


@register.filter
def calcendperiod(value):
    if value.day == 29 and value.month == 2:
        return value.replace(year=value.year + 1, month=2, day=28)
    return value.replace(year=value.year + 1) - timedelta(days=1)


@register.filter
def renewalsdate(value, year):
    if value.day == 29 and value.month == 2:
        return value.replace(year=year, month=3, day=1)
    return value.replace(year=year)
