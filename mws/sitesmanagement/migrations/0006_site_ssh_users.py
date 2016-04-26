# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sitesmanagement', '0005_site_disabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='ssh_users',
            field=models.ManyToManyField(related_name=b'+', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
