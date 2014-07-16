# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0010_auto_20140624_0919'),
    ]

    operations = [
        migrations.AddField(
            model_name='networkconfig',
            name='mws_domain',
            field=models.CharField(default=None, unique=True, max_length=250),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='networkconfig',
            name='main_domain',
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='name',
            field=models.CharField(unique=True, max_length=250),
        ),
        migrations.AlterField(
            model_name='domainname',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied')]),
        ),
    ]
