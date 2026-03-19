"""
Django settings for eshipping project.

For production deployment, copy .env.example to .env and configure your settings.

Last updated: 2026-02-28 - Fixed INSTALLED_APPS with apps. prefix
"""

import os
from pathlib import Path
from decouple import config

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# Generate a new secret key for production: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = config('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY environment variable must be set. Generate one with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default='False') == 'True'

ALLOWED_HOSTS = [h.strip() for h in config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',') if h.strip()]
# Always allow localhost and 127.0.0.1 for internal requests (e.g., wkhtmltopdf)
if 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('localhost')
if '127.0.0.1' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('127.0.0.1')

# CSRF Trusted Origins (required for cross-origin POST requests)
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='').split(',')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS if origin.strip()]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'simple_history',
    'csp',  # Content Security Policy
    'apps.tally',
    'apps.accounts',
    'apps.operations',
    'apps.ebooking',
    'apps.declaration',
    'apps.evacuation',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',  # SECURITY: Content Security Policy
    'simple_history.middleware.HistoryRequestMiddleware',
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'eshipping.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.operations.context_processors.sd_numbers',
                'apps.operations.context_processors.pending_recall_requests_count',
            ],
            'debug': DEBUG,  # Use DEBUG setting from environment
        },
    },
]

WSGI_APPLICATION = 'eshipping.wsgi.application'
ASGI_APPLICATION = 'eshipping.asgi.application'


# Database configuration
import dj_database_url

database_url = config('DATABASE_URL', default=None)

if not database_url:
    raise ImproperlyConfigured(
        'DATABASE_URL environment variable must be set. '
        'For Railway: Add DATABASE_URL variable with value ${{Postgres.DATABASE_URL}}'
    )

# Check if PostgreSQL driver is available
try:
    import psycopg  # Try psycopg3 first (preferred)
except ImportError:
    try:
        import psycopg2  # type: ignore  # Fall back to psycopg2 (legacy)
    except ImportError:
        raise ImproperlyConfigured(
            'PostgreSQL driver not found. Install psycopg2-binary: pip install psycopg2-binary'
        )

# Configure PostgreSQL database
parsed_config = dj_database_url.parse(
    database_url,
    conn_max_age=600,
    conn_health_checks=True,
)

DATABASES = {
    'default': parsed_config
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6}  # Regular staff: 6 characters minimum
    },
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (User uploads)
MEDIA_URL = '/media/'

# Railway persistent volume mount path (attach volume at /app/media)
# Using an absolute path ensures files survive container restarts/redeploys.
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/app/media')

# Fallback for local development (if running without Railway volume)
if DEBUG:
    MEDIA_ROOT = BASE_DIR / 'media'

# File Upload Security Settings
# Maximum size for request bodies / in-memory uploads.
# IMPORTANT: Must be >= MAX_EXCEL_FILE_SIZE to avoid Django rejecting uploads before validators run.
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25 MB

# Specific file size limits (used in validators)
MAX_PDF_FILE_SIZE = 10  # MB
MAX_EXCEL_FILE_SIZE = 25  # MB
MAX_IMAGE_FILE_SIZE = 5  # MB

# WhiteNoise configuration for serving static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.Account'

TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "excel_templates",
    "straight.xlsx"
)

# Production Security Settings
# Enable these in production with HTTPS
if not DEBUG:
    # SECURITY: Configure reverse proxy SSL header for platforms like Render, Heroku
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True') == 'True'
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Session Security Settings
SESSION_COOKIE_AGE = 14400  # SECURITY: Reduced from 8 hours to 4 hours (14400 seconds)
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Keep session across browser restarts
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access to CSRF token
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'


# Security Audit Logging
# Prefer stdout logging in production (Railway captures console logs).
LOGS_DIR = BASE_DIR / 'logs'
if DEBUG:
    os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        **({
            'security_file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': LOGS_DIR / 'security.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'verbose',
            }
        } if DEBUG else {}),
    },
    'loggers': {
        'django.security': {
            'handlers': (['security_file', 'console'] if DEBUG else ['console']),
            'level': 'WARNING',
            'propagate': False,
        },
        'apps.accounts': {
            'handlers': (['security_file', 'console'] if DEBUG else ['console']),
            'level': 'INFO',
            'propagate': False,
        },
        'apps.operations': {
            'handlers': (['security_file', 'console'] if DEBUG else ['console']),
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Content Security Policy (CSP) Configuration
# Enforces strict content security policy to prevent XSS and injection attacks
CSP_REPORT_ONLY = False
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com", "'unsafe-inline'")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "blob:")
CSP_CONNECT_SRC = ("'self'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com")
CSP_FRAME_ANCESTORS = ("'none'",)

# Additional Security Headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# Permissions Policy (formerly Feature Policy)
PERMISSIONS_POLICY = {
    'geolocation': [],
    'microphone': [],
    'camera': [],
    'payment': [],
    'usb': [],
}

