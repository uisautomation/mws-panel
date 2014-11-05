# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0009_auto_20141024_0951'),
    ]

    operations = [
        migrations.AddField(
            model_name='vhost',
            name='certificate',
            field=models.TextField(null=True),
            #preserve_default=True,
        ),
        migrations.AddField(
            model_name='vhost',
            name='csr',
            field=models.TextField(null=True),
            #preserve_default=True,
        ),
        migrations.AlterField(
            model_name='domainname',
            name='status',
            field=models.CharField(default=b'requested', max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'to_be_deleted', b'Removing...')]),
            #preserve_default=True,
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'ansible', b'Running Ansible'), (b'ansible_queued', b'Ansible queued'), (b'ready', b'Ready')]),
            #preserve_default=True,
        ),
    ]
