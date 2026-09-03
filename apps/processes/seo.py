import json
from decimal import Decimal

from django.utils.safestring import mark_safe


def to_json_ld_script(data):
    return mark_safe(json.dumps(data).replace("</", "<\\/"))


def build_howto_json_ld(process, steps):
    data = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": process.title,
        "description": process.summary or process.description,
        "step": [
            {
                "@type": "HowToStep",
                "position": step.order,
                "name": step.title,
                "text": step.description or step.title,
            }
            for step in steps
        ],
    }

    duration_days = process.estimated_duration_max_days or process.estimated_duration_min_days
    if duration_days:
        data["totalTime"] = f"P{duration_days}D"

    total_fee = sum((step.fee_amount for step in steps if step.fee_amount), Decimal("0"))
    if total_fee:
        data["estimatedCost"] = {
            "@type": "MonetaryAmount",
            "currency": "NPR",
            "value": str(total_fee),
        }

    return data


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


def build_faq_json_ld(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq.question,
                "acceptedAnswer": {"@type": "Answer", "text": faq.answer},
            }
            for faq in faqs
        ],
    }
