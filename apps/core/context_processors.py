from django.conf import settings
from django.templatetags.static import static
from django.urls import translate_url

from .seo import build_organization_json_ld, to_json_ld_script


def seo(request):
    canonical_url = request.build_absolute_uri(request.path)
    hreflang_alternates = {
        code: request.build_absolute_uri(translate_url(request.path, code)) for code, _label in settings.LANGUAGES
    }
    return {
        "canonical_url": canonical_url,
        "hreflang_alternates": hreflang_alternates,
        "default_og_image": request.build_absolute_uri(static("img/og-default.png")),
        "organization_json_ld": to_json_ld_script(build_organization_json_ld(request)),
    }
