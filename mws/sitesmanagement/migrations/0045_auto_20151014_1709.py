# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0044_auto_20151014_1135'),
    ]

    operations = [
        migrations.AddField(
            model_name='billing',
            name='date_sent_to_finance',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='billing',
            name='date_created',
            field=models.DateField(auto_now_add=True),
        ),
    ]
