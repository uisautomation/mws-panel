# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0058_auto_20160121_1206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suspension',
            name='start_date',
            field=models.DateField(auto_now_add=True),
            preserve_default=True,
        ),
    ]
