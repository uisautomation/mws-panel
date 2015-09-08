# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0039_auto_20150901_1505'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshot',
            name='pending_delete',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
