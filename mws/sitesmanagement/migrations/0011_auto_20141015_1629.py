# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0010_auto_20141015_1438'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='virtualmachine',
            name='network_configuration',
        ),
        migrations.AddField(
            model_name='site',
            name='network_configuration',
            field=models.OneToOneField(related_name=b'site', default=1, to='sitesmanagement.NetworkConfig'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='networkconfig',
            name='IPv4',
            field=models.GenericIPAddressField(unique=True, protocol=b'IPv4'),
        ),
        migrations.AlterField(
            model_name='networkconfig',
            name='IPv4private',
            field=models.GenericIPAddressField(unique=True, protocol=b'IPv4'),
        ),
        migrations.AlterField(
            model_name='networkconfig',
            name='IPv6',
            field=models.GenericIPAddressField(unique=True, protocol=b'IPv6'),
        ),
    ]
