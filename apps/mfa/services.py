"""MFA enrollment and verification services."""

from __future__ import annotations

import logging
import secrets

from django.db import transaction
from django.utils import timezone

from apps.mfa.models import MFABackupCode, MFADevice

logger = logging.getLogger(__name__)


class MFAService:
    @classmethod
    @transaction.atomic
    def enroll(cls, user, name: str = "Authenticator") -> MFADevice:
        device = MFADevice.objects.create(
            user=user,
            name=name,
            secret=MFADevice.generate_secret(),
            is_active=False,
        )
        logger.info("mfa_enroll user=%s device=%s", user.pk, device.pk)
        return device

    @classmethod
    def confirm(cls, device: MFADevice, token: str) -> bool:
        if not device.verify_token(token):
            return False
        device.is_active = True
        device.confirmed_at = timezone.now()
        device.last_used_at = timezone.now()
        device.save(update_fields=["is_active", "confirmed_at", "last_used_at", "updated_at"])
        return True

    @classmethod
    def verify_user(cls, user, token: str) -> bool:
        devices = MFADevice.objects.filter(user=user, is_active=True)
        for device in devices:
            if device.verify_token(token):
                device.last_used_at = timezone.now()
                device.save(update_fields=["last_used_at", "updated_at"])
                return True
        # backup codes
        code_hash = MFABackupCode.hash_code(str(token).strip().replace(" ", ""))
        backup = MFABackupCode.objects.filter(
            user=user, code_hash=code_hash, used_at__isnull=True
        ).first()
        if backup:
            backup.used_at = timezone.now()
            backup.save(update_fields=["used_at", "updated_at"])
            return True
        return False

    @classmethod
    def generate_backup_codes(cls, user, count: int = 8) -> list[str]:
        MFABackupCode.objects.filter(user=user, used_at__isnull=True).delete()
        codes = []
        for _ in range(count):
            raw = f"{secrets.randbelow(10**8):08d}"
            MFABackupCode.objects.create(user=user, code_hash=MFABackupCode.hash_code(raw))
            codes.append(raw)
        return codes

    @staticmethod
    def is_enabled(user) -> bool:
        return MFADevice.objects.filter(user=user, is_active=True).exists()

    @classmethod
    def disable(cls, user) -> int:
        updated = MFADevice.objects.filter(user=user, is_active=True).update(is_active=False)
        MFABackupCode.objects.filter(user=user).delete()
        return updated