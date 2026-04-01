from rest_framework import serializers

from .models import (
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SkillCategory,
)


class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(use_url=True, required=False)
    resume = serializers.FileField(use_url=True, required=False)
    og_image = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = Profile
        fields = [
            "full_name", "headline", "bio", "avatar", "resume", "email",
            "location", "github_url", "linkedin_url", "twitter_url",
            "website_url", "meta_title", "meta_description", "og_image",
        ]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "icon", "proficiency"]


class SkillCategorySerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = SkillCategory
        fields = ["id", "name", "skills"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["skills"] = SkillSerializer(
            instance.skills.filter(is_active=True),
            many=True,
        ).data
        return data


class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["name", "icon"]


class ProjectListSerializer(serializers.ModelSerializer):
    technologies = TechnologySerializer(many=True, read_only=True)
    thumbnail = serializers.ImageField(use_url=True)

    class Meta:
        model = Project
        fields = [
            "title", "slug", "summary", "thumbnail",
            "technologies", "github_url", "live_url", "is_featured",
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    technologies = TechnologySerializer(many=True, read_only=True)
    thumbnail = serializers.ImageField(use_url=True)
    image = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = Project
        fields = [
            "title", "slug", "summary", "description", "thumbnail", "image",
            "technologies", "github_url", "live_url", "is_featured", "created_at",
        ]


class ExperienceSerializer(serializers.ModelSerializer):
    company_logo = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = Experience
        fields = [
            "id", "company", "role", "location", "start_date",
            "end_date", "description", "company_url", "company_logo",
        ]


class EducationSerializer(serializers.ModelSerializer):
    institution_logo = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = Education
        fields = [
            "id", "institution", "degree", "field_of_study",
            "start_date", "end_date", "description", "institution_logo",
        ]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
