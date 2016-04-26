# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0065_auto_20160316_1223'),
    ]

    operations = [
        migrations.AddField(
            model_name='vhost',
            name='apache_owned',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
