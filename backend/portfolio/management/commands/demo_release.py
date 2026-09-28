"""Validate an immutable SFTP release and atomically make it selectable in admin."""

import os
import shutil
import stat
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from portfolio.demos import load_release, release_path, validate_release


def snapshot_upload(source, destination):
    """Copy bytes into new inodes; never follow uploader-controlled links."""
    if os.name != "posix":
        # Local development only; production publication uses Linux dirfds.
        shutil.copytree(source, destination, symlinks=True, dirs_exist_ok=True)
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(source.anchor, flags)
    try:
        for component in source.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        remaining = [20000]

        def copy_directory(directory_fd, target, depth=0):
            if depth > 100:
                raise ValidationError("Upload directory nesting is too deep.")
            for name in os.listdir(directory_fd):
                remaining[0] -= 1
                if remaining[0] < 0:
                    raise ValidationError("Upload contains too many entries.")
                entry_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                   dir_fd=directory_fd)
                try:
                    mode = os.fstat(entry_fd).st_mode
                    path = target / name
                    if stat.S_ISDIR(mode):
                        path.mkdir(mode=0o755)
                        copy_directory(entry_fd, path, depth + 1)
                        path.chmod(0o755)
                    elif stat.S_ISREG(mode):
                        with os.fdopen(os.dup(entry_fd), "rb") as incoming, path.open("xb") as outgoing:
                            shutil.copyfileobj(incoming, outgoing)
                        path.chmod(0o644)
                    else:
                        raise ValidationError("Uploads must contain only regular files and directories.")
                finally:
                    os.close(entry_fd)

        copy_directory(descriptor, destination)
    finally:
        os.close(descriptor)


class Command(BaseCommand):
    help = "Validate a staged demo release; --publish atomically promotes it (never executes code)."

    def add_arguments(self, parser):
        parser.add_argument("project")
        parser.add_argument("release")
        parser.add_argument("--publish", action="store_true")
        parser.add_argument("--published", action="store_true", help="Verify an already published release")

    def handle(self, *args, **options):
        try:
            area = "published" if options["published"] else "staging"
            load_release(options["project"], options["release"], area=area, verify=True)
            if options["publish"]:
                if options["published"]:
                    raise CommandError("--publish and --published cannot be combined")
                source = release_path(options["project"], options["release"], "staging")
                destination = release_path(options["project"], options["release"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise CommandError("Release already exists; upload a new release ID instead.")
                with tempfile.TemporaryDirectory(prefix=".publication-", dir=destination.parent) as temporary:
                    snapshot = Path(temporary)
                    snapshot_upload(source.absolute(), snapshot)
                    # Validate the exact bytes to be served, after copying. The
                    # uploader's open file handles cannot modify these new inodes.
                    validate_release(snapshot, options["project"], options["release"], verify=True)
                    snapshot.chmod(0o755)
                    snapshot.rename(destination)
                self.stdout.write(self.style.SUCCESS("Published. Select the release in project admin; it remains disabled."))
            else:
                self.stdout.write(self.style.SUCCESS("Validated. Review asset rights and synthetic data before publishing."))
        except (ValidationError, OSError) as exc:
            raise CommandError(str(exc)) from exc
