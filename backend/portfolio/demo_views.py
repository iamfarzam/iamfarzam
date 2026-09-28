"""Internal Nginx gate: validates each demo request, including assets and APIs."""

import logging
from secrets import compare_digest

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from .demos import demo_hostname, load_release, registered_service, release_path, request_asset, validate_identifier
from .models import ProjectDemo

logger = logging.getLogger(__name__)


@require_GET
def authorize_demo(request):
    response = HttpResponse(status=403)
    response["Cache-Control"] = "no-store"
    secret = settings.DEMOS_GATE_SECRET
    if not settings.DEMOS_ENABLED or len(secret) < 32 or not compare_digest(
        request.headers.get("X-Demo-Gate", ""), secret
    ):
        return response
    try:
        # Readiness probes go through the demo proxy so the portfolio backend
        # never needs access to demo networks. Only the private secret allows it.
        probe = request.headers.get("X-Demo-Probe", "")
        if probe and compare_digest(probe, secret):
            if (request.headers.get("X-Demo-URI") != "/healthz"
                    or request.headers.get("X-Demo-Method", "GET") != "GET"):
                return response
            response["X-Demo-File"] = "/__backend_route__"
            response["X-Demo-Upstream"] = registered_service(request.headers.get("X-Demo-Service"))
            response.status_code = 204
            return response
        host = request.headers.get("X-Demo-Host", "")
        suffix = f".{settings.DEMOS_BASE_DOMAIN}"
        if not host.startswith("demo-") or not host.endswith(suffix):
            return response
        slug = validate_identifier(host[5:-len(suffix)])
        if host != demo_hostname(slug):
            return response
        demo = ProjectDemo.objects.select_related("project").get(
            project__slug=slug, project__is_active=True, enabled=True
        )
        manifest = load_release(slug, demo.release)
        response["X-Demo-Script-Policy"] = "'self' 'unsafe-eval'" if manifest.get("script_eval") else "'self' 'wasm-unsafe-eval'"
        if manifest["type"] == "static":
            if request.headers.get("X-Demo-Method", "GET") not in {"GET", "HEAD"}:
                return response
            asset = request_asset(
                manifest, release_path(slug, demo.release) / "dist",
                request.headers.get("X-Demo-URI", "/"),
                "text/html" in request.headers.get("X-Demo-Accept", ""),
            )
            response["X-Demo-File"] = f"/published/{slug}/{demo.release}/dist/{asset}"
        else:
            response["X-Demo-File"] = "/__backend_route__"
            response["X-Demo-Upstream"] = registered_service(manifest["service"])
        response.status_code = 204
    except (ValidationError, ProjectDemo.DoesNotExist):
        pass
    except Exception:
        logger.exception("Demo authorization failed closed")
        response.status_code = 503
    return response
