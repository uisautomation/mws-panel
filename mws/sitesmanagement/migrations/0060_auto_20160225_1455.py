# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sitesmanagement.models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0059_auto_20160219_1536'),
    ]

    operations = [
        migrations.AddField(
            model_name='unixgroup',
            name='to_be_deleted',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='unixgroup',
            name='name',
            field=models.CharField(max_length=16, validators=[sitesmanagement.models.unix_group_name_validator]),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='unixgroup',
            unique_together=set([('name', 'service')]),
        ),
    ]
