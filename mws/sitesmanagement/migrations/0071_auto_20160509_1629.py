# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0070_auto_20160404_0943'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='site',
            name='exmws2',
        ),
        migrations.AddField(
            model_name='site',
            name='exmws2',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
    ]

