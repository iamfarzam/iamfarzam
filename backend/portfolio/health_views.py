"""Deployment readiness independent of optional portfolio content."""

from django.core.cache import cache
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_safe

CACHE_PROBE_KEY = "readiness-probe"


def _database_ready():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except DatabaseError:
        return False


def _cache_ready():
    """Contact throttles are shared through the cache, so a broken cache backend
    means requests would fail even while the database answers. Any backend error
    is a failure, and details never reach the response."""
    try:
        cache.set(CACHE_PROBE_KEY, "ok", 5)
        return cache.get(CACHE_PROBE_KEY) == "ok"
    except Exception:
        return False


@require_safe
def readiness(request):
    checks = {"database": _database_ready(), "cache": _cache_ready()}
    ready = all(checks.values())
    response = JsonResponse({"ready": ready, **checks}, status=200 if ready else 503)
    response["Cache-Control"] = "no-store"
    return response
