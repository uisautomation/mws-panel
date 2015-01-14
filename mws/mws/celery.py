from __future__ import absolute_import
from celery.schedules import crontab
from celery import Celery

# to launch the celery worker use the following command line:
# DJANGO_SETTINGS_MODULE='mws.(production_)settings' celery -A mws worker -l info

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
