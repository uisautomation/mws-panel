# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0057_auto_20160121_1150'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='start_date',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
