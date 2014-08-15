"""
Django settings for MWS project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.conf import global_settings

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = (
    # Customization for the grappelli admin system
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # The following app force all views to have @login_required https://github.com/mgrouchy/django-stronghold/
    'stronghold',
    'ucamwebauth',
    'ucamprojectlight',
    'sitesmanagement',
    'apimws',
    'mwsauth',
    'ucamlookup'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # The following app force all views to have @login_required https://github.com/mgrouchy/django-stronghold/
    'stronghold.middleware.LoginRequiredMiddleware',
    #TODO The CheckBannedUsers middleware check if users are banned before serving any page
    #'MWS.middleware.CheckBannedUsers'
    'ucamwebauth.middleware.DefaultErrorBehaviour'
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

STATICFILES_DIRS = ('/Users/amc203/Development/PycharmProjects/django-ucamlookup/ucamlookup/static',
                    '/Users/amc203/Development/PycharmProjects/mws/mws/static')  # TODO REMOVE

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Customization for the grappelli admin system
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + ('django.core.context_processors.request', )
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)
GRAPPELLI_ADMIN_TITLE = "Managed Web Service"

# ucamwebauth configuration
UCAMWEBAUTH_CREATE_USER = True
UCAMWEBAUTH_TIMEOUT = 30
UCAMWEBAUTH_LOGOUT_REDIRECT = 'http://www.cam.ac.uk/'

STRONGHOLD_PUBLIC_NAMED_URLS = ('raven_login', 'raven_return')