# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0009_cluster_host'),
        ('sitesmanagement', '0068_auto_20160321_1406'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='cluster',
            field=models.ForeignKey(related_name='guests', default='mws-cluster-1', to='apimws.Cluster'),
            preserve_default=False,
        ),
    ]
