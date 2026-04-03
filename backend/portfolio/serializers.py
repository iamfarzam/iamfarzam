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

def safe_file_url(field_file, request=None):
    if not field_file:
        return None
    try:
        url = field_file.url
    except Exception:
        return None
    if request is not None:
        return request.build_absolute_uri(url)
    return url


class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()
    og_image = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "full_name", "headline", "bio", "avatar", "resume", "email",
            "location", "github_url", "linkedin_url", "twitter_url",
            "website_url", "meta_title", "meta_description", "og_image",
        ]

    def get_avatar(self, obj):
        return safe_file_url(obj.avatar, self.context.get("request"))

    def get_resume(self, obj):
        return safe_file_url(obj.resume, self.context.get("request"))

    def get_og_image(self, obj):
        return safe_file_url(obj.og_image, self.context.get("request"))


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
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "title", "slug", "summary", "thumbnail",
            "technologies", "github_url", "live_url", "is_featured",
        ]

    def get_thumbnail(self, obj):
        return safe_file_url(obj.thumbnail, self.context.get("request"))


class ProjectDetailSerializer(serializers.ModelSerializer):
    technologies = TechnologySerializer(many=True, read_only=True)
    thumbnail = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "title", "slug", "summary", "description", "thumbnail", "image",
            "technologies", "github_url", "live_url", "is_featured", "created_at",
        ]

    def get_thumbnail(self, obj):
        return safe_file_url(obj.thumbnail, self.context.get("request"))

    def get_image(self, obj):
        return safe_file_url(obj.image, self.context.get("request"))


class ExperienceSerializer(serializers.ModelSerializer):
    company_logo = serializers.SerializerMethodField()

    class Meta:
        model = Experience
        fields = [
            "id", "company", "role", "location", "start_date",
            "end_date", "description", "company_url", "company_logo",
        ]

    def get_company_logo(self, obj):
        return safe_file_url(obj.company_logo, self.context.get("request"))


class EducationSerializer(serializers.ModelSerializer):
    institution_logo = serializers.SerializerMethodField()

    class Meta:
        model = Education
        fields = [
            "id", "institution", "degree", "field_of_study",
            "start_date", "end_date", "description", "institution_logo",
        ]

    def get_institution_logo(self, obj):
        return safe_file_url(obj.institution_logo, self.context.get("request"))


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
