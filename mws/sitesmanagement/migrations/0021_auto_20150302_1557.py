# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0020_auto_20150130_1434'),
    ]

    operations = [
        migrations.RenameField(
            model_name='virtualmachine',
            old_name='host_network_configuration',
            new_name='network_configuration',
        ),
    ]
