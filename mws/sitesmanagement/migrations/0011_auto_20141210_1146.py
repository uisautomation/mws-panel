# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0010_auto_20141105_1511'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='token',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'installing', b'Installing OS'), (b'ansible', b'Running Ansible'), (b'ansible_queued', b'Ansible queued'), (b'ready', b'Ready')]),
            preserve_default=True,
        ),
    ]
