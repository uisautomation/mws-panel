# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def service_to_netconf(apps, schema_editor):
    """
    Copies all ServiceNetworkConfig to NetworkConfig
    to NetworkConfig
    """
    NetworkConfig = apps.get_model('sitesmanagement', 'NetworkConfig')
    ServiceNetworkConfig = apps.get_model('sitesmanagement', 'ServiceNetworkConfig')
    for servicenetconf in ServiceNetworkConfig.objects.all():
        NetworkConfig.objects.create(IPv4=servicenetconf.IPv4,
                                     IPv6=servicenetconf.IPv6,
                                     name=servicenetconf.mws_domain,
                                     type='ipvxpub')
        NetworkConfig.objects.create(IPv4=servicenetconf.IPv4private,
                                     name=servicenetconf.mws_private_domain,
                                     type='ipv4priv')


def service_to_netconf_reverse(apps, schema_editor):
    """
    Reverse to service_to_netconf
    """
    NetworkConfig = apps.get_model('sitesmanagement', 'NetworkConfig')
    NetworkConfig.objects.filter(type='ipvxpub').delete()
    NetworkConfig.objects.filter(type='ipv4priv').delete()


def service_to_netconf_site(apps, schema_editor):
    """
    Copies all Site.service_network_configuration to Site.network_configuration, from ServiceNetworkConfig
    to NetworkConfig
    """
    Site = apps.get_model('sitesmanagement', 'Site')
    NetworkConfig = apps.get_model('sitesmanagement', 'NetworkConfig')
    Service = apps.get_model('sitesmanagement', 'Service')
    for site in Site.objects.all():
        netconf_prod = NetworkConfig.objects.get(IPv4=site.service_network_configuration.IPv4)
        netconf_test = NetworkConfig.objects.get(IPv4=site.service_network_configuration.IPv4private)
        prod_service = Service.objects.create(network_configuration=netconf_prod, site=site, type='production')
        test_service = Service.objects.create(network_configuration=netconf_test, site=site, type='test')
        primary_vm = site.virtual_machines.filter(primary=True)
        secondary_vm = site.virtual_machines.filter(primary=False)
        if primary_vm:
            primary_vm = primary_vm[0]
            primary_vm.service = prod_service
            primary_vm.save()
        if secondary_vm:
            secondary_vm = secondary_vm[0]
            secondary_vm.service = test_service
            secondary_vm.save()


def service_to_netconf_site_reverse(apps, schema_editor):
    """
    Reverse to service_to_netconf_site
    """
    Service = apps.get_model('sitesmanagement', 'Service')
    Service.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0025_auto_20150303_1607'),
    ]

    operations = [
        migrations.RunPython(service_to_netconf, service_to_netconf_reverse),
        migrations.RunPython(service_to_netconf_site, service_to_netconf_site_reverse),
    ]
