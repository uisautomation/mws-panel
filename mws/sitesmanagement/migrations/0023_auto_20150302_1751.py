# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0022_auto_20150302_1645'),
    ]

    operations = [
        migrations.RenameModel(old_name='HostNetworkConfig', new_name='NetworkConfig'),
    ]
