# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0063_auto_20160314_1630'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='exmws2',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
