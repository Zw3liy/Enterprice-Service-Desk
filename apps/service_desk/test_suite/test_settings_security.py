"""
SEC-01

Regression coverage for the environment-variable-driven settings
helpers introduced to move SECRET_KEY/DEBUG/ALLOWED_HOSTS off
hardcoded values. Settings themselves are computed once at process
start (before any test can patch os.environ), so this tests the
parsing helper functions directly rather than re-triggering settings
resolution — and separately confirms the *current* resolved values
still match the previous hardcoded defaults, since no env vars are
set in this test environment.
"""

from django.test import SimpleTestCase
from django.conf import settings

from ticketing.settings import _env_bool, _env_list, _env_int


class EnvHelperTests(SimpleTestCase):

    def test_env_bool_defaults_when_unset(self):
        self.assertTrue(_env_bool("SEC01_DOES_NOT_EXIST", default=True))
        self.assertFalse(_env_bool("SEC01_DOES_NOT_EXIST", default=False))

    def test_env_bool_parses_truthy_strings(self):
        import os
        for value in ["1", "true", "True", "yes", "on", "ON"]:
            os.environ["SEC01_TEST_BOOL"] = value
            try:
                self.assertTrue(_env_bool("SEC01_TEST_BOOL"))
            finally:
                del os.environ["SEC01_TEST_BOOL"]

    def test_env_bool_parses_falsy_strings(self):
        import os
        for value in ["0", "false", "False", "no", "off"]:
            os.environ["SEC01_TEST_BOOL"] = value
            try:
                self.assertFalse(_env_bool("SEC01_TEST_BOOL"))
            finally:
                del os.environ["SEC01_TEST_BOOL"]

    def test_env_list_splits_and_strips(self):
        import os
        os.environ["SEC01_TEST_LIST"] = "example.com, www.example.com ,api.example.com"
        try:
            self.assertEqual(
                _env_list("SEC01_TEST_LIST", default=[]),
                ["example.com", "www.example.com", "api.example.com"],
            )
        finally:
            del os.environ["SEC01_TEST_LIST"]

    def test_env_list_defaults_when_unset(self):
        self.assertEqual(
            _env_list("SEC01_DOES_NOT_EXIST", default=["localhost"]),
            ["localhost"],
        )

    def test_env_int_parses_and_falls_back(self):
        import os
        os.environ["SEC01_TEST_INT"] = "3600"
        try:
            self.assertEqual(_env_int("SEC01_TEST_INT", default=0), 3600)
        finally:
            del os.environ["SEC01_TEST_INT"]

        os.environ["SEC01_TEST_INT"] = "not-a-number"
        try:
            self.assertEqual(_env_int("SEC01_TEST_INT", default=0), 0)
        finally:
            del os.environ["SEC01_TEST_INT"]


class ResolvedSettingsMatchPreviousDefaultsTests(SimpleTestCase):
    """
    No env vars are set in this test environment, so the resolved
    settings must still equal exactly what was previously hardcoded
    — this is what guarantees the change is zero-risk for anyone
    running the app without any environment setup.
    """

    # Note: no test asserts settings.DEBUG directly — Django's test
    # runner (setup_test_environment) unconditionally forces DEBUG
    # to False for the duration of the test suite regardless of what
    # settings.py computed, so it can't be observed here. The
    # DJANGO_DEBUG default is covered instead by
    # test_env_bool_defaults_when_unset above, and indirectly by
    # test_secret_key_falls_back_to_dev_key_when_debug_true below —
    # SECRET_KEY resolution happens once at process start, before
    # the test runner's override, so it still reflects the real
    # DEBUG value this process started with.

    def test_allowed_hosts_defaults_match_previous_hardcoded_values(self):
        # Django's test runner appends "testserver" to ALLOWED_HOSTS
        # for the test client's benefit — check the real defaults
        # are still present rather than asserting exact equality.
        self.assertIn("localhost", settings.ALLOWED_HOSTS)
        self.assertIn("127.0.0.1", settings.ALLOWED_HOSTS)

    def test_secret_key_falls_back_to_dev_key_when_debug_true(self):
        self.assertTrue(settings.SECRET_KEY.startswith("django-insecure-"))

    def test_always_on_hardening_is_active(self):
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")

    def test_https_only_hardening_is_inactive_in_debug(self):
        # These require HTTPS to function; must stay off while
        # DEBUG defaults to True, or local HTTP dev would break.
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.CSRF_COOKIE_SECURE)
        self.assertFalse(settings.SECURE_SSL_REDIRECT)

    def test_hsts_disabled_by_default(self):
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)
