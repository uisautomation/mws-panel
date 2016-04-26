# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0053_auto_20151126_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='quarantined',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
