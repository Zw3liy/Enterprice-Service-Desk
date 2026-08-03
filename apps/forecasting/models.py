"""Compatibility module: apps/forecasting/models.py."""
# Models for forecasting live in primary models module.
try:
    from apps.forecasting.models import *  # noqa
except Exception:
    pass
