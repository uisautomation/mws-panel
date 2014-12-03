# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0015_auto_20141105_1328'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='token',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
    ]
