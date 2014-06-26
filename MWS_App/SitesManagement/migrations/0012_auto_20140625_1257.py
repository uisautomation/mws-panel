# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('SitesManagement', '0011_auto_20140624_1544'),
    ]

    operations = [
        migrations.AlterField(
            model_name='domainname',
            name='site',
            field=models.ForeignKey(to='SitesManagement.Site', to_field='id'),
        ),
        migrations.AlterField(
            model_name='suspension',
            name='end_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
