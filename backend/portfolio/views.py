from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework import generics, viewsets
from rest_framework.response import Response

from .models import (
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    SkillCategory,
)
from .serializers import (
    ContactMessageSerializer,
    EducationSerializer,
    ExperienceSerializer,
    ProfileSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    SkillCategorySerializer,
)


class ProfileView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return Profile.objects.first()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({})
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SkillCategoryListView(generics.ListAPIView):
    serializer_class = SkillCategorySerializer
    queryset = SkillCategory.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception:
            # Keep homepage functional even when malformed skill data exists.
            return Response([])


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"

    def get_queryset(self):
        return Project.objects.filter(is_active=True).prefetch_related("technologies")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer


class ExperienceListView(generics.ListAPIView):
    serializer_class = ExperienceSerializer
    queryset = Experience.objects.filter(is_active=True)


class EducationListView(generics.ListAPIView):
    serializer_class = EducationSerializer
    queryset = Education.objects.filter(is_active=True)


@method_decorator(csrf_exempt, name="dispatch")
class ContactCreateView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
    queryset = ContactMessage.objects.all()
    throttle_scope = "contact"
    authentication_classes = []
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()
        self._notify(instance)

    @staticmethod
    def _notify(msg):
        """Send email notification if CONTACT_NOTIFY_EMAIL is configured."""
        from django.conf import settings
        from django.core.mail import send_mail

        recipient = getattr(settings, "CONTACT_NOTIFY_EMAIL", None)
        if not recipient:
            return
        try:
            send_mail(
                subject=f"New contact message: {msg.subject}",
                message=(
                    f"From: {msg.name} <{msg.email}>\n"
                    f"Subject: {msg.subject}\n\n"
                    f"{msg.message}"
                ),
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[recipient],
                fail_silently=True,
            )
        except Exception:
            pass
