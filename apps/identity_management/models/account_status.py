"""Compatibility module: apps/identity_management/models/account_status.py."""
# Models for identity_management live in primary models module.
try:
    from apps.identity_management.models import *  # noqa
except Exception:
    pass
