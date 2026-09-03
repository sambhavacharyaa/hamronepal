from django import forms

TEXT_INPUT_CLASSES = (
    "mt-1 block w-full rounded-lg border border-outline bg-surface px-3 py-2 text-sm text-ink shadow-sm "
    "focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
)

UNSTYLED_WIDGETS = (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)


class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, UNSTYLED_WIDGETS):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TEXT_INPUT_CLASSES}".strip()
