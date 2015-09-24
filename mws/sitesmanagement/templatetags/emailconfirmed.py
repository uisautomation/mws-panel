from django import template
from sitesmanagement.models import EmailConfirmation

register = template.Library()

@register.filter
def emailconfirmed(value):
    site = value
    if site and site.email and EmailConfirmation.objects.filter(email=site.email, site_id=site.id,
                                                                status='accepted').exists():
        return True
    return False
