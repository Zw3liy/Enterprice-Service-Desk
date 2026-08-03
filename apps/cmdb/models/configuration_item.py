"""Compatibility module: apps/cmdb/models/configuration_item.py."""
# Models for cmdb live in primary models module.
try:
    from apps.cmdb.models import *  # noqa
except Exception:
    pass
