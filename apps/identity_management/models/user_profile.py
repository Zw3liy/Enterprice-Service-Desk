"""Compatibility module: apps/identity_management/models/user_profile.py."""
# Models for identity_management live in primary models module.
try:
    from apps.identity_management.models import *  # noqa
except Exception:
    pass
