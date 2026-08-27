from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse


class LivenessTests(TestCase):
    def test_liveness_succeeds_without_database_query(self):
        with self.assertNumQueries(0):
            response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})

    def test_liveness_rejects_post(self):
        response = self.client.post(reverse("health-live"))
        self.assertEqual(response.status_code, 405)


class ReadinessTests(TestCase):
    def test_readiness_succeeds_when_database_is_available(self):
        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready"})

    def test_readiness_fails_safely_when_database_is_unavailable(self):
        with patch(
            "ticketing.health_views.connection.cursor",
            side_effect=DatabaseError("sensitive database details"),
        ):
            response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotContains(
            response,
            "sensitive database details",
            status_code=503,
        )

    def test_readiness_rejects_post(self):
        response = self.client.post(reverse("health-ready"))
        self.assertEqual(response.status_code, 405)
