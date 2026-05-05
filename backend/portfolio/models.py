from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Singleton model for personal profile information."""

    full_name = models.CharField(max_length=100)
    headline = models.CharField(max_length=200, help_text="Pipe-separated roles for the typewriter animation, e.g. Software Engineer | System Architect")
    tagline = models.CharField(max_length=300, blank=True, help_text="Short intro shown below the headline, e.g. I solve complex problems and build software that lasts.")
    bio = models.TextField()
    avatar = models.ImageField(upload_to="profile/", blank=True)
    resume = models.FileField(upload_to="profile/", blank=True)
    email = models.EmailField()
    location = models.CharField(max_length=100, blank=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    og_image = models.ImageField(upload_to="profile/", blank=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profile"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        # Enforce singleton: delete all other instances before saving.
        if not self.pk:
            Profile.objects.all().delete()
        super().save(*args, **kwargs)


class SkillCategory(models.Model):
    """Grouping for skills (e.g. Backend, ML/CV, Tools)."""

    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Skill categories"

    def __str__(self):
        return self.name


class Skill(models.Model):
    """Individual technical skill."""

    category = models.ForeignKey(SkillCategory, related_name="skills", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier for frontend")
    proficiency = models.PositiveIntegerField(default=0, help_text="0-100 proficiency level")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """Portfolio project."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=300)
    description = models.TextField(help_text="Markdown supported for detail page")
    thumbnail = models.ImageField(upload_to="projects/")
    image = models.ImageField(upload_to="projects/", blank=True)
    technologies = models.ManyToManyField(Skill, blank=True, related_name="projects")
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class Experience(models.Model):
    """Work experience entry."""

    company = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank for current position")
    description = models.TextField()
    company_url = models.URLField(blank=True)
    company_logo = models.ImageField(upload_to="experience/", blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Experience"

    def __str__(self):
        return f"{self.role} at {self.company}"


class Education(models.Model):
    """Education entry."""

    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    institution_logo = models.ImageField(upload_to="education/", blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Education"

    def __str__(self):
        return f"{self.degree} — {self.institution}"


class ContactMessage(models.Model):
    """Contact form submission."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="en",
        help_text="Locale captured from the contact form. Used to pick the email language for the reply.",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"


class EmailTemplate(models.Model):
    """Configurable HTML email template stored in the database."""

    TEMPLATE_CHOICES = [
        ("contact_notification", "Contact Notification"),
        ("admin_reply", "Admin Reply"),
        ("admin_new_email", "Admin New Email"),
    ]

    name = models.CharField(max_length=50, choices=TEMPLATE_CHOICES)
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional human-readable label to distinguish multiple templates of the same category.",
    )
    subject = models.CharField(
        max_length=200,
        help_text="Use {{ placeholders }} for dynamic content, e.g. {{ subject }}, {{ name }}",
    )
    html_body = models.TextField(
        help_text="HTML email body. Use {{ placeholders }} for dynamic content.",
    )
    text_body = models.TextField(
        blank=True,
        help_text="Plain text fallback. Auto-stripped from HTML if left blank.",
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"
        ordering = ["name", "-is_active", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(is_active=True),
                name="only_one_active_template_per_name",
            ),
        ]

    def __str__(self):
        if self.label:
            return f"{self.get_name_display()} — {self.label}"
        return self.get_name_display()

    def save(self, *args, **kwargs):
        if self.is_active:
            EmailTemplate.objects.exclude(pk=self.pk).filter(
                name=self.name, is_active=True
            ).update(is_active=False)
        super().save(*args, **kwargs)


class EmailConfiguration(models.Model):
    """SMTP credentials and sender identity used for outgoing email.

    Multiple rows are allowed (e.g. one per provider or environment), but only
    one row may have ``is_active=True`` at a time. Outgoing admin email picks
    the active row; if no active row exists the code falls back to settings.
    """

    label = models.CharField(
        max_length=100,
        help_text="Human-readable name for this configuration (e.g. 'Postmark — Production').",
    )

    # SMTP transport
    smtp_host = models.CharField(max_length=200)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_user = models.CharField(max_length=200)
    smtp_password = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stored as-is. Leave blank in the form to keep the existing value.",
    )
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)

    # Sender identity — what the recipient sees in the From: header.
    from_name = models.CharField(
        max_length=100,
        help_text="Display name shown to recipients, e.g. 'Farzam Mehdi'.",
    )
    from_email = models.EmailField(
        help_text=(
            "Address shown in the From: header. Most providers require this to "
            "match the SMTP user. If you want replies to land in a different "
            "inbox, use the Reply-To fields below."
        ),
    )

    # Optional Reply-To. When set, mail clients send replies here instead of from_email.
    reply_to_name = models.CharField(max_length=100, blank=True)
    reply_to_email = models.EmailField(
        blank=True,
        help_text="Optional. Where recipient replies should land.",
    )

    is_active = models.BooleanField(
        default=False,
        help_text="Only one configuration can be active at a time.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "label"]
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="only_one_active_email_configuration",
            ),
        ]

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        # Enforce single-active: deactivate other rows when this one is activated.
        if self.is_active:
            EmailConfiguration.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    @property
    def from_identity(self):
        return f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email

    @property
    def reply_to_identity(self):
        if not self.reply_to_email:
            return ""
        return f"{self.reply_to_name} <{self.reply_to_email}>" if self.reply_to_name else self.reply_to_email


class SentEmail(models.Model):
    """Audit log for emails sent from the admin panel."""

    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=200)
    body_preview = models.TextField()
    from_identity = models.CharField(max_length=200, help_text="Display name and email")
    contact_message = models.ForeignKey(
        ContactMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Sent Email"
        verbose_name_plural = "Sent Emails"

    def __str__(self):
        return f"{self.subject} → {self.recipient_email}"
