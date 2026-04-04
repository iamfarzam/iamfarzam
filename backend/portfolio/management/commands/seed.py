"""Seed the database with sample data loaded from JSON fixtures."""

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from portfolio.models import (
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SkillCategory,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


class Command(BaseCommand):
    help = "Seed database from fixtures or flush existing data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all portfolio data and exit",
        )
        parser.add_argument(
            "--fixture-dir",
            type=str,
            default=str(FIXTURES_DIR),
            help="Directory containing seed.json and seed.{lang}.json files",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            for model in [Education, Experience, Project, Skill, SkillCategory, Profile]:
                model.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed all portfolio data."))
            return

        fixture_dir = Path(options["fixture_dir"])
        base_file = fixture_dir / "seed.json"
        if not base_file.exists():
            self.stderr.write(self.style.ERROR(f"Base fixture not found: {base_file}"))
            return

        data = json.loads(base_file.read_text(encoding="utf-8"))

        self._create_profile(data.get("profile"))
        skill_map = self._create_skills(data.get("skills", []))
        self._create_projects(data.get("projects", []), skill_map)
        self._create_experience(data.get("experience", []))
        self._create_education(data.get("education", []))

        self.stdout.write(self.style.SUCCESS("Base data seeded."))

        # Load per-language translations
        lang_codes = [code for code, _ in settings.LANGUAGES if code != settings.MODELTRANSLATION_DEFAULT_LANGUAGE]
        loaded = 0
        for lang in lang_codes:
            # Django uses "zh-hans" but modeltranslation fields use "zh_hans"
            field_suffix = lang.replace("-", "_")
            lang_file = fixture_dir / f"seed.{lang}.json"
            if not lang_file.exists():
                continue
            lang_data = json.loads(lang_file.read_text(encoding="utf-8"))
            self._apply_translations(lang_data, field_suffix)
            loaded += 1
            self.stdout.write(self.style.SUCCESS(f"  Loaded translations: {lang}"))

        if loaded:
            self.stdout.write(self.style.SUCCESS(f"Applied {loaded} language(s)."))
        else:
            self.stdout.write("No translation fixtures found, skipping.")

    def _apply_translations(self, lang_data, suffix):
        """Update existing objects with translated field values."""
        profile_t = lang_data.get("profile")
        if profile_t:
            profile = Profile.objects.first()
            if profile:
                for field, value in profile_t.items():
                    setattr(profile, f"{field}_{suffix}", value)
                profile.save()

        for group in lang_data.get("skills", []):
            cat_name_en = group.get("category_key")
            cat_translation = group.get("category")
            if cat_name_en and cat_translation:
                SkillCategory.objects.filter(name=cat_name_en).update(
                    **{f"name_{suffix}": cat_translation}
                )
            for item in group.get("items", []):
                key = item.get("key")
                name = item.get("name")
                if key and name:
                    Skill.objects.filter(name=key).update(**{f"name_{suffix}": name})

        for proj in lang_data.get("projects", []):
            slug = proj.pop("slug", None)
            if not slug:
                continue
            updates = {f"{k}_{suffix}": v for k, v in proj.items()}
            Project.objects.filter(slug=slug).update(**updates)

        for i, entry in enumerate(lang_data.get("experience", [])):
            updates = {f"{k}_{suffix}": v for k, v in entry.items()}
            Experience.objects.filter(order=i).update(**updates)

        for i, entry in enumerate(lang_data.get("education", [])):
            updates = {f"{k}_{suffix}": v for k, v in entry.items()}
            Education.objects.filter(order=i).update(**updates)

    def _create_profile(self, profile_data):
        if not profile_data:
            return
        if Profile.objects.exists():
            self.stdout.write("Profile already exists, skipping.")
            return
        Profile.objects.create(**profile_data)
        self.stdout.write(self.style.SUCCESS("  Created profile."))

    def _create_skills(self, skills_data):
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
