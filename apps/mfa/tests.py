from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.mfa.models import MFADevice
from apps.mfa.services import MFAService

User = get_user_model()


class MFAServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mfauser", password="pass12345")

    def test_enroll_confirm_verify(self):
        device = MFAService.enroll(self.user)
        self.assertFalse(device.is_active)
        # Generate a valid token from secret
        import base64
        import hashlib
        import hmac
        import struct
        import time

        key = base64.b32decode(device.secret + "=" * ((8 - len(device.secret) % 8) % 8))
        timestep = int(time.time() // 30)
        counter = struct.pack(">Q", timestep)
        digest = hmac.new(key, counter, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        token = f"{code % 1_000_000:06d}"
        self.assertTrue(MFAService.confirm(device, token))
        device.refresh_from_db()
        self.assertTrue(device.is_active)
        self.assertTrue(MFAService.is_enabled(self.user))
        self.assertTrue(MFAService.verify_user(self.user, token))
        codes = MFAService.generate_backup_codes(self.user, count=2)
        self.assertEqual(len(codes), 2)
        self.assertTrue(MFAService.verify_user(self.user, codes[0]))
        self.assertFalse(MFAService.verify_user(self.user, codes[0]))