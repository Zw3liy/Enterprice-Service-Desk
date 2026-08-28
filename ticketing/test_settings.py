"""
Fast local/CI test configuration layered over ticketing.settings.

Activate with:
    DJANGO_SETTINGS_MODULE=ticketing.test_settings python manage.py test

Only changes password hashing speed. Every other setting (database
engine, apps, middleware, security flags) is inherited unchanged from
`ticketing.settings`, so this module changes *test run time*, never
test *behavior* or coverage.

Why this exists: Django's default `PASSWORD_HASHERS` starts with
PBKDF2 at a deliberately high, slow iteration count (a production
security requirement, not a bug). Measured on this development
machine, a single hash takes ~0.6s; this test suite creates many
users per test run (RBAC fixtures across four roles, repeated in
most test modules), which made a full `manage.py test` run take
hours instead of the ~1-2 minutes a suite this size should take,
`https://docs.djangoproject.com/en/stable/topics/testing/overview/#speeding-up-the-tests`
(Django's own docs recommend exactly this). `MD5PasswordHasher` is
cryptographically weak and is used here *only* for throwaway
in-memory test-database users — never for `ticketing.settings` (local
dev) or `ticketing.production_settings` (deployed), both of which are
untouched by this file.
"""

from .settings import *  # noqa: F401,F403

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
