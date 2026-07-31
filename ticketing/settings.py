"""
Django settings for ticketing project.

Enterprise Service Desk Platform
Phase 6 - Application Layer
"""

from pathlib import Path


# -------------------------------------------------
# BASE DIRECTORY
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------
# SECURITY
# -------------------------------------------------

SECRET_KEY = "django-insecure-a)ek*sm1cxz@pst6qkgfc&h3-d!memp1ng1wtj)nhp*dxa-_wp"

DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
]


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

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = "/service-desk/"

LOGOUT_REDIRECT_URL = "/login/"