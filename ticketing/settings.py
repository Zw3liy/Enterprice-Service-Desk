"""
Django settings for ticketing project.

Enterprise Service Desk Platform
Phase 6 - Application Layer
"""

import os

from django.core.exceptions import ImproperlyConfigured

from pathlib import Path


# -------------------------------------------------
# BASE DIRECTORY
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------
# ENVIRONMENT HELPERS
#
# Stdlib-only (no django-environ / python-dotenv
# dependency added) — see docs/engineering/ROADMAP.md,
# SEC-01, for why. Every default below reproduces the
# exact previous hardcoded behavior when no environment
# variable is set, so local `manage.py runserver` needs
# no setup. See .env.example for the full variable list.
# -------------------------------------------------

_DEV_FALLBACK_SECRET_KEY = (
    "django-insecure-a)ek*sm1cxz@pst6qkgfc&h3-d!memp1ng1wtj)nhp*dxa-_wp"
)


def _env_bool(name, default=False):
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name, default):
    value = os.environ.get(name)

    if value is None:
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


def _env_int(name, default):
    value = os.environ.get(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


# -------------------------------------------------
# SECURITY
# -------------------------------------------------

DEBUG = _env_bool("DJANGO_DEBUG", default=True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = _DEV_FALLBACK_SECRET_KEY
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY environment variable must be set "
            "when DJANGO_DEBUG is not enabled. Refusing to start "
            "with a public, hardcoded key in a non-debug "
            "environment."
        )

ALLOWED_HOSTS = _env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

# Always safe — do not require HTTPS or any deployment-specific
# setup, so these are on regardless of DEBUG.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Requires HTTPS to function correctly — only enabled outside
# local development, where DEBUG is explicitly turned off.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

# HSTS is opt-in via env var (default 0 = disabled). Misconfiguring
# this can lock users out of a domain for a long time, so it is
# never enabled implicitly by DEBUG alone.
SECURE_HSTS_SECONDS = _env_int("DJANGO_SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0


# -------------------------------------------------
# APPLICATIONS
# -------------------------------------------------

INSTALLED_APPS = [

    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",


    # Enterprise Service Desk
    "apps.service_desk",

]


# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",

]


# -------------------------------------------------
# URL CONFIGURATION
# -------------------------------------------------

ROOT_URLCONF = "ticketing.urls"


# -------------------------------------------------
# TEMPLATES
# -------------------------------------------------

TEMPLATES = [

    {
        "BACKEND":
        "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {

            "context_processors": [

                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",

                "apps.service_desk.context_processors.notifications",

            ],
        },
    },
]


# -------------------------------------------------
# SERVER
# -------------------------------------------------

WSGI_APPLICATION = "ticketing.wsgi.application"

ASGI_APPLICATION = "ticketing.asgi.application"



# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASES = {

    "default": {

        "ENGINE":
        "django.db.backends.sqlite3",

        "NAME":
        BASE_DIR / "db.sqlite3",

    }

}



# -------------------------------------------------
# PASSWORD VALIDATION
# -------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
        "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },

    {
        "NAME":
        "django.contrib.auth.password_validation.MinimumLengthValidator",
    },

    {
        "NAME":
        "django.contrib.auth.password_validation.CommonPasswordValidator",
    },

    {
        "NAME":
        "django.contrib.auth.password_validation.NumericPasswordValidator",
    },

]



# -------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Johannesburg"

USE_I18N = True

USE_TZ = True



# -------------------------------------------------
# STATIC FILES
# -------------------------------------------------

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]



# -------------------------------------------------
# MEDIA FILES
# Ticket attachments / screenshots / documents
# -------------------------------------------------

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"



# -------------------------------------------------
# DEFAULT PRIMARY KEY
# -------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



# -------------------------------------------------
# LOGIN CONFIGURATION
# Phase 6 Authentication
# -------------------------------------------------

# Authentication redirects

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"



# -------------------------------------------------
# EMAIL / NOTIFICATIONS
#
# The service desk's notification boundary is in-app
# first: a Notification row is always written and email
# is an optional mirror. Everything below is env-driven
# (SEC-01's pattern) and defaults to OFF, so a clone of
# this repository — and CI — never attempts to reach a
# mail server and no credential is ever committed. See
# .env.example for the full variable list.
# -------------------------------------------------

SERVICE_DESK_EMAIL_NOTIFICATIONS = _env_bool(
    "DJANGO_EMAIL_NOTIFICATIONS",
    default=False,
)

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")

EMAIL_PORT = _env_int("DJANGO_EMAIL_PORT", default=587)

EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")

EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")

EMAIL_USE_TLS = _env_bool("DJANGO_EMAIL_USE_TLS", default=True)

EMAIL_TIMEOUT = _env_int("DJANGO_EMAIL_TIMEOUT", default=10)

DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL",
    "service-desk@localhost",
)


# -------------------------------------------------
# LOGGING
#
# Minimal, dependency-free console logging so warnings
# (e.g. django.security events, disallowed hosts) are
# actually visible once DEBUG=False stops showing the
# debug error page. Does not configure email/SMTP
# alerting (ADMINS/SERVER_EMAIL) — that needs real
# credentials, a separate decision, not guessed at here.
# -------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}