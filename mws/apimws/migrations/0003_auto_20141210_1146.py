# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0011_auto_20141210_1146'),
        ('apimws', '0002_ansibleconfiguration_site'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ansibleconfiguration',
            name='site',
        ),
        migrations.AddField(
            model_name='ansibleconfiguration',
            name='vm',
            field=models.ForeignKey(related_name='ansible_configuration', default=1, to='sitesmanagement.VirtualMachine'),
        ),
    ]
