"""Compatibility module: apps/customer_portal/models/customer.py."""
# Models for customer_portal live in primary models module.
try:
    from apps.customer_portal.models import *  # noqa
except Exception:
    pass
