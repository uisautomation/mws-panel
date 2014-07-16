# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sitesmanagement', '0009_auto_20140623_1539'),
    ]

    operations = [
        migrations.RenameField(
            model_name='site',
            old_name='group',
            new_name='groups',
        ),
    ]
