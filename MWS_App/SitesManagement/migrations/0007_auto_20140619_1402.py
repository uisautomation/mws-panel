# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0006_virtualmachine'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='email',
            field=models.EmailField(max_length=75, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='domainname',
            name='site',
            field=models.ForeignKey(to_field='id', blank=True, to='SitesManagement.Site', null=True),
        ),
    ]
