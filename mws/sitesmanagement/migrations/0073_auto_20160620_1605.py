# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations


def add_tiers(apps, schema_editor):
    ServerType = apps.get_model("sitesmanagement", "ServerType")
    ServerType.objects.create(id=1, numcpu=1, sizeram=1, sizedisk=20, price=100.00)
    ServerType.objects.create(id=2, numcpu=1, sizeram=2, sizedisk=40, price=200.00)
    ServerType.objects.create(id=3, numcpu=1, sizeram=2, sizedisk=60, price=300.00)


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0072_auto_20160527_1449'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServerType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('numcpu', models.IntegerField()),
                ('sizeram', models.IntegerField()),
                ('sizedisk', models.IntegerField()),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(add_tiers),
        migrations.AddField(
            model_name='site',
            name='type',
            field=models.ForeignKey(default=1, to='sitesmanagement.ServerType'),
            preserve_default=False,
        ),
    ]
