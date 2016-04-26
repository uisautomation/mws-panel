# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0002_auto_20140917_1152'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ansibleconfiguration',
            name='vm',
            field=models.ForeignKey(related_name='ansible_configuration', to='sitesmanagement.VirtualMachine'),
            preserve_default=True,
        ),
    ]
