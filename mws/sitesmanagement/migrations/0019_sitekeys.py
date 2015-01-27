# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0018_auto_20150126_1716'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteKeys',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=100)),
                ('public_key', models.TextField()),
                ('fingerprint', models.CharField(max_length=250, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
