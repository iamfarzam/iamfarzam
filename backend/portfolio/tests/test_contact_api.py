"""Tests for the public contact form API endpoint."""

import json

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from portfolio.models import ContactMessage


@override_settings(REST_FRAMEWORK={
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
})
class ContactAPITests(TestCase):
    URL = "/api/v1/contact/"

    def setUp(self):
        # DRF throttles use the cache; reset between tests so we hit the
        # endpoint as a fresh client each time.
        cache.clear()
        self.client = Client()

    def _post(self, payload):
        return self.client.post(
            self.URL, data=json.dumps(payload), content_type="application/json"
        )

    def test_post_without_language_defaults_to_en(self):
        r = self._post({"name": "A", "email": "a@b.test", "subject": "S", "message": "M"})
        self.assertEqual(r.status_code, 201, r.content)
        m = ContactMessage.objects.latest("created_at")
        self.assertEqual(m.language, "en")

    def test_post_with_empty_language_coerced_to_en(self):
        r = self._post({
            "name": "A", "email": "a@b.test", "subject": "S",
            "message": "M", "language": "",
        })
        self.assertEqual(r.status_code, 201, r.content)
        m = ContactMessage.objects.latest("created_at")
        self.assertEqual(m.language, "en")

    def test_post_with_valid_language(self):
        r = self._post({
            "name": "A", "email": "a@b.test", "subject": "S",
            "message": "M", "language": "fa",
        })
        self.assertEqual(r.status_code, 201, r.content)
        m = ContactMessage.objects.latest("created_at")
        self.assertEqual(m.language, "fa")

    def test_post_with_invalid_language_rejected(self):
        r = self._post({
            "name": "A", "email": "a@b.test", "subject": "S",
            "message": "M", "language": "xx",
        })
        self.assertEqual(r.status_code, 400)

    def test_required_fields_validation(self):
        r = self._post({})
        self.assertEqual(r.status_code, 400)
        body = r.json()
        for field in ("name", "email", "subject", "message"):
            self.assertIn(field, body)

    def test_post_creates_contact_message(self):
        before = ContactMessage.objects.count()
        self._post({
            "name": "Jane", "email": "jane@x.test",
            "subject": "Inquiry", "message": "Hi there",
        })
        self.assertEqual(ContactMessage.objects.count(), before + 1)
        m = ContactMessage.objects.latest("created_at")
        self.assertEqual(m.name, "Jane")
        self.assertFalse(m.is_read)
