# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sitesmanagement', '0007_auto_20140922_1408'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnixGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=16)),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('vm', models.ForeignKey(to='sitesmanagement.VirtualMachine')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
