"""Production settings."""
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
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost",
    cast=lambda v: [s.strip() for s in v.split(",")],
)
