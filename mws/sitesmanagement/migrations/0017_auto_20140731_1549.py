# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0016_auto_20140718_1629'),
    ]

    operations = [
        migrations.AddField(
            model_name='networkconfig',
            name='SSHFP',
            field=models.CharField(max_length=250, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='domainname',
            name='status',
            field=models.CharField(default=b'requested', max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied')]),
        ),
        migrations.AlterField(
            model_name='emailconfirmation',
            name='site',
            field=models.ForeignKey(to='sitesmanagement.Site', unique=True),
        ),
    ]
