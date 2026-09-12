import json

from django.utils.safestring import mark_safe


def to_json_ld_script(data):
    return mark_safe(json.dumps(data, default=str).replace("</", "<\\/"))


def build_organization_json_ld(request):
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "HamroNepal",
        "url": request.build_absolute_uri("/"),
        "logo": request.build_absolute_uri("/static/img/logo-mark.png"),
    }


def build_website_json_ld(base_url, search_url):
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "HamroNepal",
        "url": base_url,
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{search_url}?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }


def build_breadcrumb_json_ld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": str(name),
                "item": url,
            }
            for position, (name, url) in enumerate(items, start=1)
        ],
    }
