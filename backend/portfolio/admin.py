from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SkillCategory,
)


def unread_messages_count(request):
    """Badge callback for sidebar unread message count."""
    try:
        count = ContactMessage.objects.filter(is_read=False).count()
        return count if count > 0 else None
    except Exception:
        return None


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ["full_name", "headline", "email"]
    fieldsets = [
        (
            "Personal Information",
            {
                "fields": (
                    "full_name",
                    "headline",
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


class SkillInline(TabularInline):
    model = Skill
    extra = 1
    fields = ["name", "icon", "proficiency", "order", "is_active"]
    ordering = ["order"]


@admin.register(SkillCategory)
class SkillCategoryAdmin(ModelAdmin):
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


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
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


@admin.register(Experience)
class ExperienceAdmin(ModelAdmin):
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


@admin.register(Education)
class EducationAdmin(ModelAdmin):
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


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = [
        "subject",
        "name",
        "email",
        "show_read_status",
        "created_at",
    ]
    list_filter = ["is_read"]
    list_filter_submit = True
    readonly_fields = ["name", "email", "subject", "message", "created_at"]
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
    ]

    @display(
        description="Status",
        label={
            "Unread": "warning",
            "Read": "success",
        },
    )
    def show_read_status(self, obj):
        return "Read" if obj.is_read else "Unread"

    def has_add_permission(self, request):
        return False
