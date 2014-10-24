# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0013_site_ssh_groups'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='email',
            field=models.EmailField(max_length=75),
        ),
    ]
