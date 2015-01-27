# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0018_auto_20150126_1716'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostNetworkConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('IPv6', models.GenericIPAddressField(unique=True, protocol=b'IPv6')),
                ('hostname', models.CharField(unique=True, max_length=250)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SiteKeys',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=100)),
                ('public_key', models.TextField()),
                ('fingerprint', models.CharField(max_length=250, null=True)),
                ('site', models.ForeignKey(related_name='keys', to='sitesmanagement.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='virtualmachine',
            name='host_network_configuration',
            field=models.OneToOneField(related_name='vm', default=0, to='sitesmanagement.HostNetworkConfig'),
            preserve_default=False,
        ),
    ]
