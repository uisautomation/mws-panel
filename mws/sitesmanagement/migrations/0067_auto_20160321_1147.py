# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0066_auto_20160317_1546'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainname',
            name='requested_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 3, 1, 1, 1, 1, 850544, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
