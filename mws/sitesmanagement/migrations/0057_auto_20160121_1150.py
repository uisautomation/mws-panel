# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0056_auto_20160120_1706'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='start_date',
            field=models.DateField(auto_now_add=True, null=True),
            preserve_default=True,
        ),
    ]
