"""Explain, per project, why an interactive demo is or is not publicly served.

Availability depends on hosting settings, files on disk, a database row and —
for backend demos — a live service. A single "unavailable" in administration
cannot distinguish those, so this command reports each layer separately.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from portfolio.demos import check_readiness, demo_availability, load_release, release_path
from portfolio.models import Project


class Command(BaseCommand):
    help = "Report why each project's interactive demo is or is not publicly available."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Limit the report to these project slugs.")
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Re-verify asset checksums and backend readiness instead of trusting the manifest.",
        )
        parser.add_argument(
            "--fail-on-unavailable",
            action="store_true",
            help="Exit non-zero when any reported project is not being served.",
        )

    def handle(self, *args, **options):
        self._report_hosting()
        projects = Project.objects.select_related("demo_config").order_by("slug")
        if options["slugs"]:
            projects = projects.filter(slug__in=options["slugs"])
            missing = set(options["slugs"]) - {p.slug for p in projects}
            for slug in sorted(missing):
                self.stdout.write(self.style.ERROR(f"  no project has the slug {slug!r}"))
        live = 0
        reported = 0
        for project in projects:
            reported += 1
            live += self._report_project(project, verify=options["verify"])
        self.stdout.write("")
        self.stdout.write(f"{live} of {reported} reported demos are being served.")
        if live < reported:
            self.stdout.write(
                "Configure a demo under its project at /admin/portfolio/project/, "
                "select a release, save, then enable it."
            )
        if options["fail_on_unavailable"] and live < reported:
            raise CommandError(f"{reported - live} demos are not being served.")

    def _report_hosting(self):
        root = settings.DEMOS_ROOT
        published = root / "published"
        try:
            release_dirs = sorted(path.name for path in published.iterdir() if path.is_dir())
        except OSError as exc:
            release_dirs = None
            self.stdout.write(self.style.ERROR(f"cannot read {published}: {exc}"))
        secret = len(settings.DEMOS_GATE_SECRET)
        self.stdout.write("Demo hosting")
        for label, value in (
            ("DEMOS_ENABLED", settings.DEMOS_ENABLED),
            ("DEMOS_ROOT", root),
            ("DEMOS_BASE_DOMAIN", settings.DEMOS_BASE_DOMAIN),
            ("DEMOS_PROXY_URL", settings.DEMOS_PROXY_URL),
            ("DEMOS_GATE_SECRET", f"{secret} characters" + ("" if secret >= 32 else " — too short")),
            ("published/", "unreadable" if release_dirs is None else f"{len(release_dirs)} project directories"),
        ):
            self.stdout.write(f"  {label:<20} {value}")
        self.stdout.write("")

    def _report_project(self, project, verify):
        demo = getattr(project, "demo_config", None)
        info, reason, code = demo_availability(project)
        style = self.style.SUCCESS if info else self.style.WARNING
        state = "SERVED" if info else "not served"
        self.stdout.write(style(f"{project.slug}  [{state}: {code}]"))
        self.stdout.write(f"  project        active={project.is_active}")
        if demo is None:
            self.stdout.write("  configuration  none")
        else:
            self.stdout.write(
                f"  configuration  release={demo.release!r} enabled={demo.enabled} "
                f"checked={demo.last_checked_at or 'never'}"
            )
            if demo.check_result:
                self.stdout.write(f"  last check     {demo.check_result}")
        self.stdout.write(f"  releases       {self._release_dirs(project.slug)}")
        if demo is not None and demo.release:
            self.stdout.write(f"  manifest       {self._manifest(project.slug, demo.release)}")
            if verify:
                self.stdout.write(f"  verification   {self._verify(project.slug, demo.release)}")
        self.stdout.write(f"  result         {info['url'] if info else reason}")
        self.stdout.write("")
        return 1 if info else 0

    def _release_dirs(self, slug):
        try:
            directory = release_path(slug, "placeholder").parent
            names = sorted(path.name for path in directory.iterdir() if path.is_dir())
        except (OSError, ValidationError) as exc:
            return f"unreadable ({exc})"
        return ", ".join(names) if names else "none published for this slug"

    def _manifest(self, slug, release):
        try:
            manifest = load_release(slug, release)
        except ValidationError as exc:
            return "; ".join(exc.messages)
        service = manifest.get("service")
        return f"type={manifest['type']}" + (f" service={service}" if service else "")

    def _verify(self, slug, release):
        try:
            check_readiness(slug, release)
        except ValidationError as exc:
            return "; ".join(exc.messages)
        return "checksums and readiness confirmed"
