# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-02-04 11:40
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def migrate_package_names(apps, schema_editor):
    def add_package(lib, os):
        pkg = PHPPackage()
        pkg.name = lib.name_next_os if os == 'stretch' else lib.name
        pkg.os = os
        library = lib
        pkg.save()
    packages = []
    PHPPackage = apps.get_model('apimws','PHPPackage')
    PHPLib = apps.get_model('apimws','PHPLib')
    for lib in PHPLib.objects.all():
        if lib.name_next_os and (lib.name_next_os, 'stretch') not in packages:
            packages.append((lib.name_next_os, 'stretch'))
            add_package(lib, 'stretch')
        if lib.name and (lib.name, 'jessie') not in packages:
            packages.append((lib.name, 'jessie'))
            add_package(lib, 'jessie')

class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0012_auto_20190204_0918'),
    ]

    operations = [
        migrations.CreateModel(
            name='PHPPackage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('os', models.CharField(choices=[(b'jessie', b'Debian 8 (jessie)'), (b'stretch', b'Debian 9 (stretch)')], max_length=40)),
                ('library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='packages', to='apimws.PHPLib')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='phppackage',
            unique_together=set([('name', 'os')]),
        ),
        migrations.RunPython(migrate_package_names),
    ]
