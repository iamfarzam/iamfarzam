from modeltranslation.translator import register, TranslationOptions

from .models import (
    Education,
    EmailTemplate,
    Experience,
    Profile,
    Project,
    Skill,
    SkillCategory,
)


@register(Profile)
class ProfileTranslation(TranslationOptions):
    fields = ("full_name", "headline", "tagline", "bio", "location", "meta_title", "meta_description")


@register(SkillCategory)
class SkillCategoryTranslation(TranslationOptions):
    fields = ("name",)


@register(Skill)
class SkillTranslation(TranslationOptions):
    fields = ("name",)


@register(Project)
class ProjectTranslation(TranslationOptions):
    fields = ("title", "summary", "description")


@register(Experience)
class ExperienceTranslation(TranslationOptions):
    fields = ("role", "description", "location")


@register(Education)
class EducationTranslation(TranslationOptions):
    fields = ("degree", "field_of_study", "description")


@register(EmailTemplate)
class EmailTemplateTranslation(TranslationOptions):
    fields = ("subject", "html_body", "text_body")
