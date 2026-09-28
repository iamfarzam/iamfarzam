"""Production settings."""
from urllib.parse import urlparse

import dj_database_url
from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
    )
}

# Static files via WhiteNoise (serves static without nginx)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
# Media storage — S3-compatible when configured, local filesystem otherwise
_s3_bucket = config("S3_BUCKET_NAME", default="")
if _s3_bucket:
    _s3_options = {
        "bucket_name": _s3_bucket,
        "endpoint_url": config("S3_ENDPOINT_URL"),
        "region_name": config("S3_REGION", default="default"),
        "querystring_auth": config("S3_QUERYSTRING_AUTH", default=True, cast=bool),
        "default_acl": config("S3_DEFAULT_ACL", default="private"),
    }
    _custom_domain = config("S3_CUSTOM_DOMAIN", default="")
    if _custom_domain:
        _s3_options["custom_domain"] = _custom_domain
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": _s3_options,
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    AWS_ACCESS_KEY_ID = config("S3_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = config("S3_SECRET_KEY")
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Node's fetch() silently drops a Host header, so server-side rendering cannot
# present the public host that way and would otherwise arrive as the colour's
# internal container name. Nginx overwrites this header on every public path, so
# a visitor cannot choose it, and ALLOWED_HOSTS still validates whatever arrives.
USE_X_FORWARDED_HOST = True
# Preserve existing installations: opt in after verifying the TLS proxy hop.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_HSTS_SECONDS = config(
    "SECURE_HSTS_SECONDS",
    default=31536000 if SECURE_SSL_REDIRECT else 0,
    cast=int,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=SECURE_HSTS_SECONDS > 0,
    cast=bool,
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
# These optional, domain-wide policies require the domain owner's explicit opt-in.
# Keep all other deployment warnings active, including HTTPS and cookie checks.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

SESSION_COOKIE_SECURE = config(
    "SESSION_COOKIE_SECURE",
    default=SECURE_SSL_REDIRECT or DEMOS_ENABLED,
    cast=bool,
)
CSRF_COOKIE_SECURE = config(
    "CSRF_COOKIE_SECURE",
    default=SECURE_SSL_REDIRECT or DEMOS_ENABLED,
    cast=bool,
)

# __Host- cookies prevent a sibling demo host from shadowing portfolio cookies.
SESSION_COOKIE_NAME = "__Host-portfolio-session" if DEMOS_ENABLED else "sessionid"
CSRF_COOKIE_NAME = "__Host-portfolio-csrf" if DEMOS_ENABLED else "csrftoken"
if DEMOS_ENABLED and not (SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Production demo hosting requires secure portfolio session and CSRF cookies.")


def _csv(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def _derive_csrf_trusted_origins() -> list[str]:
    origins = _csv(config("CSRF_TRUSTED_ORIGINS", default=""))
    if origins:
        return origins

    derived: list[str] = []

    site_url = config("NEXT_PUBLIC_SITE_URL", default="").strip()
    if site_url:
        parsed = urlparse(site_url)
        if parsed.scheme and parsed.netloc:
            derived.append(f"{parsed.scheme}://{parsed.netloc}")

    for host in ALLOWED_HOSTS:  # noqa: F405
        host = host.strip().lstrip(".")
        if not host or host == "*":
            continue
        if host in {"localhost", "127.0.0.1"}:
            derived.extend([f"http://{host}", f"https://{host}"])
        else:
            derived.append(f"https://{host}")

    # Stable order + de-duplication.
    return list(dict.fromkeys(derived))


CSRF_TRUSTED_ORIGINS = _derive_csrf_trusted_origins()

# Contact throttles must be shared across workers and deployment colours.
# Derive the cache database from the broker only when it is actually Redis, and
# by URL parts: a broker written without a database ("redis://redis:6379") would
# otherwise yield "redis://1" and take the throttle cache down after an upgrade.
_broker = urlparse(CELERY_BROKER_URL)
_default_cache_url = (
    _broker._replace(path="/1").geturl() if _broker.scheme in {"redis", "rediss"} else ""
)
_cache_url = config("DJANGO_CACHE_URL", default=_default_cache_url)
if _cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_url,
        }
    }
# Otherwise keep Django's per-process default: a non-Redis broker gives us no
# shared cache to borrow, and set DJANGO_CACHE_URL to share throttles again.
# Nginx supplies exactly one trusted client address; visitor headers are replaced.
REST_FRAMEWORK["NUM_PROXIES"] = 1
