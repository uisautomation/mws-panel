# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def vm_to_service(apps, schema_editor):
    """
    Vhost and UnixGroup now depend from Service instead of VirtualMachine
    """
    UnixGroup = apps.get_model('sitesmanagement', 'UnixGroup')
    Vhost = apps.get_model('sitesmanagement', 'Vhost')
    for unixgroup in UnixGroup.objects.all():
        unixgroup.service = unixgroup.vm.service
        unixgroup.save()
    for vhost in Vhost.objects.all():
        vhost.service = vhost.vm.service
        vhost.save()


def vm_to_service_reverse(apps, schema_editor):
    """
    Reverse to vm_to_service
    """
    UnixGroup = apps.get_model('sitesmanagement', 'UnixGroup')
    Vhost = apps.get_model('sitesmanagement', 'Vhost')
    for unixgroup in UnixGroup.objects.all():
        unixgroup.vm = unixgroup.service.virtual_machines.first()
        unixgroup.save()
    for vhost in Vhost.objects.all():
        vhost.vm = vhost.service.virtual_machines.first()
        vhost.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0028_auto_20150305_1643'),
    ]

    operations = [
        migrations.AddField(
            model_name='unixgroup',
            name='service',
            field=models.ForeignKey(related_name='unix_groups', null=True, blank=True, to='sitesmanagement.Service'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='vhost',
            name='service',
            field=models.ForeignKey(related_name='vhosts', null=True, blank=True, to='sitesmanagement.Service'),
            preserve_default=False,
        ),
        migrations.RunPython(vm_to_service, vm_to_service_reverse),
        migrations.AlterField(
            model_name='unixgroup',
            name='service',
            field=models.ForeignKey(related_name='unix_groups', to='sitesmanagement.Service'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='vhost',
            name='service',
            field=models.ForeignKey(related_name='vhosts', to='sitesmanagement.Service'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='unixgroup',
            name='vm',
        ),
        migrations.RemoveField(
            model_name='vhost',
            name='vm',
        ),
    ]
