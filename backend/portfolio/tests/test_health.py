from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase


class ReadinessTests(TestCase):
    def test_empty_portfolio_is_ready_when_dependencies_are_available(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ready": True, "database": True, "cache": True})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.client.head("/healthz/").status_code, 200)
        self.assertEqual(self.client.post("/healthz/").status_code, 405)

    def test_database_failure_is_unavailable_without_exposing_error_details(self):
        with patch("portfolio.health_views.connection.cursor", side_effect=DatabaseError("private connection details")):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ready"])
        self.assertFalse(response.json()["database"])
        self.assertNotContains(response, "private connection details", status_code=503)

    def test_unreachable_cache_is_unavailable_without_exposing_error_details(self):
        # Contact throttling depends on the shared cache, so a misconfigured cache
        # URL must fail readiness instead of deploying and breaking on first use.
        with patch("portfolio.health_views.cache.set", side_effect=Exception("private cache location")):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ready"])
        self.assertFalse(response.json()["cache"])
        self.assertTrue(response.json()["database"])
        self.assertNotContains(response, "private cache location", status_code=503)

    def test_silently_broken_cache_round_trip_is_unavailable(self):
        with patch("portfolio.health_views.cache.get", return_value=None):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["cache"])
