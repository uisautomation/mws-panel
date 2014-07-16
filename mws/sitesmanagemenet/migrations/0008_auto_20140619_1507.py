# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0007_auto_20140619_1402'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainname',
            name='status',
            field=models.CharField(default='requested', max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'mws', b'mws domain ready to be assigned')]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='site',
            name='group',
            field=models.ManyToManyField(to='auth.Group', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='end_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
