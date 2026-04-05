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

    name = models.CharField(max_length=50, unique=True, choices=TEMPLATE_CHOICES)
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

    def __str__(self):
        return self.get_name_display()


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
