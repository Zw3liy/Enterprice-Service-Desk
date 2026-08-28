"""
PostgreSQL CI settings.

These settings retain the production database parser while using
test-safe security and static-file behavior. They must never be used
to serve a deployed environment.
"""

from .production_settings import *  # noqa: F401,F403


DEBUG = True
SECRET_KEY = "django-insecure-postgresql-ci-only-key"
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Fast, throwaway hasher for CI-only test-database users — see
# ticketing/test_settings.py for the full rationale (same fix,
# applied here too since this settings module is what the
# PostgreSQL CI job actually runs the suite under).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}
