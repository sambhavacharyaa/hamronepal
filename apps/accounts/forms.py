from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import TailwindFormMixin

from .models import Profile, User


class RegisterForm(TailwindFormMixin, UserCreationForm):
    agree_to_terms = forms.BooleanField(
        required=True,
        error_messages={"required": _("You must agree to the Terms and Privacy Policy to create an account.")},
    )

    class Meta:
        model = User
        fields = ("email", "phone_number")


class LoginForm(TailwindFormMixin, AuthenticationForm):
    pass


class PasswordResetRequestForm(TailwindFormMixin, PasswordResetForm):
    pass


class SetPasswordForm(TailwindFormMixin, DjangoSetPasswordForm):
    pass


class UserPreferencesForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("phone_number", "preferred_language")


class ProfileForm(TailwindFormMixin, forms.ModelForm):
    remove_avatar = forms.BooleanField(required=False)

    class Meta:
        model = Profile
        fields = ("display_name", "bio", "avatar", "municipality")
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["avatar"].widget.attrs["class"] = "sr-only"
        self.fields["remove_avatar"].widget.attrs["class"] = "sr-only"

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_file_uploaded = self.files.get(self.add_prefix("avatar"))
        if self.cleaned_data.get("remove_avatar") and not new_file_uploaded:
            instance.avatar.delete(save=False)
            instance.avatar = None
        if commit:
            instance.save()
        return instance
