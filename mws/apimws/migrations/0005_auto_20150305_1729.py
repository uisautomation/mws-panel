# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def vm_to_service(apps, schema_editor):
    """
    AnsibleConfiguration now depends from Service instead of VirtualMachine
    """
    AnsibleConfiguration = apps.get_model('apimws', 'AnsibleConfiguration')
    for ansibleconfiguration in AnsibleConfiguration.objects.all():
        ansibleconfiguration.service = ansibleconfiguration.vm.service
        ansibleconfiguration.save()


def vm_to_service_reverse(apps, schema_editor):
    """
    Reverse to vm_to_service
    """
    AnsibleConfiguration = apps.get_model('apimws', 'AnsibleConfiguration')
    for ansibleconfiguration in AnsibleConfiguration.objects.all():
        ansibleconfiguration.vm = ansibleconfiguration.service.virtual_machines.first()
        ansibleconfiguration.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0029_auto_20150305_1729'),
        ('apimws', '0004_unique_ansibleconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='ansibleconfiguration',
            name='service',
            field=models.ForeignKey(related_name='ansible_configuration', null=True, blank=True,
                                    to='sitesmanagement.Service'),
            preserve_default=False,
        ),
        migrations.RunPython(vm_to_service, vm_to_service_reverse),
        migrations.AlterField(
            model_name='ansibleconfiguration',
            name='service',
            field=models.ForeignKey(related_name='ansible_configuration', to='sitesmanagement.Service'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='ansibleconfiguration',
            unique_together=set([('service', 'key')]),
        ),
        migrations.RemoveField(
            model_name='ansibleconfiguration',
            name='vm',
        ),
    ]
