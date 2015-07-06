# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0035_auto_20150623_1307'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='service',
            unique_together=set([('site', 'type'), ('network_configuration',)]),
        ),
    ]
