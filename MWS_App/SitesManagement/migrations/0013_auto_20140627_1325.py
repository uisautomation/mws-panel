# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0012_auto_20140625_1257'),
    ]

    operations = [
        migrations.AlterField(
            model_name='virtualmachine',
            name='name',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
    ]
