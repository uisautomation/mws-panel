from django.db.models.signals import post_save
from django.dispatch import receiver
from sitesmanagement.models import DomainName


@receiver(post_save, sender=DomainName)
def add_name_to_user(instance, **kwargs):
    dn = instance
    site = dn.site
    if not site.main_domain:
        site.main_domain = dn
        site.save()