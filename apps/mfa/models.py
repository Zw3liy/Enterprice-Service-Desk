"""TOTP-based multi-factor authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time

from django.conf import settings
from django.db import models

from apps.service_desk.models import TimeStampedModel


class MFADevice(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_devices",
    )
    name = models.CharField(max_length=80, default="Authenticator")
    secret = models.CharField(max_length=64)
    is_active = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.name}"

    @staticmethod
    def generate_secret(length: int = 20) -> str:
        return base64.b32encode(os.urandom(length)).decode("utf-8").rstrip("=")

    def provisioning_uri(self, issuer: str = "Enterprise Service Desk") -> str:
        import urllib.parse

        label = urllib.parse.quote(f"{issuer}:{self.user.get_username()}")
        secret = self.secret
        # pad for URI consumers
        pad = "=" * ((8 - len(secret) % 8) % 8)
        return (
            f"otpauth://totp/{label}?secret={secret}{pad}"
            f"&issuer={urllib.parse.quote(issuer)}&digits=6&period=30"
        )

    def verify_token(self, token: str, window: int = 1) -> bool:
        try:
            token_int = int(str(token).strip())
        except (TypeError, ValueError):
            return False
        key = base64.b32decode(self.secret + "=" * ((8 - len(self.secret) % 8) % 8))
        timestep = int(time.time() // 30)
        for offset in range(-window, window + 1):
            counter = struct.pack(">Q", timestep + offset)
            digest = hmac.new(key, counter, hashlib.sha1).digest()
            offset_byte = digest[-1] & 0x0F
            code = struct.unpack(">I", digest[offset_byte : offset_byte + 4])[0] & 0x7FFFFFFF
            code = code % 1_000_000
            if code == token_int:
                return True
        return False


class MFABackupCode(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_backup_codes",
    )
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()