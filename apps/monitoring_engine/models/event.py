"""Compatibility module: apps/monitoring_engine/models/event.py."""
# Models for monitoring_engine live in primary models module.
try:
    from apps.monitoring_engine.models import *  # noqa
except Exception:
    pass
