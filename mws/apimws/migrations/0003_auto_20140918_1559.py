# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0005_site_disabled'),
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
            field=models.ForeignKey(default=2, to='sitesmanagement.VirtualMachine'),
            preserve_default=False,
        ),
    ]
