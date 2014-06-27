# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('SitesManagement', '0013_auto_20140627_1325'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='main_domain',
            field=models.ForeignKey(blank=True, to='SitesManagement.DomainName', null=True),
            preserve_default=True,
        ),
    ]
