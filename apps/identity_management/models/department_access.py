"""Compatibility module: apps/identity_management/models/department_access.py."""
# Models for identity_management live in primary models module.
try:
    from apps.identity_management.models import *  # noqa
except Exception:
    pass
