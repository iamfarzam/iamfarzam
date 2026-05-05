"""Hydrate per-language columns of EmailTemplate from email._get_defaults.

This data migration walks every supported language in settings.LANGUAGES
and writes the localized subject/html_body/text_body into the corresponding
modeltranslation columns (e.g. subject_fa, html_body_zh_hans). The base
columns (subject, html_body, text_body) are left as the English content for
modeltranslation's ultimate fallback path.

It only writes a per-language column if it is currently empty, so admins
who have hand-edited a language tab keep their work.
"""

from django.conf import settings
from django.db import migrations


def hydrate_translations(apps, schema_editor):
    EmailTemplate = apps.get_model("portfolio", "EmailTemplate")

    # Lazy import — settings + app registry are ready at this point.
    from portfolio.email import _get_defaults

    for lang_code, _ in settings.LANGUAGES:
        suffix = lang_code.replace("-", "_")
        defaults = _get_defaults(lang_code)

        for template_name, data in defaults.items():
            try:
                row = EmailTemplate.objects.get(name=template_name)
            except EmailTemplate.DoesNotExist:
                continue

            updates = {}
            for field in ("subject", "html_body", "text_body"):
                col = f"{field}_{suffix}"
                if hasattr(row, col) and not getattr(row, col):
                    updates[col] = data[field]

            if updates:
                EmailTemplate.objects.filter(pk=row.pk).update(**updates)


def noop_reverse(apps, schema_editor):
    # Reversing would clear admin-edited translations — refuse.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0011_contactmessage_language_emailtemplate_html_body_ar_and_more"),
    ]

    operations = [
        migrations.RunPython(hydrate_translations, noop_reverse),
    ]
