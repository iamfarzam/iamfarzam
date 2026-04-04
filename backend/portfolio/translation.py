from modeltranslation.translator import register, TranslationOptions

from .models import Education, Experience, Profile, Project, Skill, SkillCategory


@register(Profile)
class ProfileTranslation(TranslationOptions):
    fields = ("headline", "tagline", "bio", "meta_title", "meta_description")


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
    fields = ("role", "description")


@register(Education)
class EducationTranslation(TranslationOptions):
    fields = ("degree", "field_of_study", "description")
