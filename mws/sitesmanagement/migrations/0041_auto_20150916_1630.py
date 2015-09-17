# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import sitesmanagement.models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0040_auto_20150908_1343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='snapshot',
            name='name',
            field=models.CharField(max_length=50, validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid'), sitesmanagement.models.no_date_validator]),
        ),
    ]
