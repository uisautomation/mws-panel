# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0051_auto_20151120_1425'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='site',
            field=models.ForeignKey(related_name='services', blank=True, to='sitesmanagement.Site', null=True),
            preserve_default=True,
        ),
    ]
