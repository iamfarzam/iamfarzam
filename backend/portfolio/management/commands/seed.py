"""Seed the database with sample data loaded from a JSON fixture."""

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand

from portfolio.models import (
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SkillCategory,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "seed.json"


class Command(BaseCommand):
    help = "Populate the database with sample portfolio data from fixtures/seed.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data before seeding",
        )
        parser.add_argument(
            "--fixture",
            type=str,
            default=str(FIXTURE_PATH),
            help="Path to a custom seed fixture JSON file",
        )

    def handle(self, *args, **options):
        fixture = Path(options["fixture"])
        if not fixture.exists():
            self.stderr.write(self.style.ERROR(f"Fixture not found: {fixture}"))
            return

        data = json.loads(fixture.read_text(encoding="utf-8"))

        if options["flush"]:
            for model in [Education, Experience, Project, Skill, SkillCategory, Profile]:
                model.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed all portfolio data."))

        self._create_profile(data.get("profile"))
        skill_map = self._create_skills(data.get("skills", []))
        self._create_projects(data.get("projects", []), skill_map)
        self._create_experience(data.get("experience", []))
        self._create_education(data.get("education", []))

        self.stdout.write(self.style.SUCCESS("Sample data seeded successfully."))

    def _create_profile(self, profile_data):
        if not profile_data:
            return
        if Profile.objects.exists():
            self.stdout.write("Profile already exists, skipping.")
            return

        Profile.objects.create(**profile_data)
        self.stdout.write(self.style.SUCCESS("  Created profile."))

    def _create_skills(self, skills_data):
        """Return a name->Skill mapping for linking technologies to projects."""
        skill_map = {}
        if not skills_data:
            return skill_map
        if SkillCategory.objects.exists():
            self.stdout.write("Skills already exist, skipping.")
            return {s.name: s for s in Skill.objects.all()}

        for cat_order, group in enumerate(skills_data):
            category = SkillCategory.objects.create(
                name=group["category"], order=cat_order, is_active=True
            )
            for skill_order, item in enumerate(group["items"]):
                skill = Skill.objects.create(
                    category=category,
                    name=item["name"],
                    icon=item.get("icon", ""),
                    proficiency=item.get("proficiency", 0),
                    order=skill_order,
                    is_active=True,
                )
                skill_map[skill.name] = skill

        self.stdout.write(self.style.SUCCESS("  Created skill categories and skills."))
        return skill_map

    def _create_projects(self, projects_data, skill_map):
        if not projects_data:
            return
        if Project.objects.exists():
            self.stdout.write("Projects already exist, skipping.")
            return

        for proj in projects_data:
            tech_names = proj.pop("technologies", [])
            project = Project.objects.create(**proj)
            techs = [skill_map[n] for n in tech_names if n in skill_map]
            if techs:
                project.technologies.set(techs)

        self.stdout.write(self.style.SUCCESS("  Created projects."))

    def _create_experience(self, experience_data):
        if not experience_data:
            return
        if Experience.objects.exists():
            self.stdout.write("Experience already exists, skipping.")
            return

        for entry in experience_data:
            entry["start_date"] = date.fromisoformat(entry["start_date"])
            entry["end_date"] = (
                date.fromisoformat(entry["end_date"]) if entry.get("end_date") else None
            )
            Experience.objects.create(**entry)

        self.stdout.write(self.style.SUCCESS("  Created experience entries."))

    def _create_education(self, education_data):
        if not education_data:
            return
        if Education.objects.exists():
            self.stdout.write("Education already exists, skipping.")
            return

        for entry in education_data:
            entry["start_date"] = date.fromisoformat(entry["start_date"])
            entry["end_date"] = (
                date.fromisoformat(entry["end_date"]) if entry.get("end_date") else None
            )
            Education.objects.create(**entry)

        self.stdout.write(self.style.SUCCESS("  Created education entries."))
