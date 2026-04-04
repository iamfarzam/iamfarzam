from django.conf import settings
from django.utils import translation


class LanguageFromRequestMiddleware:
    """Activate translation from ?lang= param or Accept-Language header."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.supported = {code for code, _ in settings.LANGUAGES}

    def __call__(self, request):
        lang = request.GET.get("lang", "").strip()
        if not lang:
            accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
            lang = accept.split(",")[0].split(";")[0].strip()
        # Map short codes
        if lang == "zh":
            lang = "zh-hans"
        if lang in self.supported:
            translation.activate(lang)
            request.LANGUAGE_CODE = lang
        response = self.get_response(request)
        return response
