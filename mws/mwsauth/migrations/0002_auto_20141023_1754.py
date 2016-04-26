# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('mwsauth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mwsuser',
            name='uid',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='mwsuser',
            name='user',
            field=models.OneToOneField(related_name=b'mws_user', to_field=b'username', to=settings.AUTH_USER_MODEL),
        ),
    ]
