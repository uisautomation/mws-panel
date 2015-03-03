# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations


def host_to_ipv6(apps, schema_editor):
    """
    Changes NetworkConfig.type from 'host' to 'ipv6'
    """
    NetworkConfig = apps.get_model('sitesmanagement', 'NetworkConfig')
    for netconf in NetworkConfig.objects.filter(type='host'):
        netconf.type = 'ipv6'
        netconf.save()


def host_to_ipv6_reverse(apps, schema_editor):
    """
    Changes NetworkConfig.type back from 'ipv6' to 'host'
    """
    NetworkConfig = apps.get_model('sitesmanagement', 'NetworkConfig')
    for netconf in NetworkConfig.objects.filter(type='ipv6'):
        netconf.type = 'host'
        netconf.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0024_auto_20150303_1437'),
    ]

    operations = [
        migrations.AlterField(
            model_name='networkconfig',
            name='type',
            field=models.CharField(max_length=50, choices=[(b'ipv4pub', b'Public IPv4 Only'),
                                                           (b'ipv4priv', b'Private IPv4 Only'),
                                                           (b'ipvxpub', b'Public IPv4 and IPv6'),
                                                           (b'ipvxpriv', b'Private IPv4 and IPv6'),
                                                           (b'ipv6', b'IPv6 Only')]),
            preserve_default=True,
        ),
        migrations.RunPython(host_to_ipv6, host_to_ipv6_reverse),
    ]
