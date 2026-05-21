"""Tests for model invariants: single-active rules, defaults, choices."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from PIL import Image

from portfolio.models import (
    ContactMessage,
    EmailConfiguration,
    EmailTemplate,
    OG_MAX_HEIGHT,
    OG_MAX_WIDTH,
    Profile,
)


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


def _png_upload(name, width, height):
    img = Image.new("RGBA", (width, height), (255, 0, 0, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class ProfileOgImageResizeTests(TestCase):
    """og_image is downscaled to fit 1200x630 on save, preserving aspect."""

    def _profile(self, og_upload):
        return Profile.objects.create(
            full_name="N", headline="H", bio="B", email="x@x.test",
            og_image=og_upload,
        )

    def _dims(self, profile):
        profile.og_image.open("rb")
        try:
            with Image.open(profile.og_image) as img:
                return img.width, img.height
        finally:
            profile.og_image.close()

    def test_oversized_image_is_downscaled(self):
        p = self._profile(_png_upload("og.png", 4000, 3000))
        w, h = self._dims(p)
        self.assertLessEqual(w, OG_MAX_WIDTH)
        self.assertLessEqual(h, OG_MAX_HEIGHT)
        # Aspect preserved: 4000/3000 == w/h within 1px rounding.
        self.assertAlmostEqual(w / h, 4000 / 3000, places=2)

    def test_square_image_fits_within_short_side(self):
        p = self._profile(_png_upload("og.png", 2000, 2000))
        w, h = self._dims(p)
        self.assertEqual(w, OG_MAX_HEIGHT)
        self.assertEqual(h, OG_MAX_HEIGHT)

    def test_already_small_image_is_untouched(self):
        p = self._profile(_png_upload("og.png", 800, 400))
        w, h = self._dims(p)
        self.assertEqual((w, h), (800, 400))

    def test_exact_size_image_is_untouched(self):
        p = self._profile(_png_upload("og.png", OG_MAX_WIDTH, OG_MAX_HEIGHT))
        w, h = self._dims(p)
        self.assertEqual((w, h), (OG_MAX_WIDTH, OG_MAX_HEIGHT))


class ProfileBrandingFieldsTests(TestCase):
    """logo and favicon are real ImageFields that can be stored and read back."""

    def test_logo_and_favicon_persist(self):
        p = Profile.objects.create(
            full_name="N", headline="H", bio="B", email="x@x.test",
            logo=_png_upload("logo.png", 400, 100),
            favicon=_png_upload("favicon.png", 512, 512),
        )
        p.refresh_from_db()
        self.assertTrue(p.logo.name.endswith(".png"))
        self.assertTrue(p.favicon.name.endswith(".png"))

    def test_branding_fields_optional(self):
        p = Profile.objects.create(
            full_name="N", headline="H", bio="B", email="x@x.test",
        )
        self.assertFalse(bool(p.logo))
        self.assertFalse(bool(p.favicon))
