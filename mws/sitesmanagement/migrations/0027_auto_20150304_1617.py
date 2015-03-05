# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0026_auto_20150303_1615'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='network_configuration',
            field=models.OneToOneField(null=True, blank=True, to='sitesmanagement.NetworkConfig'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='service',
            name='site',
            field=models.ForeignKey(blank=True, to='sitesmanagement.Site', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='site',
            name='service_network_configuration',
            field=models.OneToOneField(related_name='site', null=True, blank=True,
                                       to='sitesmanagement.ServiceNetworkConfig'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='service',
            field=models.ForeignKey(related_name='virtual_machines', to='sitesmanagement.Service', null=True),
            preserve_default=True,
        ),
    ]
