# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0030_auto_20150306_1047'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vhost',
            name='certificate',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='vhost',
            name='csr',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
