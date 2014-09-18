# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ansibleconfiguration',
            name='site',
        ),
        migrations.AddField(
            model_name='ansibleconfiguration',
            name='vm',
            field=models.ForeignKey(default=1, to='sitesmanagement.VirtualMachine'),
            preserve_default=False,
        ),
    ]
