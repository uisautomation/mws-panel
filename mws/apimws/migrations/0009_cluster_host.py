# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0008_phplibs'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cluster',
            fields=[
                ('name', models.CharField(max_length=100, serialize=False, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                ('hostname', models.CharField(max_length=250, serialize=False, primary_key=True)),
                ('cluster', models.ForeignKey(related_name='hosts', to='apimws.Cluster')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
