# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0075_auto_20170224_1529'),
    ]

    operations = [
        migrations.AddField(
            model_name='servertype',
            name='order',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
