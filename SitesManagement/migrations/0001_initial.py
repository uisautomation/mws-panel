# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '__first__'),
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
                ('group', models.ManyToManyField(to='auth.Group', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
