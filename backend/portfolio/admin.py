import logging

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from modeltranslation.admin import TabbedTranslationAdmin, TranslationTabularInline
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import (
    ContactMessage,
    Education,
    EmailTemplate,
    Experience,
    Profile,
    Project,
    SentEmail,
    Skill,
    SkillCategory,
)

logger = logging.getLogger(__name__)


def unread_messages_count(request):
    """Badge callback for sidebar unread message count."""
    try:
        count = ContactMessage.objects.filter(is_read=False).count()
        return count if count > 0 else None
    except Exception:
        logger.exception("Failed to query unread message count")
        return None


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
    readonly_fields = ["name", "email", "subject", "message", "created_at", "reply_history"]
    fieldsets = [
        (
            "Sender",
            {
                "fields": ("name", "email"),
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

@admin.register(EmailTemplate)
class EmailTemplateAdmin(ModelAdmin):
    list_display = ["name", "subject", "show_status", "updated_at"]
    list_filter = ["is_active"]
    list_filter_submit = True
    readonly_fields = ["updated_at", "placeholder_help"]
    fieldsets = [
        (
            "Template Identity",
            {
                "fields": ("name", "subject"),
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
