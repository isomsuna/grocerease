import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-development-only-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() in {'1', 'true', 'yes'}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'accounts',
    'core',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'grocerease'),
        'USER': os.getenv('POSTGRES_USER', 'grocerease'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'grocerease'),
        'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    },
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'user_attributes': ('email', 'display_name')},
    },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.SessionAuthenticationWith401',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False

def validate_frontend_password_reset_url(url: str, *, debug: bool) -> str:
    parsed_url = urlparse(url)
    if not debug and (parsed_url.scheme != 'https' or not parsed_url.netloc):
        raise ImproperlyConfigured(
            'FRONTEND_PASSWORD_RESET_URL must be an absolute HTTPS URL when DEBUG is false.'
        )
    return url


FRONTEND_PASSWORD_RESET_URL = validate_frontend_password_reset_url(os.getenv(
    'FRONTEND_PASSWORD_RESET_URL',
    'http://localhost:5173/reset-password' if DEBUG else '',
), debug=DEBUG)
DEFAULT_FROM_EMAIL = os.getenv('DJANGO_DEFAULT_FROM_EMAIL', 'noreply@grocerease.local')
EMAIL_BACKEND = os.getenv(
    'DJANGO_EMAIL_BACKEND',
    (
        'django.core.mail.backends.locmem.EmailBackend'
        if DEBUG
        else 'django.core.mail.backends.smtp.EmailBackend'
    ),
)
EMAIL_HOST = os.getenv('DJANGO_EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('DJANGO_EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.getenv('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('DJANGO_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('DJANGO_EMAIL_USE_TLS', 'false').lower() in {'1', 'true', 'yes'}
