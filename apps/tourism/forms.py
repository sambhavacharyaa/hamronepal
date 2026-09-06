from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Trip


class TripForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Trip
        fields = ("title", "start_date", "end_date", "notes")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
