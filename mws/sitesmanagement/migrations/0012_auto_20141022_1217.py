# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0011_auto_20141015_1629'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='ssh_users',
            field=models.ManyToManyField(related_name=b'sites_auth_as_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='site',
            field=models.ForeignKey(related_name=b'virtual_machines', to='sitesmanagement.Site', null=True),
        ),
    ]
