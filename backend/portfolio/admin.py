import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from modeltranslation.admin import TabbedTranslationAdmin, TranslationTabularInline
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import (
    ContactMessage,
    Education,
    EmailConfiguration,
    EmailTemplate,
    Experience,
    Profile,
    Project,
    SentEmail,
    Skill,
    SkillCategory,
)

logger = logging.getLogger(__name__)


def project_version_environment(request):
    """Unfold ENVIRONMENT callback — renders a chip with the SemVer version."""
    from django.conf import settings
    return [f"v{settings.PROJECT_VERSION}", "info"]


def unread_messages_count(request):
    """Badge callback for sidebar unread message count."""
    try:
        count = ContactMessage.objects.filter(is_read=False).count()
        return count if count > 0 else None
    except Exception:
        logger.exception("Failed to query unread message count")
        return None


def site_favicons(request):
    """Unfold SITE_FAVICONS callback — render <link rel="icon"> in admin <head>.

    Returns a single-entry list pointing at Profile.favicon when uploaded.
    Returns an empty list otherwise, so Unfold emits no favicon link and the
    browser falls back to its own default behavior.
    """
    try:
        profile = Profile.objects.only("favicon").first()
        if profile and profile.favicon:
            return [{
                "rel": "icon",
                "type": "image/png",
                "href": profile.favicon.url,
            }]
    except Exception:
        logger.exception("Failed to resolve site favicon")
    return []


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@admin.register(Profile)
class ProfileAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ["full_name", "headline", "email"]
    fieldsets = [
        (
            "Personal Information",
            {
                "fields": (
                    "full_name",
                    "headline",
                    "tagline",
                    "bio",
                    "avatar",
                    "resume",
                    "email",
                    "location",
                ),
                "description": "Core profile details displayed across the portfolio.",
            },
        ),
        (
            "Branding",
            {
                "fields": ("logo", "favicon"),
                "classes": ["collapse"],
                "description": (
                    "Logo replaces the site title text in the header when set. "
                    "Favicon is the browser tab icon (upload a square PNG; browsers auto-scale)."
                ),
            },
        ),
        (
            "Social Links",
            {
                "fields": ("github_url", "linkedin_url", "twitter_url", "website_url"),
                "classes": ["collapse"],
            },
        ),
        (
            "SEO",
            {
                "fields": ("meta_title", "meta_description", "og_image"),
                "classes": ["collapse"],
                "description": "Search engine optimization fields for the homepage.",
            },
        ),
    ]

    def has_add_permission(self, request):
        return not Profile.objects.exists()


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

class SkillInline(TabularInline, TranslationTabularInline):
    model = Skill
    extra = 1
    fields = ["name", "icon", "proficiency", "order", "is_active"]
    ordering = ["order"]


