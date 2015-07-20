"""
Django settings for bootstrap_lti project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from os.path import abspath, basename, dirname, join, normpath
from django.core.urlresolvers import reverse_lazy
from sys import path
from .secure import SECURE_SETTINGS

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Absolute filesystem path to the Django project config directory:
# (this is the parent of the directory where this file resides,
# since this file is now inside a 'settings' pacakge directory)
DJANGO_PROJECT_CONFIG = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
# (this is one directory up from the project config directory)
SITE_ROOT = dirname(DJANGO_PROJECT_CONFIG)

# Site name:
SITE_NAME = basename(SITE_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(SITE_ROOT)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECURE_SETTINGS.get('django_secret_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'edx2canvas',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'cached_auth.Middleware',
    'django_auth_lti.middleware.LTIAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
AUTHENTICATION_BACKENDS = (
    'django_auth_lti.backends.LTIAuthBackend',
)

CRISPY_TEMPLATE_PACK = 'bootstrap3'


LOGIN_URL = reverse_lazy('lti_auth_error')

ROOT_URLCONF = 'edx_lti_authoring.urls'

WSGI_APPLICATION = 'edx_lti_authoring.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/lti_tools/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    normpath(join(SITE_ROOT, 'static')),
)
STATIC_ROOT = normpath(join(SITE_ROOT, 'http_static'))
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATE_DIRS = (
    normpath(join(SITE_ROOT, 'templates')),
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LTI_OAUTH_CREDENTIALS = SECURE_SETTINGS.get('lti_oauth_credentials', None)

CANVAS_DOMAIN = SECURE_SETTINGS.get('canvas_domain', None)
CANVAS_SDK_SETTINGS = {
    'auth_token': SECURE_SETTINGS.get('canvas_token', None),
    'base_api_url': '{}/api'.format(CANVAS_DOMAIN),
    'max_retries': 3,
    'per_page': 40,
}

EDX_URL_BASE = SECURE_SETTINGS.get('edx_url_base', None)
EXTERNAL_TOOL_DOMAIN = SECURE_SETTINGS.get('external_tool_domain', None)

EDX_LTI_PREVIEW_SETTINGS = {
    'url_base': '{}/lti_provider/courses'.format(EDX_URL_BASE),
    'key': SECURE_SETTINGS.get('edx_lti_preview_key', None),
    'secret': SECURE_SETTINGS.get('edx_lti_preview_secret', None),
    'tool_consumer_instance_guid': SECURE_SETTINGS.get('preview_tool_consumer_guid', None),
    'user_id': SECURE_SETTINGS.get('preview_user_id', None),
    'roles': u'[student]',
    'context_id': u'CanvasInstallationContext',
    'lti_version': u'LTI-1p0'
}

EDX_LTI_KEY = SECURE_SETTINGS.get('edx_lti_provider_key', None)
EDX_LTI_SECRET = SECURE_SETTINGS.get('edx_lti_provider_secret', None)

CANVAS_OAUTH_CLIENT_ID = SECURE_SETTINGS.get('canvas_oauth_client_id', None)
CANVAS_OAUTH_CLIENT_KEY = SECURE_SETTINGS.get('canvas_oauth_client_key', None)