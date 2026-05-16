from django.db import migrations, models
from django.db.models import F


def backfill_updated_at(apps, schema_editor):
    Project = apps.get_model("portfolio", "Project")
    Project.objects.update(updated_at=F("created_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0014_reseed_email_templates_clean_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(backfill_updated_at, migrations.RunPython.noop),
    ]
