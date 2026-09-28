"""Release selection and readiness feedback inside project administration."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from modeltranslation.admin import TranslationStackedInline
from unfold.admin import StackedInline

from .demos import check_readiness, load_release, release_path
from .models import ProjectDemo


class ProjectDemoForm(forms.ModelForm):
    class Meta:
        model = ProjectDemo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project = getattr(self, "demo_project", None)
        if project is None and self.instance.project_id:
            project = self.instance.project
        choices = []
        if project:
            try:
                directory = release_path(project.slug, "placeholder").parent
                if directory.is_dir():
                    for path in sorted(directory.iterdir()):
                        try:
                            load_release(project.slug, path.name)
                            choices.append((path.name, path.name))
                        except ValidationError:
                            continue
            except ValidationError:
                pass
        self.fields["release"] = forms.ChoiceField(
            choices=[("", "Select a published release"), *choices],
            help_text="Upload and validate a release first. Save an enabled configuration to check readiness.",
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.last_checked_at = timezone.now()
        try:
            check_readiness(instance.project.slug, instance.release)
            instance.check_result = "Ready"
        except ValidationError as exc:
            instance.check_result = "; ".join(exc.messages)[:300]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ProjectDemoInline(StackedInline, TranslationStackedInline):
    model = ProjectDemo
    form = ProjectDemoForm
    extra = 0
    max_num = 1
    verbose_name = "Demo"
    readonly_fields = ("runtime", "check_result", "last_checked_at")
    fields = ("release", "enabled", "instructions", "disclosure", "runtime", "check_result", "last_checked_at")

    def get_formset(self, request, obj=None, **kwargs):
        # Django attaches the parent FK after initialization, so bind it early
        # to populate the first configuration's release selector too.
        kwargs["form"] = type("BoundProjectDemoForm", (self.form,), {"demo_project": obj})
        return super().get_formset(request, obj, **kwargs)

    def runtime(self, obj):
        if not obj.project_id or not obj.release:
            return "No release selected"
        try:
            return load_release(obj.project.slug, obj.release)["type"]
        except ValidationError:
            return "Invalid or missing release"
