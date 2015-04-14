# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0031_auto_20150319_1438'),
    ]

    operations = [
        migrations.AddField(
            model_name='vhost',
            name='tls_key_hash',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
