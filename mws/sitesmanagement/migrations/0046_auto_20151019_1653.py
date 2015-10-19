# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sitesmanagement.models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0045_auto_20151014_1709'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billing',
            name='purchase_order',
            field=models.FileField(upload_to=b'billing', validators=[sitesmanagement.models.validate_file_extension]),
            preserve_default=True,
        ),
    ]
