from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="tagline",
            field=models.CharField(
                blank=True,
                help_text="Short intro shown below the headline, e.g. I solve complex problems and build software that lasts.",
                max_length=300,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="headline",
            field=models.CharField(
                help_text="Pipe-separated roles for the typewriter animation, e.g. Software Engineer | System Architect",
                max_length=200,
            ),
        ),
    ]
