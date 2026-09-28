import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class ProductionSettingsTests(SimpleTestCase):
    def read_settings(self, overrides=None):
        env = os.environ.copy()
        for name in (
            "SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE",
            "SECURE_HSTS_SECONDS", "SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "SECURE_HSTS_PRELOAD", "DJANGO_CACHE_URL", "S3_BUCKET_NAME",
        ):
            env.pop(name, None)
        env.update({
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
            "DJANGO_SECRET_KEY": "isolated-settings-test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": "sqlite:///:memory:",
            "CELERY_BROKER_URL": "redis://redis:6379/0",
            "DEMOS_ENABLED": "False",
        })
        env.update(overrides or {})
        result = subprocess.run(
            [sys.executable, "-c", (
                "import json; from django.conf import settings as s; "
                "print(json.dumps({k: getattr(s, k) for k in "
                "['DEBUG', 'SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE', "
                "'CSRF_COOKIE_SECURE', 'SECURE_HSTS_SECONDS', "
                "'SECURE_HSTS_INCLUDE_SUBDOMAINS', 'SECURE_HSTS_PRELOAD', "
                "'SILENCED_SYSTEM_CHECKS', 'CACHES', 'REST_FRAMEWORK', 'USE_X_FORWARDED_HOST']}))"
            )],
            cwd=settings.BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_explicit_https_settings_and_shared_throttles(self):
        result = self.read_settings({
            "SECURE_SSL_REDIRECT": "True",
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": "False",
        })
        self.assertFalse(result["DEBUG"])
        for name in ("SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"):
            self.assertTrue(result[name])
        self.assertEqual(result["SECURE_HSTS_SECONDS"], 31536000)
        self.assertFalse(result["SECURE_HSTS_INCLUDE_SUBDOMAINS"])
        self.assertFalse(result["SECURE_HSTS_PRELOAD"])
        self.assertEqual(result["SILENCED_SYSTEM_CHECKS"], ["security.W005", "security.W021"])
        self.assertEqual(result["CACHES"]["default"]["BACKEND"], "django.core.cache.backends.redis.RedisCache")
        self.assertEqual(result["CACHES"]["default"]["LOCATION"], "redis://redis:6379/1")
        self.assertEqual(result["REST_FRAMEWORK"]["NUM_PROXIES"], 1)
        # Server-side rendering can only present the public host this way.
        self.assertTrue(result["USE_X_FORWARDED_HOST"])

    def test_isolated_http_override_and_custom_cache(self):
        result = self.read_settings({
            "SECURE_SSL_REDIRECT": "False",
            "DJANGO_CACHE_URL": "redis://cache:6379/2",
        })
        self.assertFalse(result["SECURE_SSL_REDIRECT"])
        self.assertFalse(result["SESSION_COOKIE_SECURE"])
        self.assertFalse(result["CSRF_COOKIE_SECURE"])
        self.assertEqual(result["SECURE_HSTS_SECONDS"], 0)
        self.assertEqual(result["CACHES"]["default"]["LOCATION"], "redis://cache:6379/2")

    def test_broker_without_a_database_still_yields_a_reachable_cache(self):
        result = self.read_settings({"CELERY_BROKER_URL": "redis://redis:6379"})
        self.assertEqual(result["CACHES"]["default"]["LOCATION"], "redis://redis:6379/1")

    def test_non_redis_broker_is_never_used_as_a_cache_location(self):
        result = self.read_settings({"CELERY_BROKER_URL": "amqp://broker:example-password@rabbit:5672//"})
        self.assertNotIn("redis", result["CACHES"]["default"]["BACKEND"])
        self.assertNotIn("amqp", json.dumps(result["CACHES"]))

    def test_existing_proxy_deployments_keep_their_redirect_default(self):
        result = self.read_settings()
        self.assertFalse(result["SECURE_SSL_REDIRECT"])
        self.assertEqual(result["SECURE_HSTS_SECONDS"], 0)
