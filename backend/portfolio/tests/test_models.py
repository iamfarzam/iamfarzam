"""Tests for model invariants: single-active rules, defaults, choices."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from portfolio.models import ContactMessage, EmailConfiguration, EmailTemplate


class EmailConfigurationSingleActiveTests(TestCase):
    """Only one EmailConfiguration row may have is_active=True at a time."""

    def _make(self, label, is_active=False, email=None):
        return EmailConfiguration.objects.create(
            label=label, smtp_host="h", smtp_user="u", smtp_password="p",
            from_name="N", from_email=email or f"{label}@x.test",
            is_active=is_active,
        )

    def test_save_deactivates_other_rows(self):
        a = self._make("A", is_active=True)
        self._make("B", is_active=True)
        self.assertEqual(EmailConfiguration.objects.filter(is_active=True).count(), 1)
        self.assertEqual(
            EmailConfiguration.objects.get(is_active=True).label, "B"
        )
        a.is_active = True
        a.save()
        self.assertEqual(
            EmailConfiguration.objects.get(is_active=True).label, "A"
        )

    def test_db_constraint_blocks_two_active(self):
        a = self._make("A", is_active=True)
        b = self._make("B", is_active=False)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                # Bypass save() override to exercise the constraint directly
                EmailConfiguration.objects.filter(pk=b.pk).update(is_active=True)
                # Postgres raises at COMMIT for deferred — force it by querying
                from django.db import connection
                connection.check_constraints()

    def test_from_identity_property(self):
        cfg = self._make("X")
        cfg.from_name = "Real"
        cfg.from_email = "r@x.test"
        cfg.save()
        self.assertEqual(cfg.from_identity, "Real <r@x.test>")

    def test_from_identity_without_name(self):
        cfg = self._make("X")
        cfg.from_name = ""
        cfg.from_email = "r@x.test"
        self.assertEqual(cfg.from_identity, "r@x.test")

    def test_reply_to_identity_empty_when_no_email(self):
        cfg = self._make("X")
        self.assertEqual(cfg.reply_to_identity, "")

    def test_str_does_not_leak_password(self):
        cfg = self._make("Label")
        cfg.smtp_password = "SECRET"
        cfg.save()
        self.assertEqual(str(cfg), "Label")
        self.assertNotIn("SECRET", str(cfg))


class EmailTemplateSingleActivePerNameTests(TestCase):
    def setUp(self):
        # Migration 0007 seeds three template rows; clear so we count only ours.
        EmailTemplate.objects.all().delete()

    def test_save_deactivates_others_with_same_name(self):
        EmailTemplate.objects.create(
            name="admin_reply", label="v1",
            subject="x", html_body="<p>x</p>", is_active=True,
        )
        EmailTemplate.objects.create(
            name="admin_reply", label="v2",
            subject="x", html_body="<p>x</p>", is_active=True,
        )
        active = EmailTemplate.objects.filter(name="admin_reply", is_active=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().label, "v2")

    def test_multiple_inactive_rows_allowed(self):
        for label in ("v1", "v2", "v3"):
            EmailTemplate.objects.create(
                name="admin_reply", label=label,
                subject="x", html_body="<p>x</p>", is_active=False,
            )
        self.assertEqual(EmailTemplate.objects.filter(name="admin_reply").count(), 3)

    def test_db_constraint_blocks_two_active_same_name(self):
        EmailTemplate.objects.create(
            name="admin_reply", label="v1",
            subject="x", html_body="<p>x</p>", is_active=True,
        )
        v2 = EmailTemplate.objects.create(
            name="admin_reply", label="v2",
            subject="x", html_body="<p>x</p>", is_active=False,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmailTemplate.objects.filter(pk=v2.pk).update(is_active=True)
                from django.db import connection
                connection.check_constraints()

    def test_active_per_name_is_independent(self):
        """Different template names can each have their own active row."""
        EmailTemplate.objects.create(
            name="admin_reply", subject="x", html_body="<p>x</p>", is_active=True,
        )
        EmailTemplate.objects.create(
            name="contact_notification", subject="x", html_body="<p>x</p>", is_active=True,
        )
        self.assertEqual(EmailTemplate.objects.filter(is_active=True).count(), 2)


class ContactMessageLanguageTests(TestCase):
    def test_default_language_is_en(self):
        m = ContactMessage.objects.create(
            name="A", email="a@x.test", subject="S", message="M",
        )
        self.assertEqual(m.language, "en")

    def test_language_field_has_20_choices(self):
        choices = ContactMessage._meta.get_field("language").choices
        self.assertEqual(len(choices), 20)

    def test_valid_language_codes(self):
        for code in ("en", "fa", "zh-hans", "ja", "ar"):
            m = ContactMessage.objects.create(
                name="A", email=f"a-{code}@x.test", subject="S", message="M",
                language=code,
            )
            self.assertEqual(m.language, code)
