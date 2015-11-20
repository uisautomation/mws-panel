# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sitesmanagement', '0050_auto_20151120_1343'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainname',
            name='authorised_by',
            field=models.ForeignKey(related_name='domain_names_authorised', blank=True,
                                    to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='domainname',
            name='token',
            field=models.CharField(default=uuid.uuid4, max_length=50),
            preserve_default=True,
        ),
    ]
