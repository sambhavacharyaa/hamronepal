from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Task


class TaskForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "due_date")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}
