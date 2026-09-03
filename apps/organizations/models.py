from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class GovernmentOrganization(TimeStampedModel):
    class OrganizationType(models.TextChoices):
        MINISTRY = "ministry", _("Ministry")
        DEPARTMENT = "department", _("Department")
        CONSTITUTIONAL_BODY = "constitutional_body", _("Constitutional Body")
        LOCAL_GOVERNMENT = "local_government", _("Local Government")
        OTHER = "other", _("Other")

    name = models.CharField(max_length=200)
    name_ne = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True)
    type = models.CharField(max_length=30, choices=OrganizationType.choices)
    website_url = models.URLField(blank=True)
    logo = models.ImageField(upload_to="organizations/logos/", blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GovernmentOffice(TimeStampedModel):
    organization = models.ForeignKey(GovernmentOrganization, on_delete=models.CASCADE, related_name="offices")
    name = models.CharField(max_length=200)
    name_ne = models.CharField(max_length=200, blank=True)
    municipality = models.ForeignKey(
        "locations.Municipality",
        on_delete=models.PROTECT,
        related_name="government_offices",
    )
    ward = models.ForeignKey(
        "locations.Ward",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="government_offices",
    )
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    office_hours = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"
