# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0043_auto_20151014_1118'),
    ]

    operations = [
        migrations.AddField(
            model_name='billing',
            name='date_created',
            field=models.DateTimeField(default=datetime.datetime(2015, 10, 14, 10, 35, 12, 590932, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='billing',
            name='date_modified',
            field=models.DateField(default=datetime.datetime(2015, 10, 14, 10, 35, 14, 919620, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
