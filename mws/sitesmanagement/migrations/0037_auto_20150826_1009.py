# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0036_auto_20150706_1530'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailconfirmation',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='site',
            name='ssh_users',
            field=models.ManyToManyField(related_name='sites_auth_as_user', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name='vhost',
            name='name',
            field=models.CharField(max_length=150, validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
        ),
    ]
