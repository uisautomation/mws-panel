import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apimws.ipreg import delete_sshfp, delete_cname
from sitesmanagement.models import DomainName, SiteKey, Site, VirtualMachine

LOGGER = logging.getLogger('mws')


@receiver(post_save, sender=DomainName)
def check_main_domain_name(instance, **kwargs):
    vhost = instance.vhost
    if not vhost.main_domain and instance.status in ['external', 'accepted', 'special']:
        vhost.main_domain = instance
        vhost.save()


@receiver(pre_delete, sender=SiteKey)
def delete_sshfp_from_dns(instance, **kwargs):
    '''Delete SSHFP records from the DNS using the DNS API when a SiteKey is deleted from the database'''
    for service in instance.site.services.all():
        for fptype in SiteKey.FP_TYPES:
            delete_sshfp(service.network_configuration.name, SiteKey.ALGORITHMS[instance.type],
                         SiteKey.FP_TYPES[fptype])
        for vm in service.virtual_machines.all():
            for fptype in SiteKey.FP_TYPES:
                delete_sshfp(vm.network_configuration.name, SiteKey.ALGORITHMS[instance.type],
                             SiteKey.FP_TYPES[fptype])

@receiver(pre_delete, sender=DomainName)
def delete_cname_from_dns(instance, **kwargs):
    """Delete the hostname entry from the DNS using the DNS API when a the DomainName is deleted from
    the database and it is an internal cam.ac.uk hostname accepted by the owner of the domain."""
    if instance.status == "accepted":
        delete_cname.delay(instance.name)


@receiver(pre_delete, sender=Site)
def log_deleted_site(sender, instance, **kwargs):
    LOGGER.info("Class %s deleted the Site %s" % (str(sender), instance.name))


@receiver(pre_delete, sender=VirtualMachine)
def log_deleted_site(sender, instance, **kwargs):
    LOGGER.info("Class %s deleted the Virtual Machine %s" % (str(sender), instance.name))
