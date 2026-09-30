"""The admin landing page must report the site, not repeat the sidebar."""

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from portfolio.dashboard import _month_starts, _monthly_totals, dashboard_callback
from portfolio.models import (
    ContactMessage,
    Education,
    Experience,
    Project,
    ProjectDemo,
    SentEmail,
    Skill,
    SkillCategory,
)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "owner", "owner@example.test", "test-password"
        )
        self.client.force_login(self.user)
        category = SkillCategory.objects.create(name="Backend")
        self.skill = Skill.objects.create(category=category, name="Django")
        Skill.objects.create(category=category, name="Unused")
        self.project = Project.objects.create(title="Sample", slug="sample", summary="Sample")
        self.project.technologies.add(self.skill)
        Project.objects.create(title="Hidden", slug="hidden", summary="Hidden", is_active=False)
        Experience.objects.create(
            company="Example", role="Engineer", start_date="2024-01-01", description="Work"
        )
        Education.objects.create(
            institution="Example", degree="BSc", start_date="2020-01-01"
        )
        self.message = ContactMessage.objects.create(
            name="Visitor", email="visitor@example.test", subject="Hello", message="Hi"
        )
        SentEmail.objects.create(
            recipient_email="visitor@example.test", subject="Re: Hello",
            body_preview="Reply", from_identity="Owner <owner@example.test>",
        )

    def context(self):
        return dashboard_callback(None, {})

    def test_index_renders_counts_and_charts_instead_of_the_application_list(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Interactive demos")
        self.assertContains(response, "Unread messages")
        self.assertContains(response, "Messages received")
        self.assertContains(response, 'data-type="bar"')
        self.assertContains(response, 'data-type="line"')
        # The sidebar is the only navigation; the index no longer repeats it.
        self.assertNotContains(response, "app-portfolio")

    def test_counts_separate_active_from_hidden_records(self):
        cards = {card["title"]: card for card in self.context()["kpi_cards"]}
        self.assertEqual(cards["Projects"]["value"], 1)
        self.assertIn("of 2 total", cards["Projects"]["footer"])
        self.assertEqual(cards["Unread messages"]["value"], 1)
        self.assertEqual(cards["Replies sent"]["value"], 1)
        self.assertEqual(cards["Skills"]["value"], 2)
        self.assertEqual(cards["Experience"]["value"], 1)
        self.assertEqual(cards["Education"]["value"], 1)

    def test_charts_are_valid_json_spanning_a_full_year(self):
        context = self.context()
        for key in ["messages_chart", "email_chart", "technology_chart", "language_chart"]:
            chart = json.loads(context[key])
            self.assertEqual(len(chart["labels"]), len(chart["datasets"][0]["data"]))
        messages = json.loads(context["messages_chart"])
        self.assertEqual(len(messages["labels"]), 12)
        self.assertEqual(messages["datasets"][0]["data"][-1], 1)
        self.assertEqual(sum(messages["datasets"][0]["data"]), 1)

    def test_only_technologies_used_by_active_projects_are_charted(self):
        chart = json.loads(self.context()["technology_chart"])
        self.assertEqual(chart["labels"], ["Django"])
        self.assertEqual(chart["datasets"][0]["data"], [1])

    def test_monthly_totals_fill_gaps_with_zero(self):
        starts = _month_starts(3)
        ContactMessage.objects.all().update(created_at=starts[0] + timedelta(days=1))
        totals = _monthly_totals(ContactMessage.objects.all(), "created_at", starts)
        self.assertEqual(totals, [1, 0, 0])

    def test_demo_rows_explain_every_project_state(self):
        # Hosting is off by default, so every project must say so rather than
        # blaming a release that was never the problem.
        rows = {row["slug"]: row for row in self.context()["demo_rows"]}
        self.assertEqual(rows["sample"]["state"], "Hosting off")
        with override_settings(DEMOS_ENABLED=True, DEMOS_GATE_SECRET="a" * 48):
            rows = {row["slug"]: row for row in self.context()["demo_rows"]}
            self.assertEqual(rows["sample"]["state"], "Not configured")
            self.assertIn("No demo configuration", rows["sample"]["detail"])
            ProjectDemo.objects.create(project=self.project, release="v1", enabled=False)
            self.project.refresh_from_db()
            rows = {row["slug"]: row for row in self.context()["demo_rows"]}
            self.assertEqual(rows["sample"]["state"], "Not enabled")
            self.assertEqual(rows["sample"]["variant"], "warning")

    def test_dashboard_survives_an_empty_database(self):
        for model in [ContactMessage, SentEmail, Project, Skill, SkillCategory, Experience, Education]:
            model.objects.all().delete()
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No contact messages have arrived yet.")
        context = self.context()
        self.assertFalse(context["has_technology_chart"])
        self.assertFalse(context["has_language_chart"])

    def test_dashboard_is_not_public(self):
        self.client.logout()
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
