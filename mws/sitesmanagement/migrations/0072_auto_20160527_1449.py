# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations
from libs.sshpubkey import SSHPubKey


def process_fp_sha256(apps, schema_editor):
    SiteKey = apps.get_model("sitesmanagement", "SiteKey")
    for sitekey in SiteKey.objects.all():
        sitekey.fingerprint2 = SSHPubKey(sitekey.public_key).hash_sha256()
        sitekey.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0071_auto_20160509_1629'),
    ]

    operations = [
        migrations.AlterField(
            model_name='domainname',
            name='status',
            field=models.CharField(default=b'requested', max_length=50,
                                   choices=[(b'requested', b'Requested'),
                                            (b'accepted', b'Accepted'),
                                            (b'external', b'External'),
                                            (b'special', b'Special'),
                                            (b'denied', b'Denied')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='sitekey',
            name='fingerprint2',
            field=models.CharField(max_length=250, null=True),
            preserve_default=True,
        ),
        migrations.RunPython(process_fp_sha256),
    ]
