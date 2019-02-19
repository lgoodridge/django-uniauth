"""
Example app Django settings.
"""

import os

# Settings used by Uniauth
LOGIN_URL = '/accounts/login/'
PASSWORD_RESET_TIMEOUT_DAYS = 3
UNIAUTH_ALLOW_SHARED_EMAILS = True
UNIAUTH_ALLOW_STANDALONE_ACCOUNTS = True
UNIAUTH_FROM_EMAIL = 'uniauth@demoapp.com'
UNIAUTH_LOGIN_DISPLAY_STANDARD = True 
UNIAUTH_LOGIN_DISPLAY_CAS = True 
UNIAUTH_LOGIN_REDIRECT_URL = '/'
UNIAUTH_LOGOUT_CAS_COMPLETELY = True
UNIAUTH_LOGOUT_REDIRECT_URL = None
UNIAUTH_MAX_LINKED_EMAILS = 20
UNIAUTH_PERFORM_RECURSIVE_MERGING = True

# Uniauth requires an actual email configuration to be set
# up (to send emails for email validation, changing passwords,
# etc.). This backend just prints emails to the screen.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Definitely change these for real applications
DEBUG = True
SECRET_KEY = 'FAKE_SECRET'
ALLOWED_HOSTS = ['*']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'uniauth',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Use the Uniauth authentication backends
AUTHENTICATION_BACKENDS = [
    'uniauth.backends.LinkedEmailBackend',
    'uniauth.backends.CASBackend',
]

ROOT_URLCONF = 'demo_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'demo_app', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'demo_app.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
