# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0037_auto_20150826_1009'),
    ]

    operations = [
        migrations.CreateModel(
            name='Snapshot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('service', models.ForeignKey(related_name='snapshots', to='sitesmanagement.Service')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='snapshot',
            unique_together=set([('name', 'service')]),
        ),
    ]
