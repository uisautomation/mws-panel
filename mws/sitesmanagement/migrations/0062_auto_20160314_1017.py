# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0061_auto_20160309_0922'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='email',
            field=models.EmailField(max_length=75),
            preserve_default=True,
        ),
    ]
