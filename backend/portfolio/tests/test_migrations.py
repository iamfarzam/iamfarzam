"""Tests that migrations are clean and 0012 is idempotent."""

import importlib
from io import StringIO

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase

from portfolio.email import _get_defaults
from portfolio.models import EmailTemplate


class MigrationsCleanTests(TestCase):
    def test_no_unmigrated_model_changes(self):
        """`makemigrations --check` must not detect any pending changes."""
        out = StringIO()
        try:
            call_command(
                "makemigrations", "--dry-run", "--check",
                stdout=out, verbosity=0,
            )
        except SystemExit as exc:
            # SystemExit with non-zero code means pending migrations exist
            self.fail(f"Pending migrations detected: {exc}\n{out.getvalue()}")

    def test_email_template_migrations_applied(self):
        out = StringIO()
        call_command("showmigrations", "portfolio", stdout=out, verbosity=0)
        text = out.getvalue()
        for migration in ("0007", "0011", "0012"):
            with self.subTest(migration=migration):
                self.assertIn(f"[X] {migration}", text)


class HydrateTranslationsIdempotencyTests(TestCase):
    """Migration 0012 fills empty language columns and never overwrites edits."""

    def setUp(self):
        EmailTemplate.objects.filter(name="admin_reply").delete()
        d = _get_defaults("en")["admin_reply"]
        self.tpl = EmailTemplate.objects.create(
            name="admin_reply", is_active=True,
            subject=d["subject"], html_body=d["html_body"], text_body=d["text_body"],
        )
        self.module = importlib.import_module(
            "portfolio.migrations.0012_seed_email_template_translations"
        )

    def test_hydrates_all_language_columns(self):
        self.module.hydrate_translations(apps, None)
        self.tpl.refresh_from_db()
        from django.conf import settings
        for code, _ in settings.LANGUAGES:
            suffix = code.replace("-", "_")
            with self.subTest(language=code):
                self.assertTrue(
                    getattr(self.tpl, f"subject_{suffix}"),
                    f"subject_{suffix} is empty after hydrate",
                )

    def test_does_not_overwrite_user_edits(self):
        self.module.hydrate_translations(apps, None)
        self.tpl.refresh_from_db()
        self.tpl.subject_fa = "MANUALLY EDITED"
        self.tpl.save()

        self.module.hydrate_translations(apps, None)
        self.tpl.refresh_from_db()
        self.assertEqual(self.tpl.subject_fa, "MANUALLY EDITED")

    def test_safe_to_run_when_no_template_rows(self):
        EmailTemplate.objects.all().delete()
        # Should not raise
        self.module.hydrate_translations(apps, None)
