# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ucamlookup', '0001_initial'),
        ('sitesmanagement', '0012_auto_20141022_1217'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='ssh_groups',
            field=models.ManyToManyField(related_name=b'sites_auth_as_user', null=True, to='ucamlookup.LookupGroup',
                                         blank=True),
            preserve_default=True,
        ),
    ]
