"""Compatibility module: apps/cmdb/models/ci_type.py."""
# Models for cmdb live in primary models module.
try:
    from apps.cmdb.models import *  # noqa
except Exception:
    pass
