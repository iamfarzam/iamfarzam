from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from portfolio.demo_views import authorize_demo
from portfolio.health_views import readiness

urlpatterns = [
    path("healthz/", readiness, name="readiness"),
    path("internal/demos/authorize/", authorize_demo, name="demo-authorize"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("portfolio.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
