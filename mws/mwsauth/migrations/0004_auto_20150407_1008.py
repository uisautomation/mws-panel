# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mwsauth', '0003_auto_20150319_1215'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mwsuser',
            name='ssh_public_key',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
