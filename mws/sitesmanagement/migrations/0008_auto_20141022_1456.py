# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0007_auto_20140930_1544'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='networkconfig',
            name='type',
        ),
        migrations.RemoveField(
            model_name='virtualmachine',
            name='network_configuration',
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='IPv4private',
            field=models.GenericIPAddressField(default='172.28.18.255', unique=True, protocol=b'IPv4'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='mws_private_domain',
            field=models.CharField(default='mws-7611011.mws3.csx.private.cam.ac.uk', unique=True, max_length=250),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='site',
            name='network_configuration',
            field=models.OneToOneField(related_name=b'site', default=1, to='sitesmanagement.NetworkConfig'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='networkconfig',
            name='IPv4',
            field=models.GenericIPAddressField(unique=True, protocol=b'IPv4'),
        ),
        migrations.AlterField(
            model_name='networkconfig',
            name='IPv6',
            field=models.GenericIPAddressField(unique=True, protocol=b'IPv6'),
        ),
        migrations.AlterField(
            model_name='site',
            name='ssh_users',
            field=models.ManyToManyField(related_name=b'sites_auth_as_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='vhost',
            name='main_domain',
            field=models.ForeignKey(related_name=b'+', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='sitesmanagement.DomainName', null=True),
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='site',
            field=models.ForeignKey(related_name=b'virtual_machines', to='sitesmanagement.Site', null=True),
        ),
    ]
