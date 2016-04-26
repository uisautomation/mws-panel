# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0048_auto_20151103_1649'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SiteKeys',
            new_name='SiteKey',
        ),
        migrations.AlterUniqueTogether(
            name='sitekey',
            unique_together=set([('site', 'type')]),
        ),
    ]
