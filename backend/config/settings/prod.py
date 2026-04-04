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
