# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0005_suspension'),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualMachine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250)),
                ('primary', models.BooleanField(default=True)),
                ('network_configuration', models.OneToOneField(to='sitesmanagement.NetworkConfig', to_field='id')),
                ('site', models.ForeignKey(to='sitesmanagement.Site', to_field='id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