@admin.register(SkillCategory)
class SkillCategoryAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "skill_count", "order", "show_status"]
    list_editable = ["order"]
    list_filter_submit = True
    inlines = [SkillInline]

    @display(description="Skills")
    def skill_count(self, obj):
        return obj.skills.filter(is_active=True).count()

    @display(
        description="Status",
        label={
            True: "success",
            False: "danger",
        },
    )
    def show_status(self, obj):
        return obj.is_active


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@admin.register(Project)
class ProjectAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = [
        "title",
        "show_featured",
        "tech_list",
        "order",
        "show_status",
    ]
    list_editable = ["order"]
    list_filter = ["is_featured", "is_active", "technologies"]
    list_filter_submit = True
    search_fields = ["title", "summary"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["technologies"]
    fieldsets = [
        (
            "Project Details",
            {
                "fields": (
                    "title",
                    "slug",
                    "summary",
                    "description",
                    "technologies",
                ),
            },
        ),
        (
            "Media",
            {
                "fields": ("thumbnail", "image"),
            },
        ),
        (
            "Links",
            {
                "fields": ("github_url", "live_url"),
                "classes": ["collapse"],
            },
        ),
        (
            "Visibility",
            {
                "fields": ("is_featured", "is_active", "order"),
            },
        ),
    ]

    @display(
        description="Featured",
        label={
            True: "info",
            False: "",
        },
    )
    def show_featured(self, obj):
        return obj.is_featured

    @display(
        description="Status",
        label={
            True: "success",
            False: "danger",
        },
    )
    def show_status(self, obj):
        return obj.is_active

    @display(description="Technologies")
    def tech_list(self, obj):
        techs = obj.technologies.all()[:4]
        names = ", ".join(t.name for t in techs)
        if obj.technologies.count() > 4:
            names += f" +{obj.technologies.count() - 4}"
        return names or "—"


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

@admin.register(Experience)
class ExperienceAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = [
        "role",
        "company",
        "date_range",
        "order",
        "show_status",
    ]
    list_editable = ["order"]
    list_filter = ["is_active"]
    list_filter_submit = True
    fieldsets = [
        (
            "Position",
            {
                "fields": ("role", "company", "company_url", "company_logo", "location"),
            },
        ),
        (
            "Duration",
            {
                "fields": ("start_date", "end_date"),
                "description": "Leave end date empty for current position.",
            },
        ),
        (
            "Details",
            {
                "fields": ("description",),
            },
        ),
        (
            "Visibility",
            {
                "fields": ("is_active", "order"),
            },
        ),
    ]

    @display(description="Period")
    def date_range(self, obj):
        start = obj.start_date.strftime("%b %Y")
        end = obj.end_date.strftime("%b %Y") if obj.end_date else "Present"
        return f"{start} — {end}"

    @display(
        description="Status",
        label={
            True: "success",
            False: "danger",
        },
    )
    def show_status(self, obj):
        return obj.is_active


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

@admin.register(Education)
class EducationAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = [
        "degree",
        "institution",
        "date_range",
        "order",
        "show_status",
    ]
    list_editable = ["order"]
    list_filter = ["is_active"]
    list_filter_submit = True
    fieldsets = [
        (
            "Academic Details",
            {
                "fields": (
                    "degree",
                    "field_of_study",
                    "institution",
                    "institution_logo",
                ),
            },
        ),
        (
            "Duration",
            {
                "fields": ("start_date", "end_date"),
            },
        ),
        (
            "Details",
            {
                "fields": ("description",),
            },
        ),
        (
            "Visibility",
            {
                "fields": ("is_active", "order"),
            },
        ),
    ]

    @display(description="Period")
    def date_range(self, obj):
        start = obj.start_date.strftime("%b %Y")
        end = obj.end_date.strftime("%b %Y") if obj.end_date else "Present"
        return f"{start} — {end}"

    @display(
        description="Status",
        label={
            True: "success",
            False: "danger",
        },
    )
    def show_status(self, obj):
        return obj.is_active


# ---------------------------------------------------------------------------
# Contact Messages (with reply + send email actions)
# ---------------------------------------------------------------------------

@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = [
        "subject",
        "name",
        "email",
        "reply_count",
        "show_read_status",
        "created_at",
    ]
    list_filter = ["is_read"]
    list_filter_submit = True
    readonly_fields = ["name", "email", "subject", "message", "language", "created_at", "reply_history"]
    fieldsets = [
        (
            "Sender",
            {
                "fields": ("name", "email", "language"),
            },
        ),
        (
            "Message",
            {
                "fields": ("subject", "message"),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_read", "created_at"),
            },
        ),
        (
            "Reply History",
            {
                "fields": ("reply_history",),
                "classes": ["collapse"],
            },
        ),
    ]
    actions_detail = ["reply_to_message"]

    @display(
        description="Status",
        label={
            "Unread": "warning",
            "Read": "success",
        },
    )
    def show_read_status(self, obj):
        return "Read" if obj.is_read else "Unread"

    @display(description="Replies")
    def reply_count(self, obj):
        count = obj.replies.count()
        return count if count > 0 else "—"

    def reply_history(self, obj):
        replies = obj.replies.select_related("sent_by").all()
        if not replies:
            return "No replies yet."
        rows = []
        for r in replies:
            sent_by = r.sent_by.get_full_name() or r.sent_by.username if r.sent_by else "System"
            rows.append(
                format_html(
                    '<div style="margin-bottom:12px;padding:12px;background:#f8fafc;border-radius:6px;border-left:3px solid #3b82f6;">'
                    '<div style="font-size:12px;color:#666;margin-bottom:4px;">'
                    '{} &mdash; by {} &mdash; via {}'
                    '</div>'
                    '<div style="font-weight:600;margin-bottom:4px;">{}</div>'
                    '<div style="color:#333;">{}</div>'
                    '</div>',
                    r.sent_at.strftime("%b %d, %Y %H:%M"),
                    sent_by,
                    r.from_identity,
                    r.subject,
                    r.body_preview,
                )
            )
        return format_html("{}" * len(rows), *rows)
    reply_history.short_description = "Reply History"

    @action(description="Reply to this message", url_path="reply")
    def reply_to_message(self, request, object_id):
        obj = self.model.objects.get(pk=object_id)

        if request.method == "POST":
            reply_subject = request.POST.get("reply_subject", "").strip()
            reply_body = request.POST.get("reply_body", "").strip()

            if not reply_body:
                messages.error(request, "Reply body cannot be empty.")
                return HttpResponseRedirect(request.get_full_path())

            try:
                from .tasks import send_admin_reply
                send_admin_reply.delay(
                    contact_message_id=obj.pk,
                    reply_subject=reply_subject,
                    reply_body=reply_body,
                    sent_by_id=request.user.pk,
                )
                messages.success(request, f"Reply queued for delivery to {obj.email}")
            except Exception as exc:
                logger.exception("Failed to queue reply for message %s", obj.pk)
                messages.error(request, f"Failed to queue reply: {exc}")

            if not obj.is_read:
                obj.is_read = True
                obj.save(update_fields=["is_read"])
            return HttpResponseRedirect(
                reverse("admin:portfolio_contactmessage_change", args=[obj.pk])
            )

        # GET — render the reply form
        context = self.admin_site.each_context(request)
        context.update({
            "title": f"Reply to: {obj.subject}",
            "object": obj,
            "opts": self.model._meta,
            "original": obj,
        })

        from django.template.response import TemplateResponse
        return TemplateResponse(
            request,
            "admin/portfolio/contactmessage/reply.html",
            context,
        )

    def has_add_permission(self, request):
        return False

    # Auto-mark as read when admin opens the message
    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.model.objects.get(pk=object_id)
        if not obj.is_read:
            obj.is_read = True
            obj.save(update_fields=["is_read"])
        return super().change_view(request, object_id, form_url, extra_context)


# ---------------------------------------------------------------------------
# Email Templates
# ---------------------------------------------------------------------------

SAMPLE_CONTEXTS = {
    "contact_notification": {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "subject": "Project inquiry",
        "message": "Hi Farzam,\n\nWe're scoping a small back-end project and I'd like to talk to you about it. Do you have time next week for a short call?\n\nJane",
    },
    "admin_reply": {
        "name": "Jane",
        "subject": "Project inquiry",
        "reply_body": "Thanks for the note. Next Tuesday afternoon works for me. I'll send a calendar invite shortly.\n\nA quick question before we talk: what's the rough timeline you have in mind?",
        "original_message": "Hi Farzam,\n\nWe're scoping a small back-end project and I'd like to talk to you about it. Do you have time next week for a short call?\n\nJane",
    },
    "admin_new_email": {
        "name": "Jane",
        "subject": "Following up",
        "body": "Following up on our conversation last week. The contract draft is attached, and I've added comments where I had questions. Happy to discuss any of it whenever you have time.",
    },
}


@admin.register(EmailTemplate)
class EmailTemplateAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "label", "subject", "show_status", "updated_at"]
    list_filter = ["name", "is_active"]
    list_filter_submit = True
    actions_detail = ["preview_template", "reset_to_defaults"]
    readonly_fields = ["updated_at", "placeholder_help"]
    fieldsets = [
        (
            "Template Identity",
            {
                "fields": ("name", "label", "subject"),
                "description": (
                    "Multiple templates per category are allowed, but only one "
                    "can be active at a time. The 'label' field helps you tell "
                    "drafts apart in the list view."
                ),
            },
        ),
        (
            "HTML Body",
            {
                "fields": ("html_body",),
                "description": "The main HTML email template. Use {{ placeholders }} for dynamic content.",
            },
        ),
        (
            "Plain Text Fallback",
            {
                "fields": ("text_body",),
                "classes": ["collapse"],
                "description": "Optional plain text version. Auto-generated from HTML if left blank.",
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "updated_at"),
            },
        ),
        (
            "Placeholder Reference",
            {
                "fields": ("placeholder_help",),
                "classes": ["collapse"],
            },
        ),
    ]

    @display(
        description="Status",
        label={
            True: "success",
            False: "danger",
        },
    )
    def show_status(self, obj):
        return obj.is_active

    @action(description="Preview rendered email", url_path="preview")
    def preview_template(self, request, object_id):
        from django.conf import settings
        from django.template.response import TemplateResponse

        from .email import EmailService

        tpl = self.model.objects.get(pk=object_id)
        active_language = request.GET.get("lang") or "en"
        valid_codes = {code for code, _ in settings.LANGUAGES}
        if active_language not in valid_codes:
            active_language = "en"

        sample_context = SAMPLE_CONTEXTS.get(tpl.name, {})
        try:
            subject, html, text = EmailService.render_template(
                tpl.name, sample_context, language=active_language
            )
        except Exception as exc:
            logger.exception("Failed to render preview for template %s", tpl.pk)
            messages.error(request, f"Preview failed: {exc}")
            return HttpResponseRedirect(
                reverse("admin:portfolio_emailtemplate_change", args=[tpl.pk])
            )

        import json
        context = self.admin_site.each_context(request)
        context.update({
            "title": f"Preview: {tpl.get_name_display()}",
            "template": tpl,
            "opts": self.model._meta,
            "original": tpl,
            "active_language": active_language,
            "language_choices": settings.LANGUAGES,
            "rendered_subject": subject,
            "rendered_html": html,
            "rendered_text": text,
            "sample_context_pretty": json.dumps(sample_context, indent=2, ensure_ascii=False),
        })
        return TemplateResponse(
            request,
            "admin/portfolio/emailtemplate/preview.html",
            context,
        )

    @action(description="Reset to defaults", url_path="reset-defaults")
    def reset_to_defaults(self, request, object_id):
        """Overwrite this row's subject/html/text in every language column
        with the values from `email._get_defaults`. Wipes admin edits for
        this row only — other templates are untouched."""
        from django.conf import settings

        from .email import _get_defaults

        tpl = self.model.objects.get(pk=object_id)
        en_data = _get_defaults("en").get(tpl.name)
        if not en_data:
            messages.error(request, f"No defaults defined for {tpl.name!r}.")
            return HttpResponseRedirect(
                reverse("admin:portfolio_emailtemplate_change", args=[tpl.pk])
            )

        updates = {
            "subject": en_data["subject"],
            "html_body": en_data["html_body"],
            "text_body": en_data["text_body"],
        }
        for lang_code, _label in settings.LANGUAGES:
            suffix = lang_code.replace("-", "_")
            data = _get_defaults(lang_code).get(tpl.name, {})
            for field in ("subject", "html_body", "text_body"):
                col = f"{field}_{suffix}"
                if hasattr(tpl, col):
                    updates[col] = data.get(field, "")

        self.model.objects.filter(pk=tpl.pk).update(**updates)
        messages.success(
            request,
            f"Reset {tpl.get_name_display()!r} to defaults across all languages.",
        )
        return HttpResponseRedirect(
            reverse("admin:portfolio_emailtemplate_change", args=[tpl.pk])
        )

    def placeholder_help(self, obj):
        specific = {
            "contact_notification": "{{ name }}, {{ email }}, {{ subject }}, {{ message }}",
            "admin_reply": "{{ subject }}, {{ reply_body }}, {{ original_message }}, {{ name }}",
            "admin_new_email": "{{ subject }}, {{ body }}, {{ name }}",
        }
        branding = "{{ brand_name }}, {{ brand_email }}, {{ brand_website }}, {{ brand_github }}, {{ brand_linkedin }}"
        specific_text = specific.get(obj.name, "No specific placeholders for this template.")
        return format_html(
            '<div style="padding:14px;background:#f0f9ff;border-radius:6px;border:1px solid #bae6fd;font-size:13px;line-height:1.6;">'
            '<strong>Template-specific:</strong> {}<br>'
            '<strong>Branding (auto-injected from Profile):</strong> {}'
            '</div>',
            specific_text,
            branding,
        )
    placeholder_help.short_description = "Available Placeholders"


