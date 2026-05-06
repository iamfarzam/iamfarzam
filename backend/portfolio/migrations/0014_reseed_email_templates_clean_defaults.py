"""One-shot reseed of every EmailTemplate row to the cleaned defaults.

Unlike 0012, which only fills empty per-language columns, this migration
**overwrites** every (template × language) column from ``_get_defaults`` so
the redesigned templates reach prod. Run once.

If you have customized any template through the admin and want to keep
those edits, fake-apply this migration instead:
    python manage.py migrate portfolio 0014 --fake
"""

from django.conf import settings
from django.db import migrations


def reseed_all(apps, schema_editor):
    EmailTemplate = apps.get_model("portfolio", "EmailTemplate")

    from portfolio.email import _get_defaults

    en_defaults = _get_defaults("en")

    for template_name, en_data in en_defaults.items():
        row, _ = EmailTemplate.objects.get_or_create(
            name=template_name,
            defaults={
                "subject": en_data["subject"],
                "html_body": en_data["html_body"],
                "text_body": en_data["text_body"],
                "is_active": True,
            },
        )

        updates = {
            "subject": en_data["subject"],
            "html_body": en_data["html_body"],
            "text_body": en_data["text_body"],
        }

        for lang_code, _label in settings.LANGUAGES:
            suffix = lang_code.replace("-", "_")
            data = _get_defaults(lang_code).get(template_name, {})
            for field in ("subject", "html_body", "text_body"):
                col = f"{field}_{suffix}"
                if hasattr(row, col):
                    updates[col] = data.get(field, "")

        EmailTemplate.objects.filter(pk=row.pk).update(**updates)


def noop_reverse(apps, schema_editor):
    # Reversing would mean restoring the previous template content, which
    # we do not retain. Refuse rather than wipe rows.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0013_experience_location_ar_experience_location_bn_and_more"),
    ]

    operations = [
        migrations.RunPython(reseed_all, noop_reverse),
    ]
