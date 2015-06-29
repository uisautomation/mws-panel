# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('mwsauth', '0002_auto_20141023_1754'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mwsuser',
            name='user',
            field=models.OneToOneField(related_name='mws_user', db_constraint=False, to_field=b'username',
                                       to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
