# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations


def add_standard_storage_description(apps, schema_editor):
    ServerType = apps.get_model("sitesmanagement", "ServerType")
    ServerType.objects.update_or_create(id=1,
        defaults={
            'numcpu': 1,
            'sizeram': 1,
            'sizedisk': 20,
            'preallocated': 3,
            'price': 100.00,
            'description': "Standard"
        },)


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0074_auto_20160621_0946'),
    ]

    operations = [
        migrations.AddField(
            model_name='servertype',
            name='description',
            field=models.CharField(max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.RunPython(add_standard_storage_description),
    ]
