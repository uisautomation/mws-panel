# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siterequestdemo',
            name='date_submitted',
            field=models.DateTimeField(),
        ),
    ]
