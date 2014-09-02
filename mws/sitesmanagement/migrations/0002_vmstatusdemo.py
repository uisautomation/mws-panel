# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VMStatusDemo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'on', max_length=50, choices=[(b'off', b'Off'), (b'on', b'On')])),
                ('vm', models.OneToOneField(to='sitesmanagement.VirtualMachine')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
