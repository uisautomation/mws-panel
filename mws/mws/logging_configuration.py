LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(pathname)s:%(lineno)d %(funcName)s "%(message)s"'
        },
        'simple': {
            'format': '%(levelname)s "%(message)s"'
        },
    },
    'handlers': {
        'log_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/mws/mws.log',
            'formatter': 'verbose',
        },
        'log_errorfile': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/mws/mws_error.log',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['log_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins', 'log_errorfile'],
            'level': 'WARNING',
            'propagate': False,
        },
        'mws': {
            'handlers': ['log_file', 'mail_admins', 'log_errorfile'],
            'level': 'INFO'
        }
    }
}