# ---------------------------------------------------------------------------
# Email Configurations (SMTP credentials + sender identity)
# ---------------------------------------------------------------------------

class EmailConfigurationForm(forms.ModelForm):
    """Form that masks the SMTP password and never renders the stored value.

    Leaving the password field blank on edit keeps the existing value; typing a
    new value replaces it.
    """

    smtp_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to keep the existing password.",
    )

    class Meta:
        model = EmailConfiguration
        fields = "__all__"

    def clean_smtp_password(self):
        new_value = self.cleaned_data.get("smtp_password", "")
        if not new_value and self.instance.pk:
            return self.instance.smtp_password
        return new_value


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(ModelAdmin):
    form = EmailConfigurationForm
    list_display = ["label", "from_email", "smtp_host", "show_active"]
    list_filter = ["is_active"]
    list_filter_submit = True
    search_fields = ["label", "from_email", "smtp_host"]
    actions_detail = ["send_test_email_action"]
    fieldsets = [
        (
            "Identity",
            {
                "fields": ("label", "from_name", "from_email"),
                "description": (
                    "What recipients see in the From: header. The from_email "
                    "usually has to match the SMTP user — most providers reject "
                    "messages otherwise."
                ),
            },
        ),
        (
            "Reply-To (optional)",
            {
                "fields": ("reply_to_name", "reply_to_email"),
                "description": (
                    "If set, replies from recipients land here instead of the "
                    "from_email. Useful when the SMTP account is a noreply "
                    "address but you want replies to reach a real inbox."
                ),
            },
        ),
        (
            "SMTP transport",
            {
                "fields": (
                    "smtp_host",
                    "smtp_port",
                    "smtp_user",
                    "smtp_password",
                    "use_tls",
                    "use_ssl",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active",),
                "description": "Only one configuration can be active at a time.",
            },
        ),
    ]

    @display(
        description="Active",
        label={
            True: "success",
            False: "",
        },
    )
    def show_active(self, obj):
        return obj.is_active

    @action(description="Send a test email to your account email", url_path="send-test")
    def send_test_email_action(self, request, object_id):
        from .email import EmailService

        config = self.model.objects.get(pk=object_id)
        recipient = request.user.email
        if not recipient:
            messages.error(
                request,
                "Your admin user has no email address set — cannot send a test.",
            )
            return HttpResponseRedirect(request.get_full_path())

        try:
            connection = EmailService.build_connection(config)
            msg = EmailMultiAlternatives(
                subject=f"Test from {config.label}",
                body=(
                    "This is a test email sent from the admin panel to verify "
                    "the SMTP configuration is working."
                ),
                from_email=config.from_identity,
                to=[recipient],
                reply_to=[config.reply_to_identity] if config.reply_to_identity else None,
                connection=connection,
            )
            msg.send(fail_silently=False)
            messages.success(request, f"Test email sent to {recipient}.")
        except Exception as exc:
            logger.exception("Test email failed for EmailConfiguration %s", config.pk)
            messages.error(request, f"Test email failed: {exc}")

        return HttpResponseRedirect(request.get_full_path())


# ---------------------------------------------------------------------------
# Sent Emails (read-only audit log)
# ---------------------------------------------------------------------------

@admin.register(SentEmail)
class SentEmailAdmin(ModelAdmin):
    list_display = ["subject", "recipient_email", "from_identity", "show_sent_by", "sent_at"]
    list_filter = ["sent_at"]
    list_filter_submit = True
    readonly_fields = [
        "recipient_email",
        "recipient_name",
        "subject",
        "body_preview",
        "from_identity",
        "contact_message_link",
        "sent_at",
        "sent_by",
    ]
    fieldsets = [
        (
            "Recipient",
            {
                "fields": ("recipient_name", "recipient_email"),
            },
        ),
        (
            "Email Content",
            {
                "fields": ("subject", "body_preview"),
            },
        ),
        (
            "Sender",
            {
                "fields": ("from_identity", "sent_by"),
            },
        ),
        (
            "Related",
            {
                "fields": ("contact_message_link", "sent_at"),
            },
        ),
    ]

    @display(description="Sent by")
    def show_sent_by(self, obj):
        if obj.sent_by:
            return obj.sent_by.get_full_name() or obj.sent_by.username
        return "System"

    def contact_message_link(self, obj):
        if obj.contact_message:
            url = reverse(
                "admin:portfolio_contactmessage_change",
                args=[obj.contact_message.pk],
            )
            return format_html('<a href="{}">View original message</a>', url)
        return "—"
    contact_message_link.short_description = "Original Message"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Celery Task Results (read-only audit log)
# ---------------------------------------------------------------------------

from django_celery_results.admin import TaskResultAdmin as BaseTaskResultAdmin
from django_celery_results.models import GroupResult, TaskResult

admin.site.unregister(TaskResult)
admin.site.unregister(GroupResult)


@admin.register(TaskResult)
class TaskResultAdmin(ModelAdmin, BaseTaskResultAdmin):
    list_display = ["task_id", "task_name", "status", "worker", "date_done"]
    list_filter = ["status", "task_name", "worker", "date_done"]
    list_filter_submit = True
    search_fields = ["task_id", "task_name"]
    readonly_fields = [
        "task_id", "periodic_task_name", "task_name", "task_args",
        "task_kwargs", "status", "worker", "content_type",
        "content_encoding", "result", "date_created", "date_started",
        "date_done", "traceback", "meta",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GroupResult)
class GroupResultAdmin(ModelAdmin):
    list_display = ["group_id", "date_created", "date_done"]
    list_filter = ["date_done"]
    list_filter_submit = True
    readonly_fields = [
        "group_id", "date_created", "date_done",
        "content_type", "content_encoding", "result",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Auth (User, Group) — re-registered with Unfold for consistent styling
# ---------------------------------------------------------------------------

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
