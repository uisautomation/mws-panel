# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0064_auto_20160316_1050'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suspension',
            name='end_date',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='suspension',
            name='start_date',
            field=models.DateTimeField(auto_now_add=True),
            preserve_default=True,
        ),
    ]
