# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0017_auto_20141203_1213'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='NetworkConfig',
            new_name='ServiceNetworkConfig',
        ),
        migrations.RenameField(
            model_name='site',
            old_name='network_configuration',
            new_name='service_network_configuration',
        ),
    ]
