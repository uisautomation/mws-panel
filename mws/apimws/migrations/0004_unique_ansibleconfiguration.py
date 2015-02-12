# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def squash_duplicates(apps, schema_editor):
    """
    Delete all but the newest value of each AnsibleConfiguration variable.
    Newness is judged based on primary key value.
    """
    AnsibleConfiguration = apps.get_model('apimws', 'AnsibleConfiguration')
    for vm, key in (
            AnsibleConfiguration.objects.all().values_list('vm', 'key')
            .distinct()):
        print "vm=%s, key=%s" % (repr(vm), repr(key))
        for ac in (AnsibleConfiguration.objects.filter(vm=vm, key=key)
                   .order_by('-id')[1:]):
            print "deleting %s" % (repr(ac),)
            ac.delete()

def no_op(apps, schema_editor):
    """
    Backward migrations are a no-op: we can't create the lost duplicates,
    and they're probably useless anyway.
    """
    pass
        
class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0003_auto_20141117_1706'),
    ]

    operations = [
        migrations.RunPython(squash_duplicates, no_op),
        migrations.AlterUniqueTogether(
            name='ansibleconfiguration',
            unique_together=set([('vm', 'key')]),
        ),
    ]
