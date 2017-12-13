# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0009_cluster_host'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apachemodule',
            name='services',
        ),
        migrations.DeleteModel(
            name='ApacheModule',
        ),
    ]
