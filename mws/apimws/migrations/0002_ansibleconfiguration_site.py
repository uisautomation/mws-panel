# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0001_initial'),
        ('sitesmanagement', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ansibleconfiguration',
            name='site',
            field=models.ForeignKey(to='sitesmanagement.Site'),
            preserve_default=True,
        ),
    ]
