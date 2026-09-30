"""Metrics for the admin landing page.

Unfold's default index repeats the model list that already fills the sidebar.
This callback replaces it with counts, trends and demo readiness, so opening
administration answers "what is the site doing" instead of "what models exist".
Every query here is a read-only aggregate.
"""

import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone

from .demo_admin import DEMO_STATE_LABELS, demo_state
from .models import (
    ContactMessage,
    Education,
    Experience,
    Project,
    SentEmail,
    Skill,
    SkillCategory,
)

TREND_MONTHS = 12
TOP_TECHNOLOGIES = 8
RECENT_MESSAGES = 6
REPLY_WINDOW_DAYS = 30

# Resolved against the active Unfold palette by its chart script, so the
# dashboard follows the admin theme in both light and dark mode.
PRIMARY = "var(--color-primary-500)"
PRIMARY_SOFT = "var(--color-primary-200)"
NEUTRAL = "var(--color-base-400)"


def _month_starts(count):
    """The first instant of each of the last ``count`` months, oldest first."""
    current = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    starts = [current]
    for _ in range(count - 1):
        starts.insert(0, (starts[0] - timedelta(days=1)).replace(day=1))
    return starts


def _monthly_totals(queryset, field, starts):
    """Count rows per calendar month, filling months without rows with zero."""
    rows = (
        queryset.filter(**{f"{field}__gte": starts[0]})
        .annotate(month=TruncMonth(field))
        .values("month")
        .annotate(total=Count("id"))
        .order_by()
    )
    totals = {}
    for row in rows:
        month = row["month"]
        if month is None:
            continue
        if timezone.is_aware(month):
            month = timezone.localtime(month)
        totals[(month.year, month.month)] = row["total"]
    return [totals.get((start.year, start.month), 0) for start in starts]


def _chart(labels, datasets):
    return json.dumps({"labels": labels, "datasets": datasets})


def _changelist(model, **query):
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
    if query:
        url += "?" + "&".join(f"{key}={value}" for key, value in query.items())
    return url


def _demo_rows():
    """One row per project, carrying the state the project list also shows."""
    rows = []
    for project in Project.objects.select_related("demo_config").order_by("title"):
        state, detail = demo_state(project)
        demo = getattr(project, "demo_config", None)
        rows.append({
            "title": project.title,
            "slug": project.slug,
            "release": demo.release if demo else "",
            "state": state,
            "variant": DEMO_STATE_LABELS.get(state, ""),
            "detail": detail,
            "href": reverse("admin:portfolio_project_change", args=[project.pk]),
            "url": detail if state == "Live" else "",
        })
    return rows


def dashboard_callback(request, context):
    starts = _month_starts(TREND_MONTHS)
    labels = [start.strftime("%b %y") for start in starts]

    projects = Project.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        featured=Count("id", filter=Q(is_active=True, is_featured=True)),
    )
    contacts = ContactMessage.objects.aggregate(
        total=Count("id"),
        unread=Count("id", filter=Q(is_read=False)),
    )
    demo_rows = _demo_rows()
    demos_live = sum(1 for row in demo_rows if row["state"] == "Live")
    replies = SentEmail.objects.filter(
        sent_at__gte=timezone.now() - timedelta(days=REPLY_WINDOW_DAYS)
    ).count()

    technologies = (
        Skill.objects.annotate(used=Count("projects", filter=Q(projects__is_active=True)))
        .filter(used__gt=0)
        .order_by("-used", "name")[:TOP_TECHNOLOGIES]
    )
    languages = (
        ContactMessage.objects.values("language")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )
    language_names = dict(settings.LANGUAGES)

    context.update({
        "kpi_cards": [
            {
                "title": "Projects",
                "value": projects["active"],
                "footer": "{} featured of {} total".format(projects["featured"], projects["total"]),
                "icon": "code",
                "href": _changelist(Project),
            },
            {
                "title": "Interactive demos",
                "value": "{}/{}".format(demos_live, projects["total"]),
                "footer": "served right now" if demos_live else "none configured yet",
                "icon": "play_circle",
                "href": _changelist(Project),
            },
            {
                "title": "Unread messages",
                "value": contacts["unread"],
                "footer": "{} received in total".format(contacts["total"]),
                "icon": "mark_email_unread",
                "href": _changelist(ContactMessage, is_read__exact=0),
            },
            {
                "title": "Replies sent",
                "value": replies,
                "footer": "in the last {} days".format(REPLY_WINDOW_DAYS),
                "icon": "send",
                "href": _changelist(SentEmail),
            },
            {
                "title": "Skills",
                "value": Skill.objects.filter(is_active=True).count(),
                "footer": "across {} categories".format(
                    SkillCategory.objects.filter(is_active=True).count()
                ),
                "icon": "star",
                "href": _changelist(SkillCategory),
            },
            {
                "title": "Experience",
                "value": Experience.objects.filter(is_active=True).count(),
                "footer": "roles published",
                "icon": "work",
                "href": _changelist(Experience),
            },
            {
                "title": "Education",
                "value": Education.objects.filter(is_active=True).count(),
                "footer": "entries published",
                "icon": "school",
                "href": _changelist(Education),
            },
            {
                "title": "Demo hosting",
                "value": "On" if settings.DEMOS_ENABLED else "Off",
                "footer": settings.DEMOS_BASE_DOMAIN if settings.DEMOS_ENABLED else "DEMOS_ENABLED is false",
                "icon": "dns",
                "href": _changelist(Project),
            },
        ],
        "messages_chart": _chart(labels, [{
            "label": "Messages received",
            "data": _monthly_totals(ContactMessage.objects.all(), "created_at", starts),
            "backgroundColor": PRIMARY,
            "borderColor": PRIMARY,
            "borderRadius": 4,
        }]),
        "email_chart": _chart(labels, [{
            "label": "Replies sent",
            "data": _monthly_totals(SentEmail.objects.all(), "sent_at", starts),
            "borderColor": PRIMARY,
            "backgroundColor": PRIMARY_SOFT,
            "tension": 0.4,
            "fill": True,
            "pointRadius": 2,
        }]),
        "technology_chart": _chart(
            [skill.name for skill in technologies],
            [{
                "label": "Active projects",
                "data": [skill.used for skill in technologies],
                "backgroundColor": PRIMARY,
                "borderRadius": 4,
            }],
        ),
        "language_chart": _chart(
            [language_names.get(row["language"], row["language"]) for row in languages],
            [{
                "label": "Messages",
                "data": [row["total"] for row in languages],
                "backgroundColor": [
                    PRIMARY,
                    PRIMARY_SOFT,
                    NEUTRAL,
                    "var(--color-primary-700)",
                    "var(--color-base-300)",
                    "var(--color-primary-400)",
                ],
                "borderWidth": 0,
            }],
        ),
        "has_language_chart": bool(languages),
        "has_technology_chart": bool(technologies),
        "demo_rows": demo_rows,
        "demos_live": demos_live,
        "demos_enabled": settings.DEMOS_ENABLED,
        "recent_messages": ContactMessage.objects.order_by("-created_at")[:RECENT_MESSAGES],
        "message_changelist": _changelist(ContactMessage),
        "trend_window": "{} to {}".format(labels[0], labels[-1]),
    })
    return context
