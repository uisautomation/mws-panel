# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0029_auto_20150305_1729'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='virtualmachine',
            name='primary',
        ),
        migrations.RemoveField(
            model_name='virtualmachine',
            name='status',
        ),
        migrations.AddField(
            model_name='service',
            name='status',
            field=models.CharField(default='ready', max_length=50, choices=[(b'requested', b'Requested'),
                                                                            (b'accepted', b'Accepted'),
                                                                            (b'denied', b'Denied'),
                                                                            (b'installing', b'Installing OS'),
                                                                            (b'ansible', b'Running Ansible'),
                                                                            (b'ansible_queued', b'Ansible queued'),
                                                                            (b'ready', b'Ready')]),
            preserve_default=False,
        ),
    ]
