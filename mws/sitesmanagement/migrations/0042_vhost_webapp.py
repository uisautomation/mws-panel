# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0041_auto_20150916_1630'),
    ]

    operations = [
        migrations.AddField(
            model_name='vhost',
            name='webapp',
            field=models.CharField(blank=True, max_length=100, null=True, choices=[(b'wordpress', b'Wordpress')]),
        ),
    ]
