# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-02-04 09:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0080_new_DomainName_states'),
    ]

    operations = [
        migrations.AlterField(
            model_name='virtualmachine',
            name='numcpu',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='sizeram',
            field=models.IntegerField(),
        ),
    ]
