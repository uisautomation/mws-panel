# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0032_vhost_tls_key_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='vhost',
            name='tls_enabled',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
