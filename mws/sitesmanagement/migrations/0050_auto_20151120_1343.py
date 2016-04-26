# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sitesmanagement', '0049_auto_20151113_1545'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainname',
            name='reject_reason',
            field=models.CharField(max_length=250, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='domainname',
            name='requested_by',
            field=models.ForeignKey(related_name='domain_names_requested', blank=True,
                                    to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='domainname',
            name='status',
            field=models.CharField(default=b'requested', max_length=50,
                                   choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'),
                                            (b'external', b'External'), (b'denied', b'Denied')]),
            preserve_default=True,
        ),
    ]
