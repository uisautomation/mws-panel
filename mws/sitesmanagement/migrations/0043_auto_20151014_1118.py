# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0042_vhost_webapp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailconfirmation',
            name='site',
            field=models.OneToOneField(related_name='+', to='sitesmanagement.Site'),
        ),
        migrations.AlterField(
            model_name='site',
            name='groups',
            field=models.ManyToManyField(related_name='sites', to='ucamlookup.LookupGroup', blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='ssh_groups',
            field=models.ManyToManyField(related_name='sites_auth_as_user', to='ucamlookup.LookupGroup', blank=True),
        ),
    ]
