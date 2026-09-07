from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import LoginForm, PasswordResetRequestForm, ProfileForm, RegisterForm, SetPasswordForm, UserPreferencesForm
from .models import Profile, User
from .tokens import email_verification_token


def _send_verification_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse("accounts:verify_email", kwargs={"uidb64": uidb64, "token": token})
    )
    subject = _("Verify your HamroNepal email")
    body = render_to_string("accounts/email/verification_email.txt", {"user": user, "verify_url": verify_url})
    user.email_user(subject, body)


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.terms_accepted_at = timezone.now()
            user.save()
            _send_verification_email(request, user)
            auth_login(request, user)
            messages.success(request, _("Account created. Check your email to verify your address."))
            return redirect("core:dashboard")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        messages.success(request, _("Your email address has been verified."))
    else:
        messages.error(request, _("This verification link is invalid or has expired."))

    return redirect("accounts:profile" if request.user.is_authenticated else "accounts:login")


@login_required
@require_POST
@ratelimit(key="user", rate="5/m", method="POST", block=True)
def resend_verification_view(request):
    if request.user.email_verified:
        messages.info(request, _("Your email address is already verified."))
    else:
        _send_verification_email(request, request.user)
        messages.success(request, _("Verification email sent. Check your inbox."))
    return redirect("accounts:profile")


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="dispatch")
class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    form_class = LoginForm


class LogoutView(auth_views.LogoutView):
    pass


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="dispatch")
class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/email/password_reset_email.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    form_class = PasswordResetRequestForm


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")
    form_class = SetPasswordForm


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


@login_required
def profile_view(request):
    profile, _created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        preferences_form = UserPreferencesForm(request.POST, instance=request.user, prefix="preferences")
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile, prefix="profile")
        if preferences_form.is_valid() and profile_form.is_valid():
            preferences_form.save()
            profile_form.save()
            messages.success(request, _("Profile updated."))
            return redirect("core:dashboard")
    else:
        preferences_form = UserPreferencesForm(instance=request.user, prefix="preferences")
        profile_form = ProfileForm(instance=profile, prefix="profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "preferences_form": preferences_form,
            "profile_form": profile_form,
            "user_initial": (profile.display_name or request.user.email)[0].upper(),
        },
    )
