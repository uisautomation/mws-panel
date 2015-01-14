from __future__ import absolute_import
from celery.schedules import crontab
from celery import Celery
import os

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mws.production_settings')

app = Celery('mws')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
#app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

CELERYBEAT_SCHEDULE = {
    'add-every-night': {
        'task': 'apimws.jackdaw.jackdaw_api',
        'schedule': crontab(hour=2, minute=30),
        'args': ()
    },
}
