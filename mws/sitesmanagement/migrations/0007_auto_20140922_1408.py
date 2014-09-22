# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0006_site_ssh_users'),
    ]

    operations = [
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
