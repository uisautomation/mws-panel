# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0008_auto_20140619_1507'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='status',
            field=models.CharField(default='ready', max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'ready', b'Ready')]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='domainname',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'mws', b'mws*.cam.ac.uk domain ready to be assigned')]),
        ),
    ]
