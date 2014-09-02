# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sitesmanagement.models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0002_auto_20140819_1804'),
    ]

    operations = [
        migrations.AlterField(
            model_name='domainname',
            name='name',
            field=models.CharField(unique=True, max_length=250, validators=[sitesmanagement.models.full_domain_validator]),
        ),
    ]
