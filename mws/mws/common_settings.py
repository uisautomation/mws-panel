import os
from django.conf import global_settings

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# Application definition

PROJECT_APPS = (
    'sitesmanagement',
    'apimws',
    'mwsauth',
)

INSTALLED_APPS = (
    # Customization for the grappelli admin system
    'suit',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # The following app force all views to have @login_required https://github.com/mgrouchy/django-stronghold/
    'stronghold',
    'reversion',
    'ucamwebauth',
    'ucamprojectlight',
    'ucamlookup',
) + PROJECT_APPS

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # The following app force all views to have @login_required https://github.com/mgrouchy/django-stronghold/
    'stronghold.middleware.LoginRequiredMiddleware',
    'ucamwebauth.middleware.DefaultErrorBehaviour',
    'reversion.middleware.RevisionMiddleware',
)

AUTHENTICATION_BACKENDS = (
    # The Raven Authentication
    'ucamwebauth.backends.RavenAuthBackend',
)

ROOT_URLCONF = 'mws.urls'

WSGI_APPLICATION = 'mws.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-GB'

TIME_ZONE = 'Europe/London'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static_dep')
STATIC_URL = '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

TEMPLATE_DIRS = (os.path.join(BASE_DIR, 'templates'),)
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Customization for the grappelli admin system
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + ('django.core.context_processors.request', )
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

SUIT_CONFIG = {
    'ADMIN_NAME': "Managed Web Service",

    # menu
    # 'SEARCH_URL': '/admin/auth/user/',
    # 'MENU_ICONS': {
    #    'sites': 'icon-leaf',
    #    'auth': 'icon-lock',
    # },
    # 'MENU_OPEN_FIRST_CHILD': True, # Default True
    # 'MENU_EXCLUDE': ('auth.group',),
    # 'MENU': (
    #     'sites',
    #     {'app': 'auth', 'icon':'icon-lock', 'models': ('user', 'group')},
    #     {'label': 'Settings', 'icon':'icon-cog', 'models': ('auth.user', 'auth.group')},
    #     {'label': 'Support', 'icon':'icon-question-sign', 'url': '/support/'},
    # ),

    # misc
    # 'LIST_PER_PAGE': 15
}

# email address where all the error messages will be sent to
EMAIL_MWS3_SUPPORT = "mws3-support@cam.ac.uk"

# ucamwebauth configuration
UCAMWEBAUTH_CREATE_USER = True
UCAMWEBAUTH_TIMEOUT = 30
UCAMWEBAUTH_LOGOUT_REDIRECT = 'http://www.cam.ac.uk/'

STRONGHOLD_PUBLIC_NAMED_URLS = ('raven_login', 'raven_return')
#CELERY_ACCEPT_CONTENT = ['json'] # TODO

OS_VERSION = "jessie"
OS_VERSION_VMAPI = "Debian 8RC1 x86_64 preseed"
OS_VERSION_VMXENAPI = "jessie"
OS_DUE_UPGRADE = []

YEAR_COST = 100.00
FINANCE_EMAIL = 'amc203@cam.ac.uk'

CELERY_IMPORTS = ('apimws.platforms', 'apimws.xen', 'apimws.utils', 'apimws.jackdaw', 'apimws.ansible')
IP_REG_API_END_POINT = ['mws_ipreg']
