# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0004_networkconfig'),
    ]

    operations = [
        migrations.CreateModel(
            name='Suspension',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reason', models.CharField(max_length=250)),
                ('active', models.BooleanField(default=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True)),
                ('site', models.ForeignKey(to='SitesManagement.Site', to_field='id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
