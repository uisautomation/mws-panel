# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def new_status(apps, schema_editor):
    Site = apps.get_model('sitesmanagement', 'Site')
    for site in Site.objects.all():
        if site.disabled:
            site.status = 'disabled'
            site.save()
        if site.deleted:
            site.status = 'deleted'
            site.save()


def new_status_reverse(apps, schema_editor):
    Site = apps.get_model('sitesmanagement', 'Site')
    for site in Site.objects.all():
        site.disabled = site.status == 'disabled'
        site.deleted = site.status == 'deleted'
        site.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0053_auto_20151126_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='status',
            field=models.CharField(default=b'normal', max_length=50,
                                   choices=[(b'normal', b'Normal'), (b'deleted', b'Deleted'),
                                            (b'disabled', b'Disabled')]),
            preserve_default=True,
        ),
        migrations.RunPython(new_status, new_status_reverse),
        migrations.RemoveField(
            model_name='site',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='site',
            name='disabled',
        ),
    ]
