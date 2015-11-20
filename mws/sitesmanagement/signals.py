from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apimws.ipreg import delete_sshfp, delete_cname
from sitesmanagement.models import DomainName, SiteKey


@receiver(post_save, sender=DomainName)
def add_name_to_user(instance, **kwargs):
    dn = instance
    site = dn.site
    if not site.main_domain:
        site.main_domain = dn
        site.save()


@receiver(pre_delete, sender=SiteKey)
def delete_sshfp_from_dns(instance, **kwargs):
    if instance.type != "ED25519":
        for service in instance.site.services.all():
            delete_sshfp(service.network_configuration.name, SiteKey.ALGORITHMS[instance.type], 1)
            delete_sshfp(service.network_configuration.name, SiteKey.ALGORITHMS[instance.type], 2)
            for vm in service.virtual_machines.all():
                delete_sshfp(vm.network_configuration.name, SiteKey.ALGORITHMS[instance.type], 1)
                delete_sshfp(vm.network_configuration.name, SiteKey.ALGORITHMS[instance.type], 2)


@receiver(pre_delete, sender=DomainName)
def delete_cname_from_dns(instance, **kwargs):
    if instance.status == "accepted":
        delete_cname(instance.name)
