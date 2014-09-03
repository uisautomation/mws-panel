# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import sitesmanagement.models


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0002_auto_20140819_1804'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vhost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250)),
                ('main_domain', models.ForeignKey(related_name=b'+', blank=True, to='sitesmanagement.DomainName', null=True)),
                ('site', models.ForeignKey(related_name=b'vhosts', to='sitesmanagement.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='domainname',
            name='site',
        ),
        migrations.RemoveField(
            model_name='site',
            name='main_domain',
        ),
        migrations.AddField(
            model_name='domainname',
            name='vhost',
            field=models.ForeignKey(related_name=b'domain_names', default='', to='sitesmanagement.Vhost'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='billing',
            name='site',
            field=models.OneToOneField(related_name=b'billing', to='sitesmanagement.Site'),
        ),
        migrations.AlterField(
            model_name='domainname',
            name='name',
            field=models.CharField(unique=True, max_length=250, validators=[sitesmanagement.models.full_domain_validator]),
        ),
        migrations.AlterField(
            model_name='emailconfirmation',
            name='site',
            field=models.ForeignKey(related_name=b'+', to='sitesmanagement.Site', unique=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='groups',
            field=models.ManyToManyField(related_name=b'sites', null=True, to=b'ucamlookup.LookupGroup', blank=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='users',
            field=models.ManyToManyField(related_name=b'sites', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='suspension',
            name='site',
            field=models.ForeignKey(related_name=b'suspensions', to='sitesmanagement.Site'),
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='network_configuration',
            field=models.OneToOneField(related_name=b'virtual_machine', to='sitesmanagement.NetworkConfig'),
        ),
        migrations.AlterField(
            model_name='virtualmachine',
            name='site',
            field=models.ForeignKey(related_name=b'virtual_machines', to='sitesmanagement.Site'),
        ),
    ]
