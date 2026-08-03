"""Compatibility module: apps/ai_engine/models/ai_audit.py."""
# Models for ai_engine live in primary models module.
try:
    from apps.ai_engine.models import *  # noqa
except Exception:
    pass
