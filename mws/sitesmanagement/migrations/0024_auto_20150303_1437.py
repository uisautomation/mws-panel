# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0023_auto_20150302_1751'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=50, choices=[(b'production', b'Production'), (b'test', b'Test')])),
                ('network_configuration', models.OneToOneField(to='sitesmanagement.NetworkConfig')),
                ('site', models.ForeignKey(to='sitesmanagement.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='service',
            unique_together=set([('site', 'type')]),
        ),
        migrations.AddField(
            model_name='virtualmachine',
            name='service',
            field=models.ForeignKey(to='sitesmanagement.Service', null=True),
            preserve_default=True,
        ),
    ]
