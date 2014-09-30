# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sitesmanagement', '0006_site_ssh_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnixGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=16)),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('vm', models.ForeignKey(related_name=b'unix_groups', to='sitesmanagement.VirtualMachine')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='type',
            field=models.CharField(default='public', max_length=10, choices=[(b'public', b'Public'), (b'private', b'Private')]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='networkconfig',
            name='IPv6',
            field=models.GenericIPAddressField(null=True, protocol=b'IPv6', blank=True),
        ),
    ]
