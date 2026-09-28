"""Security and availability regressions for separately uploaded demo releases."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from portfolio.demos import check_readiness, demo_hostname, load_release, registered_service, safe_path
from portfolio.models import Project, ProjectDemo
from portfolio.serializers import ProjectDetailSerializer, ProjectListSerializer


class DemoTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.override = override_settings(
            DEMOS_ROOT=self.root, DEMOS_ENABLED=True, DEMOS_BASE_DOMAIN="example.com",
            DEMOS_GATE_SECRET="a" * 48,
        )
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.project = Project.objects.create(title="Sample", slug="sample", summary="Sample")
        self.release = self.make_release()
        self.demo = ProjectDemo.objects.create(project=self.project, release="v1", enabled=True)

    def make_release(self, area="published", runtime="static"):
        root = self.root / area / "sample" / "v1"
        (root / "dist").mkdir(parents=True, exist_ok=True)
        content = b"<!doctype html><title>Fictional demo</title>"
        (root / "dist/index.html").write_bytes(content)
        manifest = {"version": 1, "project": "sample", "release": "v1", "type": runtime,
                    "entry": "index.html", "spa": True,
                    "files": {"index.html": hashlib.sha256(content).hexdigest()}}
        if runtime == "backend":
            manifest["service"] = "sample"
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return root

    def gate(self, **headers):
        defaults = {"HTTP_X_DEMO_GATE": "a" * 48, "HTTP_X_DEMO_HOST": "demo-sample.example.com",
                    "HTTP_X_DEMO_URI": "/", "HTTP_X_DEMO_METHOD": "GET", "HTTP_X_DEMO_ACCEPT": "text/html"}
        defaults.update(headers)
        return self.client.get("/internal/demos/authorize/", **defaults)

    def test_defaults_are_disabled(self):
        self.assertFalse(ProjectDemo(project=self.project).enabled)

    def test_only_reserved_first_level_demo_hosts_are_authorized(self):
        self.assertEqual(demo_hostname("sample"), "demo-sample.example.com")
        for host in ["sample.example.com", "sample.demos.example.com", "example.com",
                     "www.example.com", "demo-sample.example.com.attacker.test",
                     "demo-sample.example.com:443", "demo-samplexexample.com"]:
            with self.subTest(host=host):
                self.assertEqual(self.gate(HTTP_X_DEMO_HOST=host).status_code, 403)

    def test_demo_prefix_counts_toward_dns_label_limit(self):
        self.assertEqual(demo_hostname("a" * 58), f"demo-{'a' * 58}.example.com")
        with self.assertRaises(ValidationError):
            demo_hostname("a" * 59)

    def test_invalid_root_domain_prevents_demo_activation(self):
        for domain in ["https://example.com", "*.example.com", "example.com/path",
                       "example.com:443", "example..com", "-example.com", "a" * 64 + ".com"]:
            with self.subTest(domain=domain), override_settings(DEMOS_BASE_DOMAIN=domain):
                with self.assertRaises(ValidationError):
                    check_readiness("sample", "v1")
                self.assertIsNone(ProjectListSerializer(self.project).data["demo"])

    def test_gate_does_not_require_visitor_authentication(self):
        response = self.gate()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["X-Demo-File"], "/published/sample/v1/dist/index.html")

    def test_disable_revokes_direct_requests(self):
        self.demo.enabled = False
        self.demo.save()
        self.assertEqual(self.gate().status_code, 403)

    def test_inactive_project_revokes_direct_requests(self):
        self.project.is_active = False
        self.project.save()
        self.assertEqual(self.gate().status_code, 403)

    def test_missing_secret_unknown_host_and_global_disable(self):
        self.assertEqual(self.gate(HTTP_X_DEMO_GATE="").status_code, 403)
        self.assertEqual(self.gate(HTTP_X_DEMO_HOST="sample.attacker.example").status_code, 403)
        self.assertEqual(self.gate(HTTP_X_DEMO_HOST="nested.demo-sample.example.com").status_code, 403)
        with override_settings(DEMOS_ENABLED=False):
            self.assertEqual(self.gate().status_code, 403)
        with override_settings(DEMOS_GATE_SECRET="short"):
            self.assertEqual(self.gate().status_code, 403)

    def test_spa_only_falls_back_for_html_navigation(self):
        self.assertEqual(self.gate(HTTP_X_DEMO_URI="/bookings/123").status_code, 204)
        self.assertEqual(self.gate(HTTP_X_DEMO_URI="/missing.js").status_code, 403)
        self.assertEqual(self.gate(HTTP_X_DEMO_URI="/api/data", HTTP_X_DEMO_ACCEPT="application/json").status_code, 403)
        self.assertEqual(self.gate(HTTP_X_DEMO_METHOD="POST").status_code, 403)

    def test_private_and_noncanonical_request_paths_are_denied(self):
        for uri in ["/../private/key", "/%2e%2e/private", "/%252e%252e/private", "/.env",
                    "/manifest.json", "//index.html", "/folder\\index.html", "/foo/./bar"]:
            with self.subTest(uri=uri):
                self.assertEqual(self.gate(HTTP_X_DEMO_URI=uri).status_code, 403)

    def test_enabling_requires_validated_release_and_configured_secret(self):
        self.demo.release = "missing"
        with self.assertRaises(ValidationError):
            self.demo.full_clean()
        self.demo.enabled = False
        self.demo.full_clean()
        self.demo.enabled = True
        self.demo.release = "v1"
        with override_settings(DEMOS_GATE_SECRET=""):
            with self.assertRaises(ValidationError):
                self.demo.full_clean()

    def test_checksum_corruption_and_unlisted_files_are_rejected(self):
        (self.release / "dist/index.html").write_text("modified", encoding="utf-8")
        with self.assertRaises(ValidationError):
            load_release("sample", "v1", verify=True)
        self.make_release()
        (self.release / "dist/source.map").write_text("source", encoding="utf-8")
        with self.assertRaises(ValidationError):
            load_release("sample", "v1", verify=True)

    def test_secret_in_inventoried_text_asset_is_rejected(self):
        content = b'const smtp_password = "a-private-password";'
        (self.release / "dist/index.html").write_bytes(content)
        manifest = json.loads((self.release / "manifest.json").read_text())
        manifest["files"]["index.html"] = hashlib.sha256(content).hexdigest()
        (self.release / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValidationError):
            load_release("sample", "v1", verify=True)

    def test_symlink_is_rejected_even_when_it_points_inside_dist(self):
        link = self.release / "dist/link.html"
        try:
            link.symlink_to(self.release / "dist/index.html")
        except OSError:
            self.skipTest("OS does not permit creating symlinks")
        with self.assertRaises(ValidationError):
            safe_path(self.release / "dist", "link.html")

    def test_manifest_and_release_identifiers_cannot_escape_storage(self):
        for name in ["../private", "Upper", "a/b", "", "a" * 64]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                load_release("sample", name)

    def test_publish_is_atomic_and_cannot_replace_existing_release(self):
        self.make_release(area="staging")
        with self.assertRaises(CommandError):
            call_command("demo_release", "sample", "v1", publish=True)
        self.assertTrue((self.root / "staging/sample/v1").exists())
        # A new project can publish without changing its availability in the DB.
        self.demo.delete()
        import shutil
        shutil.rmtree(self.release)
        call_command("demo_release", "sample", "v1", publish=True)
        self.assertTrue(self.release.is_dir())
        self.assertTrue((self.root / "staging/sample/v1").exists())

    def test_published_snapshot_cannot_be_modified_through_an_open_upload(self):
        import shutil
        shutil.rmtree(self.release)
        staging = self.make_release(area="staging")
        with (staging / "dist/index.html").open("r+b") as upload:
            call_command("demo_release", "sample", "v1", publish=True)
            upload.seek(0)
            upload.write(b"changed after publication")
            upload.flush()
        self.assertEqual((self.release / "dist/index.html").read_bytes(),
                         b"<!doctype html><title>Fictional demo</title>")
        load_release("sample", "v1", verify=True)

    def test_changed_snapshot_is_rejected_before_it_becomes_public(self):
        import shutil
        from portfolio.management.commands.demo_release import snapshot_upload
        shutil.rmtree(self.release)
        self.make_release(area="staging")

        def changed_copy(source, destination):
            snapshot_upload(source, destination)
            (destination / "dist/index.html").write_bytes(b"changed during upload")

        with patch("portfolio.management.commands.demo_release.snapshot_upload", side_effect=changed_copy):
            with self.assertRaises(CommandError):
                call_command("demo_release", "sample", "v1", publish=True)
        self.assertFalse(self.release.exists())
        self.assertEqual(list(self.release.parent.iterdir()), [])

    def test_serializers_expose_only_public_demo_info(self):
        for serializer in [ProjectListSerializer, ProjectDetailSerializer]:
            data = serializer(self.project).data
            self.assertEqual(set(data["demo"]), {"url", "type", "instructions", "disclosure"})
            self.assertNotIn(str(self.root), json.dumps(data))
            self.assertEqual(data["demo"]["url"], "https://demo-sample.example.com/")
        self.demo.enabled = False
        self.demo.save()
        self.project.refresh_from_db()
        self.assertIsNone(ProjectListSerializer(self.project).data["demo"])

    def test_linux_publication_removes_uploader_write_permissions(self):
        if os.name != "posix":
            self.skipTest("Linux ownership and modes")
        import shutil
        shutil.rmtree(self.release)
        staging = self.make_release(area="staging")
        for path in [staging, *staging.rglob("*")]:
            path.chmod(0o777)
            if os.geteuid() == 0:
                os.chown(path, 10001, 10001)
        call_command("demo_release", "sample", "v1", publish=True)
        for path in [self.release, *self.release.rglob("*")]:
            self.assertEqual(path.stat().st_uid, os.geteuid())
            self.assertEqual(path.stat().st_mode & 0o777, 0o755 if path.is_dir() else 0o644)

    def registry(self, url="http://demo-sample:8080"):
        (self.root / "config").mkdir(exist_ok=True)
        (self.root / "config/services.json").write_text(json.dumps({"sample": {"url": url}}))

    def test_backend_registry_rejects_arbitrary_destinations(self):
        for url in ["http://backend:8000", "http://127.0.0.1:8080", "http://demo-sample:8080/path",
                    "http://user:pass@demo-sample:8080", "https://external.example:443"]:
            self.registry(url)
            with self.subTest(url=url), self.assertRaises(ValidationError):
                registered_service("sample")
        self.registry()
        self.assertEqual(registered_service("sample"), "http://demo-sample:8080")

    def test_backend_gate_and_disabled_health_probe(self):
        self.make_release(runtime="backend")
        self.registry()
        self.assertEqual(self.gate()["X-Demo-Upstream"], "http://demo-sample:8080")
        self.demo.enabled = False
        self.demo.save()
        self.assertEqual(self.gate().status_code, 403)
        response = self.gate(HTTP_X_DEMO_PROBE="a" * 48, HTTP_X_DEMO_SERVICE="sample", HTTP_X_DEMO_URI="/healthz")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.gate(HTTP_X_DEMO_PROBE="wrong", HTTP_X_DEMO_URI="/healthz").status_code, 403)
        self.assertEqual(self.gate(HTTP_X_DEMO_PROBE="a" * 48, HTTP_X_DEMO_SERVICE="sample").status_code, 403)

    def test_backend_health_failure_blocks_enable(self):
        self.make_release(runtime="backend")
        self.registry()
        with patch("portfolio.demos.build_opener") as opener:
            opener.return_value.open.side_effect = TimeoutError()
            with self.assertRaises(ValidationError):
                check_readiness("sample", "v1")

    def test_healthy_backend_with_wrong_release_cannot_be_enabled(self):
        self.make_release(runtime="backend")
        self.registry()
        with patch("portfolio.demos.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b'{"ready":true,"release":"v2"}'
            with self.assertRaises(ValidationError):
                check_readiness("sample", "v1")
            response.read.return_value = b'{"ready":true,"release":"v1"}'
            self.assertEqual(check_readiness("sample", "v1")["type"], "backend")
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header("Host"), "demo-sample.example.com")

    def test_database_errors_fail_closed(self):
        with patch("portfolio.demo_views.ProjectDemo.objects.select_related", side_effect=RuntimeError("offline")):
            self.assertEqual(self.gate().status_code, 503)

    def test_project_admin_includes_release_selector(self):
        from portfolio.demo_admin import ProjectDemoForm
        form = ProjectDemoForm(instance=self.demo)
        self.assertIn(("v1", "v1"), form.fields["release"].choices)
        user = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.create_superuser(
            "owner", "owner@example.test", "test-password"
        )
        self.client.force_login(user)
        response = self.client.get(f"/admin/portfolio/project/{self.project.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v1")
        self.demo.delete()
        response = self.client.get(f"/admin/portfolio/project/{self.project.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="v1">v1</option>', html=True)

    def test_dependency_review_is_bound_to_exact_bytes(self):
        content = b'const smtp_password = "a-private-password";'
        (self.release / "dist/index.html").write_bytes(content)
        manifest = json.loads((self.release / "manifest.json").read_text())
        checksum = hashlib.sha256(content).hexdigest()
        manifest["files"]["index.html"] = checksum
        (self.release / "manifest.json").write_text(json.dumps(manifest))
        (self.root / "config").mkdir()
        (self.root / "config/reviewed-assets.json").write_text(json.dumps({checksum: "Operator reviewed this fictional fixture for the test."}))
        load_release("sample", "v1", verify=True)
        (self.release / "dist/index.html").write_bytes(content + b"changed")
        manifest["files"]["index.html"] = hashlib.sha256(content + b"changed").hexdigest()
        (self.release / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValidationError):
            load_release("sample", "v1", verify=True)
