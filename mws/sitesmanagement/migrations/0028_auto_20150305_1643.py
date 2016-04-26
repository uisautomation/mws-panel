# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0027_auto_20150304_1617'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='site',
            name='service_network_configuration',
        ),
        migrations.DeleteModel(
            name='ServiceNetworkConfig',
        ),
        migrations.RemoveField(
            model_name='virtualmachine',
            name='site',
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='service',
            field=models.ForeignKey(related_name='virtual_machines', to='sitesmanagement.Service'),
            preserve_default=True,
        ),
    ]
