"""Add translation columns for fa (Persian)."""

from django.db import migrations, models

_TRANSLATED_FIELDS = [
    ("profile", "headline", lambda: models.CharField(max_length=200, null=True)),
    ("profile", "tagline", lambda: models.CharField(max_length=300, blank=True, null=True)),
    ("profile", "bio", lambda: models.TextField(null=True)),
    ("profile", "meta_title", lambda: models.CharField(max_length=60, blank=True, null=True)),
    ("profile", "meta_description", lambda: models.CharField(max_length=160, blank=True, null=True)),
    ("skillcategory", "name", lambda: models.CharField(max_length=50, null=True)),
    ("skill", "name", lambda: models.CharField(max_length=50, null=True)),
    ("project", "title", lambda: models.CharField(max_length=200, null=True)),
    ("project", "summary", lambda: models.CharField(max_length=300, null=True)),
    ("project", "description", lambda: models.TextField(null=True)),
    ("experience", "role", lambda: models.CharField(max_length=200, null=True)),
    ("experience", "description", lambda: models.TextField(null=True)),
    ("education", "degree", lambda: models.CharField(max_length=200, null=True)),
    ("education", "field_of_study", lambda: models.CharField(max_length=200, blank=True, null=True)),
    ("education", "description", lambda: models.TextField(blank=True, null=True)),
]


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0004_add_new_language_translation_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name=model_name,
            name=f"{field_name}_fa",
            field=field_factory(),
        )
        for model_name, field_name, field_factory in _TRANSLATED_FIELDS
    ]
