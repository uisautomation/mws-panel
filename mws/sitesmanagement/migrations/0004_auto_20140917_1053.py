# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0003_auto_20140903_1416'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vhost',
            name='site',
        ),
        migrations.AddField(
            model_name='vhost',
            name='vm',
            field=models.ForeignKey(related_name=b'vhosts', default=2, to='sitesmanagement.VirtualMachine'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'ansible', b'Running Ansible'), (b'ready', b'Ready')]),
        ),
    ]
