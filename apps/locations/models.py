from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Province(TimeStampedModel):
    name = models.CharField(max_length=100)
    name_ne = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(TimeStampedModel):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=100)
    name_ne = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "districts"

    def __str__(self):
        return self.name


class Municipality(TimeStampedModel):
    class MunicipalityType(models.TextChoices):
        METROPOLITAN = "metropolitan", _("Metropolitan City")
        SUB_METROPOLITAN = "sub_metropolitan", _("Sub-Metropolitan City")
        MUNICIPALITY = "municipality", _("Municipality")
        RURAL_MUNICIPALITY = "rural_municipality", _("Rural Municipality")

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="municipalities")
    name = models.CharField(max_length=100)
    name_ne = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=10, unique=True)
    type = models.CharField(max_length=20, choices=MunicipalityType.choices)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "municipalities"

    def __str__(self):
        return self.name


class Ward(TimeStampedModel):
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name="wards")
    number = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["municipality", "number"]
        unique_together = ("municipality", "number")

    def __str__(self):
        return f"{self.municipality.name} Ward {self.number}"
