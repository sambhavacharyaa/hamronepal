from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.forms import UserCreationForm

from apps.core.forms import TailwindFormMixin

from .models import Profile, User


class RegisterForm(TailwindFormMixin, UserCreationForm):
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
    class Meta:
        model = Profile
        fields = ("display_name", "bio", "avatar", "municipality")
