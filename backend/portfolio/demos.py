"""Validation and routing for private demo releases. No uploaded code executes here."""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError

IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
PUBLIC_SUFFIXES = {".html", ".js", ".mjs", ".css", ".json", ".png", ".jpg", ".jpeg",
                   ".webp", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf",
                   ".wasm", ".bin", ".tflite", ".task", ".txt", ".xml", ".mp4", ".webm", ".mp3", ".ogg"}
SECRET_PATTERNS = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?-i:AKIA[0-9A-Z]{16})|"
    rb"(?:postgres(?:ql)?|mysql|redis)://[^\s\"']+:[^\s\"']+@|"
    rb"(?:smtp_password|secret_key|api_secret)\s*[\"']?\s*[:=]\s*[\"'][^\"']{8,}",
    re.IGNORECASE,
)


def validate_identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError("Use a lowercase DNS label (letters, numbers, hyphens; max 63 characters).")
    return value


def demo_hostname(slug):
    """One first-level DNS label, with a reserved namespace for demo origins."""
    validate_identifier(slug)
    label = validate_identifier(f"demo-{slug}")
    domain = settings.DEMOS_BASE_DOMAIN
    if (not isinstance(domain, str)
            or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain)
            or len(f"{label}.{domain}") > 253):
        raise ValidationError("Configure a valid root demo domain without a scheme, path or wildcard.")
    return f"{label}.{domain}"


