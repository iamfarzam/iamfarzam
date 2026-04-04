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

# Only these fields have translation columns — everything else must be skipped.
TRANSLATABLE = {
    "profile": {"headline", "tagline", "bio", "meta_title", "meta_description"},
    "project": {"title", "summary", "description"},
    "experience": {"role", "description"},
    "education": {"degree", "field_of_study", "description"},
}


class Command(BaseCommand):
    help = "Seed database from fixtures or flush existing data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all portfolio data and exit",
        )
        parser.add_argument(
            "--fixture",
            type=str,
            help="Path to a single fixture file (language auto-detected from filename, e.g. seed.es.json)",
        )
        parser.add_argument(
            "--lang",
            type=str,
            help="Language code for --fixture (overrides auto-detection)",
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

        # Single fixture mode
        if options["fixture"]:
            return self._handle_single_fixture(options["fixture"], options.get("lang"))

        # Full seed mode: base + all languages
        fixture_dir = Path(options["fixture_dir"])
        if not fixture_dir.is_dir():
            self.stdout.write(self.style.WARNING(f"Fixtures directory not found: {fixture_dir} — skipping."))
            return
        base_file = fixture_dir / "seed.json"
        if not base_file.exists():
            # Try seed.en.json as fallback
            base_file = fixture_dir / "seed.en.json"
        if not base_file.exists():
            self.stderr.write(self.style.ERROR(f"No base fixture (seed.json or seed.en.json) found in {fixture_dir}"))
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

    def _handle_single_fixture(self, fixture_path, explicit_lang):
        """Load a single fixture file. Auto-detects language from filename."""
        path = Path(fixture_path)
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Fixture not found: {path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))

        if explicit_lang:
            lang = explicit_lang
        else:
            # Auto-detect from filename: seed.es.json -> es, seed.zh-hans.json -> zh-hans
            parts = path.stem.split(".")
            lang = parts[1] if len(parts) > 1 else None

        default_lang = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
        valid_codes = [code for code, _ in settings.LANGUAGES]

        if lang is None or lang == default_lang:
            # Treat as base English fixture
            self._create_profile(data.get("profile"))
            skill_map = self._create_skills(data.get("skills", []))
            self._create_projects(data.get("projects", []), skill_map)
            self._create_experience(data.get("experience", []))
            self._create_education(data.get("education", []))
            self.stdout.write(self.style.SUCCESS(f"Seeded base data from {path.name}"))
        elif lang in valid_codes:
            field_suffix = lang.replace("-", "_")
            self._apply_translations(data, field_suffix)
            self.stdout.write(self.style.SUCCESS(f"Applied {lang} translations from {path.name}"))
        else:
            self.stderr.write(self.style.ERROR(
                f"Unknown language '{lang}'. Valid: {', '.join(valid_codes)}"
            ))

    def _apply_translations(self, lang_data, suffix):
        """Update existing objects with translated field values."""
        profile_t = lang_data.get("profile")
        if profile_t:
            profile = Profile.objects.first()
            if profile:
                allowed = TRANSLATABLE["profile"]
                for field, value in profile_t.items():
                    if field in allowed:
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

        allowed_proj = TRANSLATABLE["project"]
        for proj in lang_data.get("projects", []):
            slug = proj.get("slug")
            if not slug:
                continue
            updates = {f"{k}_{suffix}": v for k, v in proj.items() if k in allowed_proj}
            if updates:
                Project.objects.filter(slug=slug).update(**updates)

        allowed_exp = TRANSLATABLE["experience"]
        for i, entry in enumerate(lang_data.get("experience", [])):
            updates = {f"{k}_{suffix}": v for k, v in entry.items() if k in allowed_exp}
            if updates:
                Experience.objects.filter(order=i).update(**updates)

        allowed_edu = TRANSLATABLE["education"]
        for i, entry in enumerate(lang_data.get("education", [])):
            updates = {f"{k}_{suffix}": v for k, v in entry.items() if k in allowed_edu}
            if updates:
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
