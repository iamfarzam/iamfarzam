"""Inventory a prepared dist directory; the validator still reviews every asset."""

import hashlib
import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from portfolio.demos import load_release, release_path, safe_path, validate_identifier


class Command(BaseCommand):
    help = "Create and validate a manifest for a staged build (does not publish or execute it)."

    def add_arguments(self, parser):
        parser.add_argument("project")
        parser.add_argument("release")
        parser.add_argument("--spa", action="store_true")
        parser.add_argument("--service", help="Registered backend service key; omit for static demos")
        parser.add_argument("--script-eval", action="store_true", help="Allow JS eval for reviewed legacy WASM bindings only")

    def handle(self, *args, **options):
        try:
            root = release_path(options["project"], options["release"], "staging")
            dist = safe_path(root, "dist")
            if not dist.is_dir():
                raise CommandError("Upload a dist directory first.")
            files = {}
            for path in dist.rglob("*"):
                safe_path(dist, path.relative_to(dist).as_posix())
                if path.is_file():
                    with path.open("rb") as stream:
                        files[path.relative_to(dist).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
            manifest = {"version": 1, "project": options["project"], "release": options["release"],
                        "type": "backend" if options["service"] else "static", "files": files,
                        "script_eval": options["script_eval"]}
            if options["service"]:
                manifest["service"] = validate_identifier(options["service"])
            else:
                manifest.update(entry="index.html", spa=options["spa"])
            safe_path(root, "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            load_release(options["project"], options["release"], "staging", verify=True)
            self.stdout.write(self.style.SUCCESS("Manifest created and validated. Not published."))
        except (ValidationError, OSError) as exc:
            raise CommandError(str(exc)) from exc
