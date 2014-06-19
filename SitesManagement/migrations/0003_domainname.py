# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('SitesManagement', '0002_billing'),
    ]

    operations = [
        migrations.CreateModel(
            name='DomainName',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=250)),
                ('site', models.ForeignKey(to='SitesManagement.Site', to_field='id', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
