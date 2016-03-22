# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations


def add_mws_cluster_1(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Cluster = apps.get_model("apimws", "Cluster")
    Host = apps.get_model("apimws", "Host")
    cluster1 = Cluster.objects.create(name="mws-cluster-1")
    host1 = Host.objects.create(hostname="agogue.csi.cam.ac.uk", cluster=cluster1)
    host2 = Host.objects.create(hostname="odochium.csi.cam.ac.uk", cluster=cluster1)


class Migration(migrations.Migration):

    dependencies = [
        ('apimws', '0008_phplibs'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cluster',
            fields=[
                ('name', models.CharField(max_length=100, serialize=False, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                ('hostname', models.CharField(max_length=250, serialize=False, primary_key=True)),
                ('cluster', models.ForeignKey(related_name='hosts', to='apimws.Cluster')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(add_mws_cluster_1),
    ]
