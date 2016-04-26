# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0008_unixgroup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='unixgroup',
            name='vm',
            field=models.ForeignKey(related_name=b'unix_groups', to='sitesmanagement.VirtualMachine'),
        ),
    ]
