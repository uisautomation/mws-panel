# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import re
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0019_auto_20150127_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vhost',
            name='name',
            field=models.CharField(max_length=150, validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+$'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
            preserve_default=True,
        ),
    ]
