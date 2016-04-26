# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0062_auto_20160314_1017'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='days_without_admin',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
    ]
