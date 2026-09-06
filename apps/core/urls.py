from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("privacy/", views.privacy_policy_view, name="privacy_policy"),
    path("terms/", views.terms_view, name="terms"),
    path("cookies/", views.cookie_policy_view, name="cookie_policy"),
    path("refunds/", views.refund_policy_view, name="refund_policy"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
]
