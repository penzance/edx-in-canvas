from .local import *


DATABASE_APPS_MAPPING = {
}

DATABASE_MIGRATION_WHITELIST = ['default']

# Make tests faster by using sqlite3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

"""
Unit tests should be able to run without talking to external services like
redis/elasticache.  Let's disable the caching middleware, and use the db
to store session data.
"""
MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
MIDDLEWARE_CLASSES[MIDDLEWARE_CLASSES.index('cached_auth.Middleware')] = \
    'django.contrib.auth.middleware.AuthenticationMiddleware'
MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
