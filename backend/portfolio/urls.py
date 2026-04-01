from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ContactCreateView,
    EducationListView,
    ExperienceListView,
    ProfileView,
    ProjectViewSet,
    SkillCategoryListView,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
    path("skills/", SkillCategoryListView.as_view(), name="skills"),
    path("experience/", ExperienceListView.as_view(), name="experience"),
    path("education/", EducationListView.as_view(), name="education"),
    path("contact/", ContactCreateView.as_view(), name="contact"),
    path("", include(router.urls)),
]
