"""Tests for portfolio.email.EmailService — class-based email orchestrator."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from portfolio.email import EmailService, HTMLStripper, _get_defaults
from portfolio.models import EmailConfiguration, EmailTemplate


class EmailServiceIdentityTests(TestCase):
    """Sender identity resolution: active config wins, settings fall back."""

    def test_get_active_config_returns_active_row(self):
        cfg = EmailConfiguration.objects.create(
            label="A", smtp_host="h", smtp_user="u", smtp_password="p",
            from_name="N", from_email="a@x.test", is_active=True,
        )
        self.assertEqual(EmailService.get_active_config().pk, cfg.pk)

    def test_get_active_config_returns_none_when_no_active(self):
        EmailConfiguration.objects.create(
            label="A", smtp_host="h", smtp_user="u", smtp_password="p",
            from_name="N", from_email="a@x.test", is_active=False,
        )
        self.assertIsNone(EmailService.get_active_config())

    def test_get_admin_identity_uses_active_config(self):
        EmailConfiguration.objects.create(
            label="A", smtp_host="h", smtp_user="u", smtp_password="p",
            from_name="Real Name", from_email="real@x.test", is_active=True,
        )
        self.assertEqual(EmailService.get_admin_identity(), "Real Name <real@x.test>")

    @override_settings(ADMIN_EMAIL_NAME="Fallback", ADMIN_FROM_EMAIL="fb@x.test")
    def test_get_admin_identity_falls_back_to_settings(self):
        self.assertEqual(EmailService.get_admin_identity(), "Fallback <fb@x.test>")

    def test_get_admin_reply_to_uses_active_config(self):
        EmailConfiguration.objects.create(
            label="A", smtp_host="h", smtp_user="u", smtp_password="p",
            from_name="N", from_email="a@x.test",
            reply_to_name="Reply Box", reply_to_email="rep@x.test",
            is_active=True,
        )
        self.assertEqual(EmailService.get_admin_reply_to(), "Reply Box <rep@x.test>")

    def test_get_admin_reply_to_empty_without_active(self):
        self.assertEqual(EmailService.get_admin_reply_to(), "")

    @override_settings(SYSTEM_EMAIL_NAME="System", DEFAULT_FROM_EMAIL="noreply@x.test")
    def test_get_system_identity(self):
        self.assertEqual(EmailService.get_system_identity(), "System <noreply@x.test>")


class EmailServiceSendTests(TestCase):
    """Verifies send() routes through active config when requested."""

    def setUp(self):
        self.cfg = EmailConfiguration.objects.create(
            label="A", smtp_host="h", smtp_user="u", smtp_password="p",
            from_name="Real", from_email="real@x.test",
            reply_to_name="Reply", reply_to_email="rep@x.test", is_active=True,
        )

    def test_send_with_active_config_overrides_from(self):
        with patch("portfolio.email.EmailMultiAlternatives") as MAL, \
             patch.object(EmailService, "build_connection", return_value=MagicMock()):
            msg = MagicMock()
            MAL.return_value = msg
            EmailService.send(
                "S", "<p>h</p>", "t", "Ignored <i@x.test>", "to@x.test",
                use_active_config=True,
            )
            kwargs = MAL.call_args.kwargs
            self.assertEqual(kwargs["from_email"], "Real <real@x.test>")
            self.assertEqual(kwargs["reply_to"], ["Reply <rep@x.test>"])
            msg.send.assert_called_once()

    def test_send_without_active_config_uses_given_from(self):
        EmailConfiguration.objects.all().delete()
        with patch("portfolio.email.EmailMultiAlternatives") as MAL, \
             patch("portfolio.email.get_connection") as GC:
            msg = MagicMock()
            MAL.return_value = msg
            EmailService.send(
                "S", "<p>h</p>", "t", "Pass <p@x.test>", "to@x.test",
                use_active_config=False,
            )
            kwargs = MAL.call_args.kwargs
            self.assertEqual(kwargs["from_email"], "Pass <p@x.test>")
            self.assertIsNone(kwargs["reply_to"])
            GC.assert_not_called()
            msg.send.assert_called_once()

    def test_send_use_active_config_falls_through_when_none_active(self):
        self.cfg.is_active = False
        self.cfg.save()
        with patch("portfolio.email.EmailMultiAlternatives") as MAL, \
             patch("portfolio.email.get_connection") as GC:
            msg = MagicMock()
            MAL.return_value = msg
            EmailService.send(
                "S", "<p>h</p>", "t", "Pass <p@x.test>", "to@x.test",
                use_active_config=True,
            )
            kwargs = MAL.call_args.kwargs
            self.assertEqual(kwargs["from_email"], "Pass <p@x.test>")
            GC.assert_not_called()


class EmailServiceConnectionTests(TestCase):
    def test_build_connection_returns_smtp_backend(self):
        cfg = EmailConfiguration.objects.create(
            label="A", smtp_host="h", smtp_port=2525, smtp_user="u", smtp_password="p",
            from_name="N", from_email="a@x.test",
        )
        conn = EmailService.build_connection(cfg)
        self.assertIn("smtp", conn.__class__.__module__)


class EmailServiceTemplateRenderingTests(TestCase):
    """render_template: DB row first, fallback to defaults, language override."""

    def setUp(self):
        # Clear migration-seeded rows so each test starts from a known state.
        EmailTemplate.objects.all().delete()
        d = _get_defaults("en")["admin_reply"]
        fa = _get_defaults("fa")["admin_reply"]
        EmailTemplate.objects.create(
            name="admin_reply", is_active=True,
            subject=d["subject"], subject_en=d["subject"], subject_fa=fa["subject"],
            html_body=d["html_body"], html_body_en=d["html_body"], html_body_fa=fa["html_body"],
            text_body=d["text_body"], text_body_en=d["text_body"], text_body_fa=fa["text_body"],
        )

    def _ctx(self):
        return {"name": "Ali", "subject": "X", "reply_body": "hi", "original_message": "orig"}

    def test_renders_english_by_default(self):
        s, h, _ = EmailService.render_template("admin_reply", self._ctx(), language="en")
        self.assertEqual(s, "Re: X")
        self.assertIn("Hello Ali", h)

    def test_renders_persian_when_requested(self):
        s, h, _ = EmailService.render_template("admin_reply", self._ctx(), language="fa")
        self.assertIn("پاسخ", s)
        self.assertIn("سلام", h)

    def test_falls_back_to_english_for_missing_locale(self):
        # Samoan translation is filled in TEMPLATE_STRINGS but not in DB row,
        # so modeltranslation falls back through MODELTRANSLATION_FALLBACK_LANGUAGES → en
        s, _, _ = EmailService.render_template("admin_reply", self._ctx(), language="sm")
        self.assertEqual(s, "Re: X")

    def test_falls_back_to_defaults_when_no_db_row(self):
        EmailTemplate.objects.filter(name="admin_reply").delete()
        s, _, _ = EmailService.render_template("admin_reply", self._ctx(), language="fa")
        self.assertIn("پاسخ", s)

    def test_render_template_injects_branding(self):
        s, h, _ = EmailService.render_template(
            "admin_reply", self._ctx(), language="en"
        )
        # brand_name comes from Profile (none in test DB) → settings.SYSTEM_EMAIL_NAME
        self.assertIn("&copy;", h)


class HTMLStripperTests(TestCase):
    def test_strips_tags(self):
        self.assertEqual(HTMLStripper.to_text("<p>hi <b>there</b></p>"), "hi there")

    def test_collapses_blank_lines(self):
        out = HTMLStripper.to_text("<p>a</p>\n\n\n\n<p>b</p>")
        self.assertNotIn("\n\n\n", out)

    def test_handles_empty_input(self):
        self.assertEqual(HTMLStripper.to_text(""), "")
