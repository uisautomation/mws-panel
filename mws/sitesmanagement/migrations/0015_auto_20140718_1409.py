# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0014_site_main_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='billing',
            name='purchase_order_number',
            field=models.CharField(default=None, max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='billing',
            name='purchase_order',
            field=models.FileField(upload_to=b'/Users/amc203/Development/PycharmProjects/MWS/mws/media'),
        ),
    ]
