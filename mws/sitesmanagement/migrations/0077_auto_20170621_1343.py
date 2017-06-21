# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0076_auto_20170327_1646'),
    ]

    operations = [
        migrations.AddField(
            model_name='vhost',
            name='certificate_chain',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
