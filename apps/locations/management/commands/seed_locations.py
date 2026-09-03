from django.core.management.base import BaseCommand
from django.db import transaction

from apps.locations.models import District, Municipality, Province

PROVINCES = [
    (
        "Koshi Province",
        "koshi",
        [
            "Bhojpur", "Dhankuta", "Ilam", "Jhapa", "Khotang", "Morang", "Okhaldhunga",
            "Panchthar", "Sankhuwasabha", "Solukhumbu", "Sunsari", "Taplejung", "Terhathum", "Udayapur",
        ],
    ),
    (
        "Madhesh Province",
        "madhesh",
        ["Bara", "Dhanusha", "Mahottari", "Parsa", "Rautahat", "Saptari", "Sarlahi", "Siraha"],
    ),
    (
        "Bagmati Province",
        "bagmati",
        [
            "Bhaktapur", "Chitwan", "Dhading", "Dolakha", "Kathmandu", "Kavrepalanchok", "Lalitpur",
            "Makwanpur", "Nuwakot", "Ramechhap", "Rasuwa", "Sindhuli", "Sindhupalchok",
        ],
    ),
    (
        "Gandaki Province",
        "gandaki",
        [
            "Baglung", "Gorkha", "Kaski", "Lamjung", "Manang", "Mustang", "Myagdi",
            "Nawalpur", "Parbat", "Syangja", "Tanahun",
        ],
    ),
    (
        "Lumbini Province",
        "lumbini",
        [
            "Arghakhanchi", "Banke", "Bardiya", "Dang", "Eastern Rukum", "Gulmi", "Kapilvastu",
            "Parasi", "Palpa", "Pyuthan", "Rolpa", "Rupandehi",
        ],
    ),
    (
        "Karnali Province",
        "karnali",
        [
            "Dailekh", "Dolpa", "Humla", "Jajarkot", "Jumla", "Kalikot", "Mugu",
            "Salyan", "Surkhet", "Western Rukum",
        ],
    ),
    (
        "Sudurpashchim Province",
        "sudur",
        [
            "Bajura", "Bajhang", "Darchula", "Baitadi", "Dadeldhura", "Doti", "Achham",
            "Kailali", "Kanchanpur",
        ],
    ),
]

KATHMANDU_METRO_CODE = "ktm-metro"


class Command(BaseCommand):
    help = (
        "Seed Nepal's 7 provinces and 77 districts, plus Kathmandu Metropolitan City "
        "(the only municipality the seeded example processes' offices reference)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        province_count = 0
        district_count = 0

        for province_name, province_code, district_names in PROVINCES:
            province, was_created = Province.objects.get_or_create(
                code=province_code, defaults={"name": province_name}
            )
            province_count += int(was_created)

            for index, district_name in enumerate(district_names, start=1):
                district_code = f"{province_code}-{index:02d}"
                _, was_created = District.objects.get_or_create(
                    code=district_code,
                    defaults={"name": district_name, "province": province},
                )
                district_count += int(was_created)

        kathmandu_district = District.objects.get(name="Kathmandu", province__code="bagmati")
        _, municipality_created = Municipality.objects.get_or_create(
            code=KATHMANDU_METRO_CODE,
            defaults={
                "name": "Kathmandu Metropolitan City",
                "district": kathmandu_district,
                "type": Municipality.MunicipalityType.METROPOLITAN,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Provinces: {province_count} created. Districts: {district_count} created. "
                f"Kathmandu Metropolitan City {'created' if municipality_created else 'already existed'}."
            )
        )
