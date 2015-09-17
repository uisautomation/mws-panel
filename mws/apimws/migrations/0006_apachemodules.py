# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0041_auto_20150916_1630'),
        ('apimws', '0005_auto_20150305_1729'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApacheModule',
            fields=[
                ('name', models.CharField(max_length=150, serialize=False, primary_key=True)),
                ('description', models.CharField(max_length=250)),
                ('available', models.BooleanField(default=True)),
                ('services', models.ManyToManyField(related_name='apache_modules', to='sitesmanagement.Service')),
            ],
        ),
    ]
