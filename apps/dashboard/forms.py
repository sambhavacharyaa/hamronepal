from django import forms

from apps.core.forms import TailwindFormMixin

from .models import UserDocument


class UserDocumentForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UserDocument
        fields = ("title", "document_type", "image", "expiry_date")
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
        }
