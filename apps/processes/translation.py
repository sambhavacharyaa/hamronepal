from modeltranslation.translator import TranslationOptions, register

from .models import Process, ProcessCategory, ProcessFAQ, ProcessRequirement, ProcessStep


@register(ProcessCategory)
class ProcessCategoryTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(Process)
class ProcessTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "summary",
        "description",
        "eligibility",
        "estimated_duration_note",
        "total_fee_note",
        "meta_title",
        "meta_description",
    )


@register(ProcessStep)
class ProcessStepTranslationOptions(TranslationOptions):
    fields = ("title", "description", "fee_note", "estimated_duration_note")


@register(ProcessRequirement)
class ProcessRequirementTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(ProcessFAQ)
class ProcessFAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")
