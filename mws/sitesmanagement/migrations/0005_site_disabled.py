# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0004_auto_20140917_1053'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='disabled',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
