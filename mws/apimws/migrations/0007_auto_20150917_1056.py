# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0006_apachemodules'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apachemodules',
            name='services',
            field=models.ManyToManyField(related_name='apache_modules', to='sitesmanagement.Service', blank=True),
        ),
    ]
