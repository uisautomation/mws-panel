# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0052_auto_20151124_1530'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vhost',
            name='name',
            field=models.CharField(max_length=60, validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
            preserve_default=True,
        ),
    ]
