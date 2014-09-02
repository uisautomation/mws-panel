# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import sitesmanagement.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ucamlookup', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Billing',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('purchase_order_number', models.CharField(max_length=100)),
                ('purchase_order', models.FileField(upload_to=b'billing')),
                ('group', models.CharField(max_length=250)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainName',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=250, validators=[sitesmanagement.models.full_domain_validator])),
                ('status', models.CharField(default=b'requested', max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailConfirmation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('token', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50, choices=[(b'pending', b'Pending'), (b'accepted', b'Accepted')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NetworkConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('IPv4', models.GenericIPAddressField(protocol=b'IPv4')),
                ('IPv6', models.GenericIPAddressField(protocol=b'IPv6')),
                ('SSHFP', models.CharField(max_length=250, null=True, blank=True)),
                ('mws_domain', models.CharField(unique=True, max_length=250)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('description', models.CharField(max_length=250, blank=True)),
                ('institution_id', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True, blank=True)),
                ('deleted', models.BooleanField(default=False)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('groups', models.ManyToManyField(to='ucamlookup.LookupGroup', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='emailconfirmation',
            name='site',
            field=models.ForeignKey(to='sitesmanagement.Site', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='domainname',
            name='site',
            field=models.ForeignKey(to='sitesmanagement.Site'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='billing',
            name='site',
            field=models.OneToOneField(to='sitesmanagement.Site'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='site',
            name='main_domain',
            field=models.ForeignKey(blank=True, to='sitesmanagement.DomainName', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='site',
            name='users',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Suspension',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reason', models.CharField(max_length=250)),
                ('active', models.BooleanField(default=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True, blank=True)),
                ('site', models.ForeignKey(to='sitesmanagement.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VirtualMachine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250, null=True, blank=True)),
                ('primary', models.BooleanField(default=True)),
                ('status', models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'ready', b'Ready')])),
                ('network_configuration', models.OneToOneField(to='sitesmanagement.NetworkConfig')),
                ('site', models.ForeignKey(to='sitesmanagement.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
