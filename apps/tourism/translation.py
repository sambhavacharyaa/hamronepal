from modeltranslation.translator import TranslationOptions, register

from .models import Destination, DestinationCategory, DestinationHighlight


@register(DestinationCategory)
class DestinationCategoryTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(Destination)
class DestinationTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "summary",
        "description",
        "highlights_intro",
        "budget_note",
        "meta_title",
        "meta_description",
    )


@register(DestinationHighlight)
class DestinationHighlightTranslationOptions(TranslationOptions):
    fields = ("title", "description")
