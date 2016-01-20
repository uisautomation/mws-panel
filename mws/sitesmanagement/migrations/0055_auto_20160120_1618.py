# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0054_auto_20160119_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='preallocated',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
