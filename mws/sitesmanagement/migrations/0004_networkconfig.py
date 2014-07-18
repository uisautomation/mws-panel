# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0003_domainname'),
    ]

    operations = [
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
    ]
