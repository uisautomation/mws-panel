# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sitesmanagement', '0067_auto_20160321_1147'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='supporters',
            field=models.ManyToManyField(related_name='sites_auth_as_supporter', to=settings.AUTH_USER_MODEL,
                                         blank=True),
            preserve_default=True,
        ),
    ]
