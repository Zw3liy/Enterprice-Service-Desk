"""Compatibility module: apps/network_discovery/models/device.py."""
# Models for network_discovery live in primary models module.
try:
    from apps.network_discovery.models import *  # noqa
except Exception:
    pass
