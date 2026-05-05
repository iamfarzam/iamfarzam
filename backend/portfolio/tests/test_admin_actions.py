"""Tests for admin custom actions: reply, send-test, preview."""

from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase

from portfolio.admin import EmailConfigurationForm
from portfolio.email import EmailService, _get_defaults
from portfolio.models import (
    ContactMessage, EmailConfiguration, EmailTemplate,
)


def _decorate_request_with_messages(req):
    SessionMiddleware(lambda r: None).process_request(req)
    req.session.save()
    MessageMiddleware(lambda r: None).process_request(req)


class AdminReplyFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="ad@x.test", password="x",
            is_staff=True, is_superuser=True,
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.message = ContactMessage.objects.create(
            name="Z", email="z@x.test", subject="Hello",
            message="Body", language="fa",
        )
        self.url = f"/admin/portfolio/contactmessage/{self.message.pk}/reply/"

    def test_reply_form_renders(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"reply_body", r.content)

    def test_reply_post_queues_celery_task(self):
        with patch("portfolio.tasks.send_admin_reply.delay") as MD:
            r = self.client.post(
                self.url, {"reply_subject": "Re: Hello", "reply_body": "thanks"}
            )
            self.assertEqual(r.status_code, 302)
            MD.assert_called_once()
            kwargs = MD.call_args.kwargs
            self.assertEqual(kwargs["contact_message_id"], self.message.pk)
            self.assertEqual(kwargs["reply_body"], "thanks")
            self.assertEqual(kwargs["sent_by_id"], self.admin.pk)

    def test_reply_marks_message_as_read(self):
        with patch("portfolio.tasks.send_admin_reply.delay"):
            self.client.post(self.url, {"reply_body": "x"})
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)

    def test_reply_with_empty_body_does_not_queue(self):
        with patch("portfolio.tasks.send_admin_reply.delay") as MD:
            r = self.client.post(self.url, {"reply_body": "   "})
            self.assertEqual(r.status_code, 302)
            MD.assert_not_called()

    def test_change_view_marks_message_read(self):
        url = f"/admin/portfolio/contactmessage/{self.message.pk}/change/"
        self.client.get(url)
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)


class EmailConfigurationAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="me@x.test", password="x",
            is_staff=True, is_superuser=True,
        )
        self.cfg = EmailConfiguration.objects.create(
            label="X", smtp_host="h", smtp_user="u", smtp_password="ORIG",
            from_name="N", from_email="f@x.test", is_active=True,
        )
        self.admin_obj = site._registry[EmailConfiguration]
        self.rf = RequestFactory()

    def test_password_field_is_password_input(self):
        form = EmailConfigurationForm(instance=self.cfg)
        self.assertEqual(
            type(form.fields["smtp_password"].widget).__name__, "PasswordInput",
        )

    def test_password_not_in_rendered_form(self):
        form = EmailConfigurationForm(instance=self.cfg)
        html = form["smtp_password"].as_widget()
        self.assertNotIn("ORIG", html)

    def test_blank_password_preserves_value(self):
        data = self._base_data()
        data["smtp_password"] = ""
        form = EmailConfigurationForm(data, instance=self.cfg)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.cfg.refresh_from_db()
        self.assertEqual(self.cfg.smtp_password, "ORIG")

    def test_new_password_replaces_value(self):
        data = self._base_data()
        data["smtp_password"] = "NEW"
        form = EmailConfigurationForm(data, instance=self.cfg)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.cfg.refresh_from_db()
        self.assertEqual(self.cfg.smtp_password, "NEW")

    def test_send_test_action_with_user_email(self):
        req = self.rf.post(f"/admin/portfolio/emailconfiguration/{self.cfg.pk}/send-test/")
        req.user = self.admin
        _decorate_request_with_messages(req)
        with patch.object(EmailService, "build_connection", return_value=MagicMock()), \
             patch("portfolio.admin.EmailMultiAlternatives") as MAL:
            msg = MagicMock()
            MAL.return_value = msg
            resp = self.admin_obj.send_test_email_action(req, self.cfg.pk)
            self.assertEqual(resp.status_code, 302)
            msg.send.assert_called_once()

    def test_send_test_action_without_user_email(self):
        self.admin.email = ""
        self.admin.save()
        req = self.rf.post(f"/admin/portfolio/emailconfiguration/{self.cfg.pk}/send-test/")
        req.user = self.admin
        _decorate_request_with_messages(req)
        resp = self.admin_obj.send_test_email_action(req, self.cfg.pk)
        # Should not crash; just redirect with an error message
        self.assertEqual(resp.status_code, 302)

    def _base_data(self):
        return {
            "label": self.cfg.label, "smtp_host": self.cfg.smtp_host, "smtp_port": 587,
            "smtp_user": self.cfg.smtp_user, "use_tls": True, "use_ssl": False,
            "from_name": self.cfg.from_name, "from_email": self.cfg.from_email,
            "reply_to_name": "", "reply_to_email": "", "is_active": False,
        }


class EmailTemplatePreviewActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="ad@x.test", password="x",
            is_staff=True, is_superuser=True,
        )
        for n, d in _get_defaults("en").items():
            EmailTemplate.objects.update_or_create(
                name=n, is_active=True,
                defaults={
                    "subject": d["subject"],
                    "html_body": d["html_body"],
                    "text_body": d["text_body"],
                },
            )
        self.rf = RequestFactory()
        self.admin_obj = site._registry[EmailTemplate]

    def test_preview_renders_for_each_template(self):
        for tname in ("contact_notification", "admin_reply", "admin_new_email"):
            with self.subTest(template=tname):
                tpl = EmailTemplate.objects.get(name=tname, is_active=True)
                req = self.rf.get(
                    f"/admin/portfolio/emailtemplate/{tpl.pk}/preview/?lang=en"
                )
                req.user = self.admin
                resp = self.admin_obj.preview_template(req, tpl.pk)
                resp.render()
                self.assertEqual(resp.status_code, 200)
                self.assertIn(b"<iframe", resp.content)
                self.assertIn(b"<select", resp.content)

    def test_preview_with_each_supported_language(self):
        tpl = EmailTemplate.objects.get(name="admin_reply", is_active=True)
        for lang in ("en", "fa", "ja", "ar", "zh-hans"):
            with self.subTest(language=lang):
                req = self.rf.get(
                    f"/admin/portfolio/emailtemplate/{tpl.pk}/preview/?lang={lang}"
                )
                req.user = self.admin
                resp = self.admin_obj.preview_template(req, tpl.pk)
                self.assertEqual(resp.status_code, 200)

    def test_preview_with_invalid_language_falls_back(self):
        tpl = EmailTemplate.objects.get(name="admin_reply", is_active=True)
        req = self.rf.get(f"/admin/portfolio/emailtemplate/{tpl.pk}/preview/?lang=zz")
        req.user = self.admin
        resp = self.admin_obj.preview_template(req, tpl.pk)
        self.assertEqual(resp.status_code, 200)
