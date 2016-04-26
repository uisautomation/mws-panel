# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0009_auto_20141009_1433'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='networkconfig',
            name='type',
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='IPv4private',
            field=models.GenericIPAddressField(default='172.28.18.1', protocol=b'IPv4'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='mws_private_domain',
            field=models.CharField(default='mws-76110.mws3.csx.private.cam.ac.uk', unique=True, max_length=250),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='vhost',
            name='main_domain',
            field=models.ForeignKey(related_name=b'+', on_delete=django.db.models.deletion.SET_NULL, blank=True,
                                    to='sitesmanagement.DomainName', null=True),
        ),
    ]
