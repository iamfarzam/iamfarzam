"""Seed the database with realistic sample data for testing and demos."""

from datetime import date

from django.core.management.base import BaseCommand

from portfolio.models import (
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SkillCategory,
)


class Command(BaseCommand):
    help = "Populate the database with sample portfolio data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            for model in [Education, Experience, Project, Skill, SkillCategory, Profile]:
                model.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed all portfolio data."))

        self._create_profile()
        self._create_skills()
        self._create_projects()
        self._create_experience()
        self._create_education()

        self.stdout.write(self.style.SUCCESS("Sample data seeded successfully."))

    def _create_profile(self):
        if Profile.objects.exists():
            self.stdout.write("Profile already exists, skipping.")
            return

        Profile.objects.create(
            full_name="Alex Morgan",
            headline="Software Engineer | System Architect | Open Source Contributor",
            bio=(
                "I'm a software engineer with a passion for designing robust systems "
                "and writing clean, maintainable code. Over the years, I've worked "
                "across the full stack — from low-level infrastructure to user-facing "
                "applications — always focused on solving the right problems the "
                "right way.\n\n"
                "When I'm not coding, I contribute to open source projects and enjoy "
                "mentoring developers who are early in their careers. I believe that "
                "great software is built by curious people who never stop learning."
            ),
            email="hello@example.com",
            location="San Francisco, CA",
            github_url="https://github.com",
            linkedin_url="https://linkedin.com",
            twitter_url="https://twitter.com",
            website_url="https://example.com",
            meta_title="Alex Morgan — Software Engineer",
            meta_description=(
                "Portfolio of Alex Morgan — a software engineer specializing "
                "in system architecture, distributed systems, and open source."
            ),
        )
        self.stdout.write(self.style.SUCCESS("  Created profile."))

    def _create_skills(self):
        if SkillCategory.objects.exists():
            self.stdout.write("Skills already exist, skipping.")
            return

        categories = {
            "Languages": [
                ("Python", "python", 90),
                ("JavaScript", "javascript", 85),
                ("TypeScript", "typescript", 80),
                ("Go", "go", 70),
                ("SQL", "sql", 85),
            ],
            "Frameworks & Libraries": [
                ("Django", "django", 90),
                ("React", "react", 80),
                ("Next.js", "nextjs", 75),
                ("FastAPI", "fastapi", 80),
                ("Node.js", "nodejs", 70),
            ],
            "Infrastructure & Tools": [
                ("Docker", "docker", 85),
                ("PostgreSQL", "postgresql", 85),
                ("Redis", "redis", 75),
                ("Git", "git", 90),
                ("Linux", "linux", 80),
                ("AWS", "aws", 70),
                ("Nginx", "nginx", 75),
            ],
        }

        for order, (cat_name, skills) in enumerate(categories.items()):
            category = SkillCategory.objects.create(
                name=cat_name, order=order, is_active=True
            )
            for skill_order, (name, icon, proficiency) in enumerate(skills):
                Skill.objects.create(
                    category=category,
                    name=name,
                    icon=icon,
                    proficiency=proficiency,
                    order=skill_order,
                    is_active=True,
                )

        self.stdout.write(self.style.SUCCESS("  Created skill categories and skills."))

    def _create_projects(self):
        if Project.objects.exists():
            self.stdout.write("Projects already exist, skipping.")
            return

        projects = [
            {
                "title": "TaskFlow",
                "slug": "taskflow",
                "summary": "A real-time task management platform with team collaboration, Kanban boards, and automated workflow triggers.",
                "description": (
                    "TaskFlow is a full-stack project management tool designed for "
                    "small engineering teams. It features real-time updates via "
                    "WebSockets, a drag-and-drop Kanban interface, and customizable "
                    "workflow automations.\n\n"
                    "The backend is built with Django and Django REST Framework, "
                    "using PostgreSQL for persistence and Redis for real-time "
                    "pub/sub. The frontend is a React SPA with optimistic UI updates.\n\n"
                    "Key challenges included designing the real-time sync layer "
                    "to handle concurrent edits gracefully and building a flexible "
                    "automation engine that lets users define custom triggers and actions."
                ),
                "github_url": "https://github.com",
                "live_url": "https://example.com",
                "is_featured": True,
                "order": 0,
                "tech": ["Python", "Django", "React", "PostgreSQL", "Redis"],
            },
            {
                "title": "CloudMetrics",
                "slug": "cloudmetrics",
                "summary": "Infrastructure monitoring dashboard that aggregates metrics from multiple cloud providers into a unified view.",
                "description": (
                    "CloudMetrics provides a single pane of glass for monitoring "
                    "cloud infrastructure across AWS, GCP, and Azure. It collects "
                    "metrics via provider APIs, normalizes them into a common schema, "
                    "and presents them through interactive dashboards.\n\n"
                    "Built with a Go ingestion service for high-throughput metric "
                    "collection, a Python analytics layer for anomaly detection, "
                    "and a Next.js frontend with real-time charting.\n\n"
                    "The architecture uses a time-series database for efficient "
                    "metric storage and supports custom alerting rules with "
                    "configurable notification channels."
                ),
                "github_url": "https://github.com",
                "live_url": "",
                "is_featured": True,
                "order": 1,
                "tech": ["Go", "Python", "Next.js", "PostgreSQL", "AWS"],
            },
            {
                "title": "AuthGate",
                "slug": "authgate",
                "summary": "A lightweight, self-hosted authentication service supporting OAuth 2.0, SAML, and passwordless login flows.",
                "description": (
                    "AuthGate is an open-source authentication and authorization "
                    "service designed to be self-hosted. It supports multiple "
                    "identity protocols including OAuth 2.0, SAML 2.0, and "
                    "magic-link passwordless authentication.\n\n"
                    "The service is built with FastAPI for performance and uses "
                    "PostgreSQL for user and session management. It includes a "
                    "built-in admin dashboard for managing users, roles, and "
                    "permissions.\n\n"
                    "Security features include rate limiting, brute-force "
                    "protection, audit logging, and support for hardware "
                    "security keys via WebAuthn."
                ),
                "github_url": "https://github.com",
                "live_url": "",
                "is_featured": True,
                "order": 2,
                "tech": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            },
            {
                "title": "DevBlog Engine",
                "slug": "devblog-engine",
                "summary": "A statically-generated blog platform with Markdown support, syntax highlighting, and built-in SEO optimization.",
                "description": (
                    "DevBlog Engine is a developer-focused blogging platform "
                    "that generates static HTML from Markdown files. It features "
                    "automatic syntax highlighting, responsive images, RSS feed "
                    "generation, and comprehensive SEO metadata.\n\n"
                    "Built with Next.js and deployed on Vercel, it achieves "
                    "perfect Lighthouse scores out of the box. Content is managed "
                    "through a Git-based workflow — write Markdown, push, and "
                    "the site rebuilds automatically."
                ),
                "github_url": "https://github.com",
                "live_url": "https://example.com",
                "is_featured": False,
                "order": 3,
                "tech": ["TypeScript", "Next.js", "Node.js"],
            },
        ]

        for proj_data in projects:
            tech_names = proj_data.pop("tech")
            project = Project.objects.create(**proj_data)
            skills = Skill.objects.filter(name__in=tech_names)
            project.technologies.set(skills)

        self.stdout.write(self.style.SUCCESS("  Created projects."))

    def _create_experience(self):
        if Experience.objects.exists():
            self.stdout.write("Experience already exists, skipping.")
            return

        entries = [
            {
                "company": "Nexus Technologies",
                "role": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "start_date": date(2022, 3, 1),
                "end_date": None,
                "description": (
                    "Leading the architecture and development of the core platform "
                    "services. Designed a microservices migration strategy that "
                    "reduced deployment times by 60%. Mentoring a team of 4 engineers "
                    "and driving adoption of engineering best practices across the org."
                ),
                "company_url": "https://example.com",
                "order": 0,
            },
            {
                "company": "Arcline Systems",
                "role": "Software Engineer",
                "location": "Austin, TX",
                "start_date": date(2019, 6, 1),
                "end_date": date(2022, 2, 28),
                "description": (
                    "Built and maintained internal tools and APIs serving 50k+ "
                    "daily requests. Implemented a caching layer that reduced "
                    "average API response times from 800ms to 120ms. Collaborated "
                    "with product and design teams to ship user-facing features."
                ),
                "company_url": "https://example.com",
                "order": 1,
            },
            {
                "company": "Greenfield Labs",
                "role": "Junior Software Engineer",
                "location": "Remote",
                "start_date": date(2017, 9, 1),
                "end_date": date(2019, 5, 31),
                "description": (
                    "Contributed to a data processing pipeline handling 2M+ "
                    "records daily. Wrote unit and integration tests that "
                    "improved code coverage from 45% to 87%. Participated in "
                    "code reviews and on-call rotations."
                ),
                "company_url": "",
                "order": 2,
            },
        ]

        for entry in entries:
            Experience.objects.create(**entry)

        self.stdout.write(self.style.SUCCESS("  Created experience entries."))

    def _create_education(self):
        if Education.objects.exists():
            self.stdout.write("Education already exists, skipping.")
            return

        entries = [
            {
                "institution": "University of California, Berkeley",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "start_date": date(2013, 8, 1),
                "end_date": date(2017, 5, 31),
                "description": (
                    "Graduated with honors. Coursework in distributed systems, "
                    "algorithms, operating systems, and software engineering. "
                    "Teaching assistant for Introduction to Database Systems."
                ),
                "order": 0,
            },
        ]

        for entry in entries:
            Education.objects.create(**entry)

        self.stdout.write(self.style.SUCCESS("  Created education entries."))
