# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def modifytiers(apps, schema_editor):
    ServerType = apps.get_model("sitesmanagement", "ServerType")
    ServerType.objects.filter(id=1).update(preallocated=10)


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0073_auto_20160620_1605'),
    ]

    operations = [
        migrations.AddField(
            model_name='servertype',
            name='preallocated',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
        migrations.RunPython(modifytiers),
    ]
