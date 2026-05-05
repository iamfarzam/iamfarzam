"""Tests for translation coverage and language-aware rendering."""

from django.conf import settings
from django.test import TestCase

from portfolio.email import EmailService, TEMPLATE_STRINGS, _get_defaults
from portfolio.models import EmailTemplate


SUPPORTED_LANGUAGES = {code for code, _ in settings.LANGUAGES}
TEMPLATE_NAMES = {"contact_notification", "admin_reply", "admin_new_email"}


class TemplateStringsCoverageTests(TestCase):
    """TEMPLATE_STRINGS dict integrity across all 20 languages."""

    def test_covers_all_supported_languages(self):
        self.assertEqual(set(TEMPLATE_STRINGS.keys()), SUPPORTED_LANGUAGES)

    def test_every_language_has_every_english_key(self):
        en_keys = set(TEMPLATE_STRINGS["en"].keys())
        for lang, strings in TEMPLATE_STRINGS.items():
            with self.subTest(language=lang):
                missing = en_keys - set(strings.keys())
                self.assertFalse(missing, f"missing keys: {missing}")

    def test_no_empty_translations(self):
        for lang, strings in TEMPLATE_STRINGS.items():
            for key, value in strings.items():
                with self.subTest(language=lang, key=key):
                    self.assertTrue(
                        value.strip(),
                        f"TEMPLATE_STRINGS[{lang}][{key}] is empty",
                    )


class GetDefaultsTests(TestCase):
    def test_returns_three_templates_per_language(self):
        for code in SUPPORTED_LANGUAGES:
            with self.subTest(language=code):
                self.assertEqual(set(_get_defaults(code).keys()), TEMPLATE_NAMES)

    def test_each_template_has_required_fields(self):
        for code in SUPPORTED_LANGUAGES:
            for tname, tdata in _get_defaults(code).items():
                with self.subTest(language=code, template=tname):
                    for field in ("subject", "html_body", "text_body"):
                        self.assertIn(field, tdata)
                        self.assertTrue(tdata[field], f"{tname}.{field} empty")

    def test_unknown_language_falls_back_to_english(self):
        en = _get_defaults("en")
        unknown = _get_defaults("xx-unknown")
        self.assertEqual(unknown, en)


class TranslationFieldColumnsTests(TestCase):
    """modeltranslation creates 60 columns on EmailTemplate (3 fields × 20 langs)."""

    def test_all_translation_columns_exist(self):
        all_fields = {f.name for f in EmailTemplate._meta.get_fields()}
        for code in SUPPORTED_LANGUAGES:
            suffix = code.replace("-", "_")
            for base in ("subject", "html_body", "text_body"):
                with self.subTest(column=f"{base}_{suffix}"):
                    self.assertIn(f"{base}_{suffix}", all_fields)


class CrossLanguageRenderingTests(TestCase):
    """End-to-end render test for every (template, language) combination."""

    SAMPLE_CTX = {
        "contact_notification": {
            "name": "X", "email": "x@y.test", "subject": "S", "message": "M",
        },
        "admin_reply": {
            "name": "X", "subject": "S", "reply_body": "B", "original_message": "O",
        },
        "admin_new_email": {"name": "X", "subject": "S", "body": "B"},
    }

    def test_renders_every_template_in_every_language(self):
        for code in SUPPORTED_LANGUAGES:
            for tname, ctx in self.SAMPLE_CTX.items():
                with self.subTest(template=tname, language=code):
                    s, h, t = EmailService.render_template(tname, ctx, language=code)
                    self.assertTrue(s, f"empty subject for {tname}/{code}")
                    self.assertTrue(h, f"empty html for {tname}/{code}")
                    self.assertTrue(t, f"empty text for {tname}/{code}")
