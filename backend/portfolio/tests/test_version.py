"""Tests for the SemVer chip exposed via Unfold ENVIRONMENT."""

import re

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase

from portfolio.admin import project_version_environment


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+].*)?$")


class ProjectVersionTests(TestCase):
    def test_settings_exposes_project_version(self):
        self.assertTrue(hasattr(settings, "PROJECT_VERSION"))
        self.assertTrue(SEMVER_RE.match(settings.PROJECT_VERSION),
                        f"not a SemVer string: {settings.PROJECT_VERSION!r}")

    def test_environment_callback_returns_chip_tuple(self):
        chip = project_version_environment(None)
        self.assertEqual(len(chip), 2)
        label, color = chip
        self.assertTrue(label.startswith("v"))
        self.assertIn(settings.PROJECT_VERSION, label)
        self.assertEqual(color, "info")

    def test_unfold_environment_setting_wired(self):
        self.assertEqual(
            settings.UNFOLD.get("ENVIRONMENT"),
            "portfolio.admin.project_version_environment",
        )


class VersionChipRendersInAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="ad@x.test", password="x",
            is_staff=True, is_superuser=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_version_appears_on_admin_index(self):
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 200)
        chip_text = f"v{settings.PROJECT_VERSION}".encode()
        self.assertIn(chip_text, r.content)
