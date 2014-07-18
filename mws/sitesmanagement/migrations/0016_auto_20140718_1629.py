# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0015_auto_20140718_1409'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailConfirmation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('token', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50, choices=[(b'pending', b'Pending'), (b'accepted', b'Accepted')])),
                ('site', models.ForeignKey(to='sitesmanagement.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='billing',
            name='purchase_order',
            field=models.FileField(upload_to=b'billing'),
        ),
    ]
