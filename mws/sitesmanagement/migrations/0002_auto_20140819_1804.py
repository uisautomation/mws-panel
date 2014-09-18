# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0001_squashed_0017_auto_20140731_1549'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billing',
            name='purchase_order_number',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='site',
            name='groups',
            field=models.ManyToManyField(to=b'ucamlookup.LookupGroup', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='status',
            field=models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'ready', b'Ready')]),
        ),
    ]
