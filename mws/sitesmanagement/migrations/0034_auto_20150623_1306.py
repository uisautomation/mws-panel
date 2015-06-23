# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0033_vhost_tls_enabled'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='site',
            options={'ordering': ['-id']},
        ),
    ]
