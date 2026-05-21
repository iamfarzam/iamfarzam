from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0015_project_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Header brand mark. PNG recommended; replaces the site title text when set.",
                upload_to="profile/",
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="favicon",
            field=models.ImageField(
                blank=True,
                help_text="Browser tab icon. Upload a square PNG (512x512 is plenty); browsers auto-scale.",
                upload_to="profile/",
            ),
        ),
    ]