def safe_path(root, relative):
    """Reject noncanonical names and every symlink, including directory ancestors."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError("Invalid demo asset path.")
    parts = PurePosixPath(relative).parts
    if (relative.startswith("/") or PurePosixPath(relative).as_posix() != relative
            or any(part in {".", ".."} or part.startswith(".") for part in parts)
            or any(ord(char) < 32 or char in "%?#:" for char in relative)):
        raise ValidationError("Invalid demo asset path.")
    target = root
    # Checking the lexical chain matters: resolve() alone silently follows links.
    for ancestor in [root, *root.parents]:
        if ancestor.is_symlink():
            raise ValidationError("Demo directories cannot be symlinks.")
    for part in parts:
        target = target / part
        if target.is_symlink():
            raise ValidationError("Demo assets cannot be symlinks.")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValidationError("Asset escapes the demo directory.")
    return target


def release_path(slug, release, area="published"):
    validate_identifier(slug)
    validate_identifier(release)
    return safe_path(Path(settings.DEMOS_ROOT), f"{area}/{slug}/{release}")


def read_json(path):
    try:
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ValidationError("Demo manifest or registry is too large.")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValidationError("Expected a JSON object.")
        return value
    except (OSError, ValueError) as exc:
        raise ValidationError("Demo manifest or registry is missing or invalid.") from exc


def load_release(slug, release, area="published", verify=False):
    root = release_path(slug, release, area)
    return validate_release(root, slug, release, verify=verify)


def validate_release(root, slug, release, verify=False):
    """Validate a release, including a private publication snapshot."""
    manifest = read_json(safe_path(root, "manifest.json"))
    if (manifest.get("version") != 1 or manifest.get("project") != slug
            or manifest.get("release") != release or manifest.get("type") not in {"static", "backend"}):
        raise ValidationError("Manifest version, project, release, or runtime is invalid.")
    files = manifest.get("files")
    if not isinstance(files, dict) or len(files) > 10000:
        raise ValidationError("Manifest must contain a bounded asset/checksum inventory.")
    dist = safe_path(root, "dist")
    for name, checksum in files.items():
        path = safe_path(dist, name)
        if path.suffix.lower() not in PUBLIC_SUFFIXES or not re.fullmatch(r"[a-f0-9]{64}", str(checksum)):
            raise ValidationError("Unapproved asset type or invalid checksum.")
        if not path.is_file():
            raise ValidationError(f"Missing asset: {name}")
        if verify:
            with path.open("rb") as stream:
                actual_checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual_checksum != checksum:
                raise ValidationError(f"Checksum mismatch: {name}")
            if path.suffix.lower() in {".html", ".js", ".mjs", ".css", ".json", ".txt", ".xml", ".svg"}:
                if path.stat().st_size > 20 * 1024 * 1024:
                    raise ValidationError("Text assets must be smaller than 20 MiB.")
                if SECRET_PATTERNS.search(path.read_bytes()):
                    review_path = safe_path(Path(settings.DEMOS_ROOT), "config/reviewed-assets.json")
                    reviewed = read_json(review_path) if review_path.is_file() else {}
                    reason = reviewed.get(checksum)
                    if not isinstance(reason, str) or len(reason.strip()) < 20:
                        raise ValidationError(f"Possible embedded credential: {name}; operator review required.")
    if verify:
        allowed = {"manifest.json", *[f"dist/{name}" for name in files]}
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            safe_path(root, relative)
            if not path.is_dir() and (not path.is_file() or relative not in allowed):
                raise ValidationError(f"Unlisted or private file: {relative}")
    if manifest["type"] == "static":
        if manifest.get("entry", "index.html") != "index.html" or "index.html" not in files:
            raise ValidationError("Static demos require an inventoried index.html.")
        if not isinstance(manifest.get("spa", False), bool):
            raise ValidationError("spa must be a boolean.")
    else:
        validate_identifier(manifest.get("service"))
    if not isinstance(manifest.get("script_eval", False), bool):
        raise ValidationError("script_eval must be a boolean.")
    return manifest


def registered_service(key):
    """Only operator-owned registry entries can select an internal demo service."""
    validate_identifier(key)
    registry = read_json(safe_path(Path(settings.DEMOS_ROOT), "config/services.json"))
    service = registry.get(key)
    if not isinstance(service, dict):
        raise ValidationError("Backend service has not been registered by the operator.")
    url = service.get("url", "")
    if not isinstance(url, str):
        raise ValidationError("Service URL must be a string.")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise ValidationError("Service URL is invalid.") from exc
    # Demo-only Docker DNS names prevent registry mistakes pointing at portfolio services.
    if (parsed.scheme != "http" or not re.fullmatch(r"demo-[a-z0-9-]+", parsed.hostname or "")
            or parsed.username or parsed.password or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment):
        raise ValidationError("Service URL must use an internal demo-* Docker hostname and no path.")
    try:
        if not parsed.port or not 1 <= parsed.port <= 65535:
            raise ValueError
    except ValueError as exc:
        raise ValidationError("Service URL requires a valid port.") from exc
    return url.rstrip("/")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_readiness(slug, release):
    if not settings.DEMOS_ENABLED or len(settings.DEMOS_GATE_SECRET) < 32:
        raise ValidationError("Enable demo hosting and configure a gate secret of at least 32 characters.")
    demo_hostname(slug)
    manifest = load_release(slug, release, verify=True)
    if manifest["type"] == "backend":
        check_backend_health(slug, manifest["service"], release)
    return manifest


def check_backend_health(slug, service, release):
    registered_service(service)
    try:
        opener = build_opener(NoRedirect(), ProxyHandler({}))
        probe = Request(f"{settings.DEMOS_PROXY_URL.rstrip('/')}/healthz", headers={
            "Host": demo_hostname(slug),
            "X-Demo-Probe": settings.DEMOS_GATE_SECRET,
            "X-Demo-Service": service,
        })
        with opener.open(probe, timeout=settings.DEMOS_HEALTH_TIMEOUT) as response:
            if response.status != 200:
                raise ValueError("unhealthy")
            health = json.loads(response.read(4097))
            if not isinstance(health, dict) or health.get("ready") is not True or health.get("release") != release:
                raise ValueError("Backend is serving a different release.")
    except Exception as exc:
        raise ValidationError("Registered demo service must report ready and the selected release at /healthz.") from exc


def backend_ready(slug, service, release):
    """Cached readiness for a registered backend demo service."""
    try:
        url = registered_service(service)
    except ValidationError:
        return False
    key = "demo-health:" + hashlib.sha256(
        f"{settings.DEMOS_ROOT}:{url}:{settings.DEMOS_GATE_SECRET}:{slug}:{release}".encode()
    ).hexdigest()
    ready = cache.get(key)
    if ready is None:
        try:
            check_backend_health(slug, service, release)
            ready = True
        except ValidationError:
            ready = False
        cache.set(key, ready, 15)
    return ready


def demo_availability(project):
    """Return ``(public payload or None, reason, code)`` for one project's demo.

    Availability spans hosting settings, files on disk, a database row and, for
    backend demos, a live service. The code names which of those layers stopped
    the demo so administration and ``demo_doctor`` can say more than
    "unavailable"; the reason is the sentence they render. Neither reaches a
    public response, because a visitor must not learn whether a demo exists but
    is misconfigured.
    """
    if not settings.DEMOS_ENABLED:
        return None, "Demo hosting is off; set DEMOS_ENABLED=True and redeploy.", "hosting_off"
    if len(settings.DEMOS_GATE_SECRET) < 32:
        return None, "DEMOS_GATE_SECRET must hold at least 32 characters.", "hosting_off"
    demo = getattr(project, "demo_config", None)
    if demo is None:
        return None, "No demo configuration. Add one on this project and select a release.", "unconfigured"
    if not project.is_active:
        return None, "The project itself is inactive, so its demo stays private.", "not_enabled"
    if not demo.enabled:
        return None, "The demo configuration exists but is not enabled.", "not_enabled"
    try:
        manifest = load_release(project.slug, demo.release)
        url = f"https://{demo_hostname(project.slug)}/"
    except ValidationError as exc:
        return None, "; ".join(exc.messages), "invalid_release"
    if manifest["type"] == "backend" and not backend_ready(project.slug, manifest["service"], demo.release):
        return None, (
            f"Registered service {manifest['service']!r} is not reporting release "
            f"{demo.release} ready at /healthz."
        ), "service_down"
    return {
        "url": url,
        "type": manifest["type"],
        "instructions": demo.instructions,
        "disclosure": demo.disclosure,
    }, "", "served"


def demo_public_info(project):
    return demo_availability(project)[0]


def request_asset(manifest, root, uri, accepts_html=False):
    raw_path = uri.split("?", 1)[0]
    path = unquote(raw_path)
    # No ambiguous second decoding or normalization at the proxy/filesystem boundary.
    if "%" in path or not path.startswith("/") or path.startswith("//"):
        raise ValidationError("Invalid request path.")
    name = path[1:] or "index.html"
    safe_path(root, name.rstrip("/"))
    if name in manifest["files"]:
        return name
    if (manifest.get("spa", False) and accepts_html
            and not PurePosixPath(name.rstrip("/")).suffix):
        return "index.html"
    raise ValidationError("Demo asset not found.")
