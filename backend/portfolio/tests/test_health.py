from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase


class ReadinessTests(TestCase):
    def test_empty_portfolio_is_ready_when_database_is_available(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ready": True})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.client.head("/healthz/").status_code, 200)
        self.assertEqual(self.client.post("/healthz/").status_code, 405)

    def test_database_failure_is_unavailable_without_exposing_error_details(self):
        with patch("portfolio.health_views.connection.cursor", side_effect=DatabaseError("private connection details")):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"ready": False})
        self.assertNotContains(response, "private connection details", status_code=503)
