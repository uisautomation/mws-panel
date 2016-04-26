# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0034_auto_20150623_1306'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='vhost',
            unique_together=set([('name', 'service')]),
        ),
    ]
