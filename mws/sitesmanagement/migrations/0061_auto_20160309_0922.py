# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0060_auto_20160225_1455'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='suspension',
            name='active',
        ),
    ]
