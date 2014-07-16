# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Billing',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('purchase_order', models.FileField(upload_to=b'')),
                ('group', models.CharField(max_length=250)),
                ('site', models.OneToOneField(to='SitesManagement.Site', to_field='id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
