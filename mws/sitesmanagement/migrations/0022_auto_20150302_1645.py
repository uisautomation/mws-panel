# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0021_auto_20150302_1557'),
    ]

    operations = [
        migrations.RenameField(
            model_name='hostnetworkconfig',
            old_name='hostname',
            new_name='name',
        ),
        migrations.AddField(
            model_name='hostnetworkconfig',
            name='IPv4',
            field=models.GenericIPAddressField(unique=True, null=True, protocol=b'IPv4', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='hostnetworkconfig',
            name='IPv4_gateway',
            field=models.GenericIPAddressField(null=True, protocol=b'IPv4', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='hostnetworkconfig',
            name='IPv4_netmask',
            field=models.GenericIPAddressField(null=True, protocol=b'IPv4', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='hostnetworkconfig',
            name='type',
            field=models.CharField(default='host', max_length=50, choices=[(b'service', b'Service'),
                                                                           (b'host', b'Host')]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='hostnetworkconfig',
            name='IPv6',
            field=models.GenericIPAddressField(unique=True, null=True, protocol=b'IPv6', blank=True),
            preserve_default=True,
        ),
    ]
