# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import sitesmanagement.models


class Migration(migrations.Migration):

    replaces = [(b'sitesmanagement', '0001_initial'), (b'sitesmanagement', '0002_billing'), (b'sitesmanagement', '0003_domainname'), (b'sitesmanagement', '0004_networkconfig'), (b'sitesmanagement', '0005_suspension'), (b'sitesmanagement', '0006_virtualmachine'), (b'sitesmanagement', '0007_auto_20140619_1402'), (b'sitesmanagement', '0008_auto_20140619_1507'), (b'sitesmanagement', '0009_auto_20140623_1539'), (b'sitesmanagement', '0010_auto_20140624_0919'), (b'sitesmanagement', '0011_auto_20140624_1544'), (b'sitesmanagement', '0012_auto_20140625_1257'), (b'sitesmanagement', '0013_auto_20140627_1325'), (b'sitesmanagement', '0014_site_main_domain'), (b'sitesmanagement', '0015_auto_20140718_1409'), (b'sitesmanagement', '0016_auto_20140718_1629'), (b'sitesmanagement', '0017_auto_20140731_1549'), (b'sitesmanagement', '0002_auto_20140819_1804'), (b'sitesmanagement', '0003_auto_20140902_1214')]

    dependencies = [
        ('auth', '0001_initial'),
        ('ucamlookup', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('description', models.CharField(max_length=250, blank=True)),
                ('institution_id', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True)),
                ('deleted', models.BooleanField(default=False)),
                ('email', models.EmailField(max_length=75, null=True)),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('groups', models.ManyToManyField(to=b'auth.Group', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Billing',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('purchase_order', models.FileField(upload_to=b'billing')),
                ('group', models.CharField(max_length=250)),
                ('site', models.OneToOneField(to='sitesmanagement.Site', to_field='id')),
                ('purchase_order_number', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainName',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=250)),
                ('site', models.ForeignKey(to='sitesmanagement.Site', to_field='id', null=True)),
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
                ('main_domain', models.OneToOneField(to='sitesmanagement.DomainName', to_field='id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Suspension',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reason', models.CharField(max_length=250)),
                ('active', models.BooleanField(default=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True, blank=True)),
                ('site', models.ForeignKey(to='sitesmanagement.Site', to_field='id')),
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
                ('network_configuration', models.OneToOneField(to='sitesmanagement.NetworkConfig', to_field='id')),
                ('site', models.ForeignKey(to='sitesmanagement.Site', to_field='id')),
                ('status', models.CharField(max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied'), (b'ready', b'Ready')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='site',
            name='email',
            field=models.EmailField(max_length=75, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='domainname',
            name='site',
            field=models.ForeignKey(to_field='id', blank=True, to='sitesmanagement.Site', null=True),
        ),
        migrations.AddField(
            model_name='domainname',
            name='status',
            field=models.CharField(default=b'requested', max_length=50, choices=[(b'requested', b'Requested'), (b'accepted', b'Accepted'), (b'denied', b'Denied')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='site',
            name='end_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='mws_domain',
            field=models.CharField(default=None, unique=True, max_length=250),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='networkconfig',
            name='main_domain',
        ),
        migrations.AlterField(
            model_name='domainname',
            name='site',
            field=models.ForeignKey(to='sitesmanagement.Site', to_field='id'),
        ),
        migrations.AddField(
            model_name='site',
            name='main_domain',
            field=models.ForeignKey(blank=True, to='sitesmanagement.DomainName', null=True),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='EmailConfirmation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('token', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50, choices=[(b'pending', b'Pending'), (b'accepted', b'Accepted')])),
                ('site', models.ForeignKey(to='sitesmanagement.Site', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='networkconfig',
            name='SSHFP',
            field=models.CharField(max_length=250, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='site',
            name='groups',
            field=models.ManyToManyField(to=b'ucamlookup.LookupGroup', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='domainname',
            name='name',
            field=models.CharField(unique=True, max_length=250, validators=[sitesmanagement.models.full_domain_validator]),
        ),
    ]
