from __future__ import absolute_import
from datetime import timedelta
from celery.schedules import crontab
from mws.common_settings import *
# This file is generated when deploying
from mws.production_secrets import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ADMINS = (('automation', 'automation@uis.cam.ac.uk'), )
SERVER_EMAIL = "mws-support+test@uis.cam.ac.uk"

# ucamwebauth configuration
UCAMWEBAUTH_LOGIN_URL = 'https://raven.cam.ac.uk/auth/authenticate.html'
UCAMWEBAUTH_LOGOUT_URL = 'https://raven.cam.ac.uk/auth/logout.html'
UCAMWEBAUTH_CERTS = {2: """
-----BEGIN CERTIFICATE-----
MIIDrTCCAxagAwIBAgIBADANBgkqhkiG9w0BAQQFADCBnDELMAkGA1UEBhMCR0Ix
EDAOBgNVBAgTB0VuZ2xhbmQxEjAQBgNVBAcTCUNhbWJyaWRnZTEgMB4GA1UEChMX
VW5pdmVyc2l0eSBvZiBDYW1icmlkZ2UxKDAmBgNVBAsTH0NvbXB1dGluZyBTZXJ2
aWNlIFJhdmVuIFNlcnZpY2UxGzAZBgNVBAMTElJhdmVuIHB1YmxpYyBrZXkgMjAe
Fw0wNDA4MTAxMzM1MjNaFw0wNDA5MDkxMzM1MjNaMIGcMQswCQYDVQQGEwJHQjEQ
MA4GA1UECBMHRW5nbGFuZDESMBAGA1UEBxMJQ2FtYnJpZGdlMSAwHgYDVQQKExdV
bml2ZXJzaXR5IG9mIENhbWJyaWRnZTEoMCYGA1UECxMfQ29tcHV0aW5nIFNlcnZp
Y2UgUmF2ZW4gU2VydmljZTEbMBkGA1UEAxMSUmF2ZW4gcHVibGljIGtleSAyMIGf
MA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/9qcAW1XCSk0RfAfiulvTouMZKD4j
m99rXtMIcO2bn+3ExQpObbwWugiO8DNEffS7bzSxZqGp7U6bPdi4xfX76wgWGQ6q
Wi55OXJV0oSiqrd3aOEspKmJKuupKXONo2efAt6JkdHVH0O6O8k5LVap6w4y1W/T
/ry4QH7khRxWtQIDAQABo4H8MIH5MB0GA1UdDgQWBBRfhSRqVtJoL0IfzrSh8dv/
CNl16TCByQYDVR0jBIHBMIG+gBRfhSRqVtJoL0IfzrSh8dv/CNl16aGBoqSBnzCB
nDELMAkGA1UEBhMCR0IxEDAOBgNVBAgTB0VuZ2xhbmQxEjAQBgNVBAcTCUNhbWJy
aWRnZTEgMB4GA1UEChMXVW5pdmVyc2l0eSBvZiBDYW1icmlkZ2UxKDAmBgNVBAsT
H0NvbXB1dGluZyBTZXJ2aWNlIFJhdmVuIFNlcnZpY2UxGzAZBgNVBAMTElJhdmVu
IHB1YmxpYyBrZXkgMoIBADAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBAUAA4GB
AFciErbr6zl5i7ClrpXKA2O2lDzvHTFM8A3rumiOeauckbngNqIBiCRemYapZzGc
W7fgOEEsI4FoLOjQbJgIrgdYR2NIJh6pKKEf+9Ts2q/fuWv2xOLw7w29PIICeFIF
hAM+a6/30F5fdkWpE1smPyrfASyXRfWE4Ccn1RVgYX9u
-----END CERTIFICATE-----
"""}

BROKER_URL = 'redis://localhost:6379/0'
CELERYD_TASK_SOFT_TIME_LIMIT = 4*60*60  # 4 hours
CELERYD_TASK_TIME_LIMIT = 5*60*60  # 5 hours
CELERYBEAT_SCHEDULE = {
    'jackdaw-api': {
        'task': 'apimws.jackdaw.jackdaw_api',
        'schedule': timedelta(hours=1, minutes=3),
        'args': ()
    },
    'delete_cancelled': {
        'task': 'sitesmanagement.cronjobs.delete_cancelled',
        'schedule': crontab(hour=0, minute=5),
        'args': ()
    },
    'check_num_preallocated_sites': {
        'task': 'sitesmanagement.cronjobs.check_num_preallocated_sites',
        'schedule': timedelta(minutes=15),
        'args': ()
    },
    'validate_domains': {
        'task': 'sitesmanagement.cronjobs.validate_domains',
        'schedule': crontab(hour=0, minute=55),
        'args': ()
    },
    'expire_domains': {
        'task': 'sitesmanagement.cronjobs.expire_domains',
        'schedule': crontab(hour=1, minute=5),
        'args': ()
    },
}

MIDDLEWARE_CLASSES += (
    'mwsauth.middleware.CheckBannedUsers',
)

VM_END_POINT_COMMAND = ["userv", "mws-admin", "mws_xen_vm_api"]
VM_API = "apimws.xen"

EMAIL_TIMEOUT = 60

IP_REG_API_END_POINT = IP_REG_API_END_POINT + ['live']

METRICS_URL = 'https://test.dev.mws3.csx.cam.ac.uk:3000/dashboard/script/mws3.js'

from mws.logging_configuration import *
